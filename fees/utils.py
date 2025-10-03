# fees/utils.py - Helper Functions for Fees Management

from django.db.models import Sum, Count, Q
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from datetime import date, timedelta
from decimal import Decimal
import logging

from .models import (
    StudentFeeAssignment, EMISchedule, PaymentRecord, 
    PaymentReminder, FeeStructure
)

logger = logging.getLogger(__name__)

def calculate_overdue_amount(student=None, course=None):
    """Calculate total overdue amount for student or course"""
    
    overdue_emis = EMISchedule.objects.filter(
        status__in=['pending', 'overdue'],
        due_date__lt=date.today()
    )
    
    if student:
        overdue_emis = overdue_emis.filter(fee_assignment__student=student)
    
    if course:
        overdue_emis = overdue_emis.filter(fee_assignment__course=course)
    
    # Update status to overdue
    overdue_emis.update(status='overdue')
    
    total_overdue = overdue_emis.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
    
    return {
        'total_amount': total_overdue,
        'count': overdue_emis.count(),
        'emis': overdue_emis
    }


def check_and_lock_courses():
    """Check all students and lock courses if payments are overdue"""
    
    locked_count = 0
    
    # Get all active fee assignments
    assignments = StudentFeeAssignment.objects.filter(
        status='active',
        is_course_locked=False
    )
    
    for assignment in assignments:
        if assignment.should_lock_course():
            assignment.lock_course()
            locked_count += 1
            
            # Log the action
            logger.info(f"Course locked for student {assignment.student.get_full_name()} "
                       f"in course {assignment.course.title} due to overdue payments")
    
    return locked_count


def auto_unlock_courses():
    """Auto-unlock courses based on unlock_date"""
    
    unlocked_count = 0
    
    # Get locked assignments with unlock dates
    assignments = StudentFeeAssignment.objects.filter(
        is_course_locked=True,
        unlock_date__lte=date.today()
    )
    
    for assignment in assignments:
        assignment.unlock_course()
        unlocked_count += 1
        
        # Log the action
        logger.info(f"Course auto-unlocked for student {assignment.student.get_full_name()} "
                   f"in course {assignment.course.title}")
    
    return unlocked_count


def send_payment_reminder(assignment, reminder_type='overdue'):
    """Send payment reminder to student"""
    
    try:
        student = assignment.student
        course = assignment.course
        
        # Get overdue EMIs
        overdue_emis = assignment.emi_schedules.filter(
            status='overdue',
            due_date__lt=date.today()
        )
        
        if not overdue_emis.exists() and reminder_type == 'overdue':
            return {'success': False, 'message': 'No overdue payments found'}
        
        # Calculate total overdue amount
        total_overdue = overdue_emis.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        
        # Create reminder content based on type
        if reminder_type == 'overdue':
            subject = f"Payment Overdue - {course.title}"
            message = f"""
Dear {student.get_full_name()},

This is to inform you that your payment for the course "{course.title}" is overdue.

Overdue Amount: ${total_overdue}
Number of Overdue EMIs: {overdue_emis.count()}

Please make the payment immediately to avoid course suspension.

If you have already made the payment, please contact our support team.

Best regards,
LMS Team
"""
        elif reminder_type == 'due_soon':
            # Get EMIs due in next 3 days
            upcoming_emis = assignment.emi_schedules.filter(
                status='pending',
                due_date__lte=date.today() + timedelta(days=3),
                due_date__gte=date.today()
            )
            
            if not upcoming_emis.exists():
                return {'success': False, 'message': 'No upcoming payments found'}
            
            upcoming_amount = upcoming_emis.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
            
            subject = f"Payment Reminder - {course.title}"
            message = f"""
Dear {student.get_full_name()},

This is a friendly reminder that your payment for the course "{course.title}" is due soon.

Amount Due: ${upcoming_amount}
Due Date: {upcoming_emis.first().due_date}

Please ensure timely payment to continue your course access.

Best regards,
LMS Team
"""
        elif reminder_type == 'final_notice':
            subject = f"Final Notice - Payment Overdue - {course.title}"
            message = f"""
Dear {student.get_full_name()},

FINAL NOTICE: Your payment for the course "{course.title}" is severely overdue.

Overdue Amount: ${total_overdue}
Days Overdue: {(date.today() - overdue_emis.first().due_date).days}

Your course access will be suspended if payment is not received within 24 hours.

Please make immediate payment or contact our support team.

Best regards,
LMS Team
"""
        
        # Send email
        try:
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[student.email],
                fail_silently=False,
            )
            
            # Record reminder
            for emi in overdue_emis:
                PaymentReminder.objects.create(
                    emi_schedule=emi,
                    reminder_type=reminder_type,
                    scheduled_date=date.today(),
                    subject=subject,
                    message=message,
                    status='sent'
                )
            
            return {'success': True, 'message': f'Reminder sent to {student.email}'}
            
        except Exception as e:
            logger.error(f"Failed to send email to {student.email}: {str(e)}")
            return {'success': False, 'message': 'Failed to send email'}
            
    except Exception as e:
        logger.error(f"Error in send_payment_reminder: {str(e)}")
        return {'success': False, 'message': 'An error occurred'}


def generate_fee_report(report_params):
    """Generate various fee reports"""
    
    report_type = report_params.get('report_type')
    date_from = report_params.get('date_from')
    date_to = report_params.get('date_to')
    course = report_params.get('course')
    student = report_params.get('student')
    status = report_params.get('status')
    
    report_data = {
        'report_type': report_type,
        'date_range': f"{date_from} to {date_to}",
        'generated_at': timezone.now(),
        'data': {},
        'summary': {}
    }
    
    if report_type == 'payment_summary':
        # Payment summary report
        payments = PaymentRecord.objects.filter(
            payment_date__range=[date_from, date_to],
            status='completed'
        )
        
        if course:
            payments = payments.filter(fee_assignment__course=course)
        
        if student:
            payments = payments.filter(fee_assignment__student=student)
        
        # Summary data
        total_payments = payments.count()
        total_amount = payments.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        
        # Payment method breakdown
        method_breakdown = payments.values('payment_method').annotate(
            count=Count('id'),
            total=Sum('amount')
        ).order_by('-total')
        
        # Daily collection data
        daily_collections = payments.extra(
            select={'day': 'DATE(payment_date)'}
        ).values('day').annotate(
            count=Count('id'),
            total=Sum('amount')
        ).order_by('day')
        
        report_data['data'] = {
            'payments': payments.values(
                'payment_date', 'amount', 'payment_method',
                'fee_assignment__student__first_name',
                'fee_assignment__student__last_name',
                'fee_assignment__course__title',
                'transaction_id', 'status'
            ),
            'method_breakdown': list(method_breakdown),
            'daily_collections': list(daily_collections)
        }
        
        report_data['summary'] = {
            'total_payments': total_payments,
            'total_amount': float(total_amount),
            'average_payment': float(total_amount / total_payments) if total_payments > 0 else 0
        }
    
    elif report_type == 'overdue_payments':
        # Overdue payments report
        overdue_emis = EMISchedule.objects.filter(
            status='overdue',
            due_date__lt=date.today()
        ).select_related('fee_assignment__student', 'fee_assignment__course')
        
        if course:
            overdue_emis = overdue_emis.filter(fee_assignment__course=course)
        
        if student:
            overdue_emis = overdue_emis.filter(fee_assignment__student=student)
        
        # Group by student
        student_overdue = {}
        total_overdue_amount = Decimal('0.00')
        
        for emi in overdue_emis:
            student_id = emi.fee_assignment.student.id
            if student_id not in student_overdue:
                student_overdue[student_id] = {
                    'student_name': emi.fee_assignment.student.get_full_name(),
                    'student_email': emi.fee_assignment.student.email,
                    'course': emi.fee_assignment.course.title,
                    'emis': [],
                    'total_overdue': Decimal('0.00'),
                    'days_overdue': 0
                }
            
            student_overdue[student_id]['emis'].append({
                'installment_number': emi.installment_number,
                'amount': float(emi.amount),
                'due_date': emi.due_date,
                'days_overdue': (date.today() - emi.due_date).days
            })
            student_overdue[student_id]['total_overdue'] += emi.amount
            student_overdue[student_id]['days_overdue'] = max(
                student_overdue[student_id]['days_overdue'],
                (date.today() - emi.due_date).days
            )
            total_overdue_amount += emi.amount
        
        report_data['data'] = {
            'overdue_students': student_overdue
        }
        
        report_data['summary'] = {
            'total_overdue_students': len(student_overdue),
            'total_overdue_amount': float(total_overdue_amount),
            'total_overdue_emis': overdue_emis.count()
        }
    
    elif report_type == 'collection_report':
        # Collection efficiency report
        assignments = StudentFeeAssignment.objects.filter(
            assigned_date__range=[date_from, date_to]
        )
        
        if course:
            assignments = assignments.filter(course=course)
        
        if status:
            assignments = assignments.filter(status=status)
        
        # Calculate collection metrics
        total_assigned_amount = assignments.aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')
        total_collected_amount = assignments.aggregate(total=Sum('amount_paid'))['total'] or Decimal('0.00')
        collection_percentage = (total_collected_amount / total_assigned_amount * 100) if total_assigned_amount > 0 else 0
        
        # Fee structure wise breakdown
        structure_breakdown = assignments.values(
            'fee_structure__name'
        ).annotate(
            count=Count('id'),
            total_assigned=Sum('total_amount'),
            total_collected=Sum('amount_paid')
        ).order_by('-total_assigned')
        
        report_data['data'] = {
            'assignments': assignments.values(
                'student__first_name', 'student__last_name',
                'course__title', 'fee_structure__name',
                'total_amount', 'amount_paid', 'amount_pending',
                'assigned_date', 'status'
            ),
            'structure_breakdown': list(structure_breakdown)
        }
        
        report_data['summary'] = {
            'total_assignments': assignments.count(),
            'total_assigned_amount': float(total_assigned_amount),
            'total_collected_amount': float(total_collected_amount),
            'collection_percentage': round(float(collection_percentage), 2),
            'pending_amount': float(total_assigned_amount - total_collected_amount)
        }
    
    elif report_type == 'student_wise':
        # Student-wise fee report
        if student:
            assignments = StudentFeeAssignment.objects.filter(student=student)
        else:
            assignments = StudentFeeAssignment.objects.all()
        
        if course:
            assignments = assignments.filter(course=course)
        
        student_data = {}
        
        for assignment in assignments.select_related('student', 'course', 'fee_structure'):
            student_id = assignment.student.id
            if student_id not in student_data:
                student_data[student_id] = {
                    'student_name': assignment.student.get_full_name(),
                    'student_email': assignment.student.email,
                    'courses': [],
                    'total_fees': Decimal('0.00'),
                    'total_paid': Decimal('0.00'),
                    'total_pending': Decimal('0.00')
                }
            
            # Get payment history for this assignment
            payments = assignment.payments.filter(status='completed')
            
            course_info = {
                'course_name': assignment.course.title,
                'fee_structure': assignment.fee_structure.name,
                'total_amount': float(assignment.total_amount),
                'amount_paid': float(assignment.amount_paid),
                'amount_pending': float(assignment.amount_pending),
                'status': assignment.status,
                'payment_history': list(payments.values(
                    'amount', 'payment_date', 'payment_method', 'status'
                ))
            }
            
            student_data[student_id]['courses'].append(course_info)
            student_data[student_id]['total_fees'] += assignment.total_amount
            student_data[student_id]['total_paid'] += assignment.amount_paid
            student_data[student_id]['total_pending'] += assignment.amount_pending
        
        report_data['data'] = {
            'students': student_data
        }
        
        total_students = len(student_data)
        total_fees = sum(data['total_fees'] for data in student_data.values())
        total_paid = sum(data['total_paid'] for data in student_data.values())
        
        report_data['summary'] = {
            'total_students': total_students,
            'total_fees': float(total_fees),
            'total_paid': float(total_paid),
            'total_pending': float(total_fees - total_paid),
            'collection_rate': round(float(total_paid / total_fees * 100) if total_fees > 0 else 0, 2)
        }
    
    elif report_type == 'course_wise':
        # Course-wise fee report
        if course:
            assignments = StudentFeeAssignment.objects.filter(course=course)
        else:
            assignments = StudentFeeAssignment.objects.all()
        
        if date_from and date_to:
            assignments = assignments.filter(assigned_date__range=[date_from, date_to])
        
        course_data = {}
        
        for assignment in assignments.select_related('course', 'fee_structure'):
            course_id = assignment.course.id
            if course_id not in course_data:
                course_data[course_id] = {
                    'course_name': assignment.course.title,
                    'course_code': assignment.course.course_code,
                    'total_students': 0,
                    'total_fees': Decimal('0.00'),
                    'total_collected': Decimal('0.00'),
                    'fee_structures': {}
                }
            
            course_data[course_id]['total_students'] += 1
            course_data[course_id]['total_fees'] += assignment.total_amount
            course_data[course_id]['total_collected'] += assignment.amount_paid
            
            # Fee structure breakdown
            structure_name = assignment.fee_structure.name
            if structure_name not in course_data[course_id]['fee_structures']:
                course_data[course_id]['fee_structures'][structure_name] = {
                    'count': 0,
                    'total_amount': Decimal('0.00'),
                    'collected_amount': Decimal('0.00')
                }
            
            course_data[course_id]['fee_structures'][structure_name]['count'] += 1
            course_data[course_id]['fee_structures'][structure_name]['total_amount'] += assignment.total_amount
            course_data[course_id]['fee_structures'][structure_name]['collected_amount'] += assignment.amount_paid
        
        report_data['data'] = {
            'courses': course_data
        }
        
        total_courses = len(course_data)
        total_students = sum(data['total_students'] for data in course_data.values())
        total_fees = sum(data['total_fees'] for data in course_data.values())
        total_collected = sum(data['total_collected'] for data in course_data.values())
        
        report_data['summary'] = {
            'total_courses': total_courses,
            'total_students': total_students,
            'total_fees': float(total_fees),
            'total_collected': float(total_collected),
            'total_pending': float(total_fees - total_collected),
            'collection_rate': round(float(total_collected / total_fees * 100) if total_fees > 0 else 0, 2)
        }
    
    return report_data


def process_bulk_payment_update(form_data, user):
    """Process bulk payment operations"""
    
    action = form_data.get('action')
    emi_schedules = form_data.get('emi_schedules')
    payment_date = form_data.get('payment_date')
    new_due_date = form_data.get('new_due_date')
    payment_method = form_data.get('payment_method')
    notes = form_data.get('notes', '')
    
    try:
        if action == 'mark_paid':
            # Mark selected EMIs as paid
            for emi in emi_schedules:
                if emi.status in ['pending', 'overdue']:
                    # Create payment record
                    PaymentRecord.objects.create(
                        fee_assignment=emi.fee_assignment,
                        emi_schedule=emi,
                        amount=emi.amount,
                        payment_method=payment_method,
                        payment_date=payment_date,
                        status='completed',
                        notes=f"Bulk payment update: {notes}",
                        recorded_by=user
                    )
                    
                    # Mark EMI as paid
                    emi.mark_as_paid(payment_date)
            
            return {
                'success': True,
                'message': f'{len(emi_schedules)} EMIs marked as paid successfully'
            }
        
        elif action == 'send_reminder':
            # Send payment reminders
            sent_count = 0
            for emi in emi_schedules:
                result = send_payment_reminder(emi.fee_assignment, 'overdue')
                if result['success']:
                    sent_count += 1
            
            return {
                'success': True,
                'message': f'Payment reminders sent to {sent_count} students'
            }
        
        elif action == 'apply_late_fee':
            # Apply late fees
            total_late_fee = Decimal('0.00')
            for emi in emi_schedules:
                if emi.status == 'overdue':
                    late_fee = emi.calculate_late_fee()
                    total_late_fee += late_fee
            
            return {
                'success': True,
                'message': f'Late fees applied. Total: ${total_late_fee}'
            }
        
        elif action == 'waive_late_fee':
            # Waive late fees
            for emi in emi_schedules:
                emi.late_fee_applied = Decimal('0.00')
                emi.save()
            
            return {
                'success': True,
                'message': f'Late fees waived for {len(emi_schedules)} EMIs'
            }
        
        elif action == 'extend_due_date':
            # Extend due dates
            for emi in emi_schedules:
                emi.due_date = new_due_date
                emi.status = 'pending'  # Reset status
                emi.save()
            
            return {
                'success': True,
                'message': f'Due dates extended for {len(emi_schedules)} EMIs'
            }
        
        else:
            return {
                'success': False,
                'message': 'Invalid action specified'
            }
    
    except Exception as e:
        logger.error(f"Error in bulk payment update: {str(e)}")
        return {
            'success': False,
            'message': f'An error occurred: {str(e)}'
        }


def calculate_late_fees_for_overdue():
    """Calculate and apply late fees for all overdue EMIs"""
    
    overdue_emis = EMISchedule.objects.filter(
        status='overdue',
        late_fee_applied=0,
        due_date__lt=date.today()
    )
    
    total_late_fee = Decimal('0.00')
    processed_count = 0
    
    for emi in overdue_emis:
        late_fee = emi.calculate_late_fee()
        if late_fee > 0:
            total_late_fee += late_fee
            processed_count += 1
    
    return {
        'processed_count': processed_count,
        'total_late_fee': total_late_fee
    }


def get_dashboard_stats():
    """Get key statistics for fees dashboard"""
    
    today = date.today()
    
    # Active assignments
    active_assignments = StudentFeeAssignment.objects.filter(status='active')
    
    # Total amounts
    total_assigned = active_assignments.aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')
    total_collected = active_assignments.aggregate(total=Sum('amount_paid'))['total'] or Decimal('0.00')
    total_pending = total_assigned - total_collected
    
    # Collection rate
    collection_rate = (total_collected / total_assigned * 100) if total_assigned > 0 else 0
    
    # Today's collections
    today_collections = PaymentRecord.objects.filter(
        payment_date=today,
        status='completed'
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
    
    # Overdue information
    overdue_emis = EMISchedule.objects.filter(
        status='overdue',
        due_date__lt=today
    )
    
    overdue_amount = overdue_emis.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
    overdue_students = overdue_emis.values('fee_assignment__student').distinct().count()
    
    # Locked courses
    locked_courses = active_assignments.filter(is_course_locked=True).count()
    
    # Upcoming due payments (next 7 days)
    upcoming_emis = EMISchedule.objects.filter(
        status='pending',
        due_date__gte=today,
        due_date__lte=today + timedelta(days=7)
    )
    
    upcoming_amount = upcoming_emis.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
    
    return {
        'total_assigned': total_assigned,
        'total_collected': total_collected,
        'total_pending': total_pending,
        'collection_rate': round(float(collection_rate), 2),
        'today_collections': today_collections,
        'overdue_amount': overdue_amount,
        'overdue_students': overdue_students,
        'locked_courses': locked_courses,
        'upcoming_amount': upcoming_amount,
        'upcoming_payments': upcoming_emis.count()
    }


def sync_course_enrollments_with_fees():
    """Sync course enrollments with fee payments - unlock/lock based on payment status"""
    
    updated_count = 0
    
    # Check all active fee assignments
    assignments = StudentFeeAssignment.objects.filter(status='active')
    
    for assignment in assignments:
        # Check if course should be locked/unlocked
        should_lock = assignment.should_lock_course()
        is_currently_locked = assignment.is_course_locked
        
        if should_lock and not is_currently_locked:
            # Lock the course
            assignment.lock_course()
            updated_count += 1
            logger.info(f"Locked course for {assignment.student.get_full_name()} - {assignment.course.title}")
        
        elif not should_lock and is_currently_locked:
            # Check if payments are up to date
            overdue_emis = assignment.emi_schedules.filter(
                status='overdue',
                due_date__lt=date.today()
            )
            
            if not overdue_emis.exists():
                # Unlock the course
                assignment.unlock_course()
                updated_count += 1
                logger.info(f"Unlocked course for {assignment.student.get_full_name()} - {assignment.course.title}")
    
    return updated_count



# fees/utils.py - Updated with automation functions

from django.db.models import Sum
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from datetime import date, timedelta
from .models import StudentFeeAssignment, EMISchedule, PaymentRecord
import logging

logger = logging.getLogger(__name__)

def check_and_lock_courses():
    """Check overdue payments and lock courses automatically"""
    today = date.today()
    locked_count = 0
    
    # Get all assignments with overdue EMIs
    overdue_assignments = StudentFeeAssignment.objects.filter(
        status='active',
        is_course_locked=False,
        emi_schedules__status='overdue',
        emi_schedules__due_date__lt=today
    ).distinct()
    
    for assignment in overdue_assignments:
        # Check grace period
        grace_period = assignment.fee_structure.grace_period_days or 0
        
        # Get the oldest overdue EMI
        oldest_overdue = assignment.emi_schedules.filter(
            status='overdue',
            due_date__lt=today
        ).order_by('due_date').first()
        
        if oldest_overdue:
            days_overdue = (today - oldest_overdue.due_date).days
            
            if days_overdue > grace_period:
                assignment.lock_course()
                locked_count += 1
                logger.info(f"Locked course for student {assignment.student.email} - {days_overdue} days overdue")
    
    return locked_count

def auto_unlock_courses():
    """Auto-unlock courses based on unlock dates"""
    today = date.today()
    unlocked_count = 0
    
    # Get assignments that should be unlocked today
    assignments_to_unlock = StudentFeeAssignment.objects.filter(
        is_course_locked=True,
        unlock_date=today
    )
    
    for assignment in assignments_to_unlock:
        assignment.unlock_course()
        unlocked_count += 1
        logger.info(f"Auto-unlocked course for student {assignment.student.email}")
    
    return unlocked_count

def calculate_late_fees_for_overdue():
    """Calculate and apply late fees for overdue EMIs"""
    today = date.today()
    processed_count = 0
    
    # Get overdue EMIs that haven't had late fees applied
    overdue_emis = EMISchedule.objects.filter(
        status='overdue',
        due_date__lt=today,
        late_fee_applied=False
    )
    
    for emi in overdue_emis:
        fee_structure = emi.fee_assignment.fee_structure
        
        # Check if late fee should be applied
        if fee_structure.late_fee_amount > 0:
            days_overdue = (today - emi.due_date).days
            
            # Apply late fee after grace period
            grace_period = fee_structure.grace_period_days or 0
            
            if days_overdue > grace_period:
                # Add late fee to EMI amount
                emi.amount += fee_structure.late_fee_amount
                emi.late_fee_applied = True
                emi.save()
                
                processed_count += 1
                logger.info(f"Applied late fee of ${fee_structure.late_fee_amount} to EMI {emi.id}")
    
    return {'processed_count': processed_count}

def send_payment_reminders():
    """Send payment reminders to students with upcoming or overdue EMIs"""
    today = date.today()
    reminder_count = 0
    
    # Get EMIs due in next 3 days or overdue
    upcoming_emis = EMISchedule.objects.filter(
        status__in=['pending', 'overdue'],
        due_date__lte=today + timedelta(days=3)
    ).select_related('fee_assignment__student', 'fee_assignment__course')
    
    for emi in upcoming_emis:
        try:
            student = emi.fee_assignment.student
            course = emi.fee_assignment.course
            
            # Check if reminder was already sent today
            if hasattr(emi, 'last_reminder_sent') and emi.last_reminder_sent == today:
                continue
            
            # Determine reminder type
            if emi.due_date < today:
                subject = f"Overdue Payment Reminder - {course.title}"
                days_overdue = (today - emi.due_date).days
                message = f"""
Dear {student.get_full_name()},

Your EMI payment for {course.title} is overdue by {days_overdue} days.

Payment Details:
- EMI Number: {emi.installment_number}
- Amount: ${emi.amount}
- Due Date: {emi.due_date}

Please make the payment immediately to avoid course access restrictions.

Thank you.
"""
            else:
                subject = f"Upcoming Payment Reminder - {course.title}"
                days_remaining = (emi.due_date - today).days
                message = f"""
Dear {student.get_full_name()},

Your EMI payment for {course.title} is due in {days_remaining} days.

Payment Details:
- EMI Number: {emi.installment_number}
- Amount: ${emi.amount}
- Due Date: {emi.due_date}

Please ensure timely payment to continue your course access.

Thank you.
"""
            
            # Send email
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[student.email],
                fail_silently=True
            )
            
            # Update reminder sent date
            emi.last_reminder_sent = today
            emi.save(update_fields=['last_reminder_sent'])
            
            reminder_count += 1
            logger.info(f"Sent payment reminder to {student.email} for EMI {emi.id}")
            
        except Exception as e:
            logger.error(f"Failed to send reminder for EMI {emi.id}: {str(e)}")
            continue
    
    return reminder_count

def generate_fee_report(report_data):
    """Generate comprehensive fee reports"""
    # Implementation for generating reports
    pass

def process_bulk_payment_update(form_data, user):
    """Process bulk payment updates"""
    # Implementation for bulk operations
    pass

def send_payment_reminder(assignment):
    """Send individual payment reminder"""
    try:
        student = assignment.student
        course = assignment.course
        
        overdue_emis = assignment.emi_schedules.filter(
            status='overdue'
        ).order_by('due_date')
        
        if overdue_emis.exists():
            total_overdue = overdue_emis.aggregate(
                total=Sum('amount')
            )['total'] or 0
            
            subject = f"Payment Reminder - {course.title}"
            message = f"""
Dear {student.get_full_name()},

You have overdue payments for {course.title}.

Total Overdue Amount: ${total_overdue}
Number of Overdue EMIs: {overdue_emis.count()}

Please make the payment as soon as possible to avoid course access restrictions.

Thank you.
"""
            
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[student.email],
                fail_silently=False
            )
            
            return {'success': True, 'message': 'Reminder sent successfully'}
        else:
            return {'success': False, 'message': 'No overdue payments found'}
            
    except Exception as e:
        return {'success': False, 'message': f'Error sending reminder: {str(e)}'}