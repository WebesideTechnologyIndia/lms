# fees/views.py - Complete Fees Management Views

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, Sum, Count, Avg
from django.http import JsonResponse, HttpResponse
from django.utils import timezone
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import get_user_model
from datetime import date, timedelta
import json

from .models import (
    FeeStructure, StudentFeeAssignment, PaymentRecord, 
    EMISchedule, BatchAccessControl, FeeDiscount
)
from .forms import (
    FeeStructureForm, StudentFeeAssignmentForm, PaymentRecordForm,
    QuickPaymentForm, BatchAccessControlForm, FeeDiscountForm,
    FeeReportForm, BulkPaymentUpdateForm, FeeFilterForm
)
from courses.models import Course, Batch
from .utils import (
    calculate_overdue_amount, send_payment_reminder,
    generate_fee_report, process_bulk_payment_update
)

User = get_user_model()

def check_admin_permission(user):
    """Check if user has admin permissions for fees"""
    return user.role in ['superadmin', 'instructor'] and user.is_active

# ==================== ADMIN DASHBOARD ====================

# fees/views.py - Updated admin_fees_dashboard with automatic execution

@login_required
def admin_fees_dashboard(request):
    """Main fees management dashboard with automatic daily tasks"""
    if not check_admin_permission(request.user):
        messages.error(request, "You don't have permission to access fees management")
        return redirect('admin_dashboard')
    
    # Auto-run daily tasks when dashboard is accessed
    tasks_auto_run = False
    daily_task_info = None
    
    try:
        # Check and run daily tasks automatically
        tasks_auto_run, daily_task_info = auto_run_daily_tasks()
        if tasks_auto_run:
            messages.success(request, "Daily tasks completed automatically!")
    except Exception as e:
        logger.error(f"Auto daily tasks failed: {e}")
    
    # Get dashboard statistics
    today = date.today()
    
    # Total statistics
    total_assignments = StudentFeeAssignment.objects.filter(status='active').count()
    total_amount = StudentFeeAssignment.objects.filter(status='active').aggregate(
        total=Sum('total_amount'))['total'] or 0
    collected_amount = StudentFeeAssignment.objects.filter(status='active').aggregate(
        collected=Sum('amount_paid'))['collected'] or 0
    pending_amount = total_amount - collected_amount
    
    # Today's collections
    today_collections = PaymentRecord.objects.filter(
        payment_date=today,
        status='completed'
    ).aggregate(total=Sum('amount'))['total'] or 0
    
    # Overdue payments
    overdue_emis = EMISchedule.objects.filter(
        status='overdue',
        due_date__lt=today
    ).count()
    
    overdue_amount = EMISchedule.objects.filter(
        status='overdue',
        due_date__lt=today
    ).aggregate(total=Sum('amount'))['total'] or 0
    
    # Recent payments
    recent_payments = PaymentRecord.objects.filter(
        status='completed'
    ).select_related(
        'fee_assignment__student',
        'fee_assignment__course'
    ).order_by('-payment_date')[:10]
    
    # Students with locked courses
    locked_students = StudentFeeAssignment.objects.filter(
        is_course_locked=True
    ).count()
    
    # Monthly collection chart data (last 6 months)
    monthly_data = []
    for i in range(6):
        month_date = today.replace(day=1) - timedelta(days=i*30)
        month_collection = PaymentRecord.objects.filter(
            payment_date__year=month_date.year,
            payment_date__month=month_date.month,
            status='completed'
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        monthly_data.append({
            'month': month_date.strftime('%b %Y'),
            'amount': float(month_collection)
        })
    
    monthly_data.reverse()
    
    # Get daily task information if not already fetched
    if not daily_task_info:
        daily_task_info = get_daily_task_info()
    
    # Recent system activity
    recent_activity = get_recent_system_activity()
    
    context = {
        'total_assignments': total_assignments,
        'total_amount': total_amount,
        'collected_amount': collected_amount,
        'pending_amount': pending_amount,
        'collection_percentage': round((collected_amount / total_amount * 100) if total_amount > 0 else 0, 1),
        'today_collections': today_collections,
        'overdue_emis': overdue_emis,
        'overdue_amount': overdue_amount,
        'recent_payments': recent_payments,
        'locked_students': locked_students,
        'monthly_data': json.dumps(monthly_data),
        'daily_task_info': daily_task_info,
        'recent_activity': recent_activity,
        'tasks_auto_run': tasks_auto_run,
    }
    
    return render(request, 'fees/admin_dashboard.html', context)


def auto_run_daily_tasks():
    """Automatically run daily tasks if not done today"""
    from .models import DailyTaskLog
    from .utils import check_and_lock_courses, auto_unlock_courses, calculate_late_fees_for_overdue, send_payment_reminders
    
    today = date.today()
    
    # Check if already run today
    existing_log = DailyTaskLog.objects.filter(
        run_date=today,
        status='completed'
    ).first()
    
    if existing_log:
        # Already completed today, just return the info
        return False, {
            'last_run_time': existing_log.run_time,
            'courses_locked_today': existing_log.courses_locked,
            'courses_unlocked_today': existing_log.courses_unlocked,
            'late_fees_applied_today': existing_log.late_fees_applied,
            'reminders_sent_today': existing_log.reminders_sent,
            'status': existing_log.status,
            'error_message': existing_log.error_message
        }
    
    # Create new log entry
    task_log = DailyTaskLog.objects.create(
        run_date=today,
        status='running'
    )
    
    try:
        logger.info("Starting automatic daily fee tasks...")
        
        # 1. Lock courses for overdue payments
        locked_count = check_and_lock_courses()
        task_log.courses_locked = locked_count
        
        # 2. Auto-unlock courses
        unlocked_count = auto_unlock_courses()
        task_log.courses_unlocked = unlocked_count
        
        # 3. Calculate late fees
        late_fee_result = calculate_late_fees_for_overdue()
        task_log.late_fees_applied = late_fee_result.get('processed_count', 0)
        
        # 4. Send reminders
        reminder_count = send_payment_reminders()
        task_log.reminders_sent = reminder_count
        
        # 5. Calculate total overdue amount
        overdue_amount = EMISchedule.objects.filter(
            status='overdue',
            due_date__lt=today
        ).aggregate(total=Sum('amount'))['total'] or 0
        task_log.total_overdue_amount = overdue_amount
        
        # Mark as completed
        task_log.status = 'completed'
        task_log.save()
        
        logger.info(f"Automatic daily tasks completed: {locked_count} locked, {unlocked_count} unlocked, {task_log.late_fees_applied} late fees, {reminder_count} reminders")
        
        return True, {
            'last_run_time': task_log.run_time,
            'courses_locked_today': locked_count,
            'courses_unlocked_today': unlocked_count,
            'late_fees_applied_today': task_log.late_fees_applied,
            'reminders_sent_today': reminder_count,
            'status': 'completed',
            'error_message': None
        }
        
    except Exception as e:
        task_log.status = 'failed'
        task_log.error_message = str(e)
        task_log.save()
        
        logger.error(f"Automatic daily tasks failed: {str(e)}")
        
        return False, {
            'last_run_time': task_log.run_time,
            'courses_locked_today': 0,
            'courses_unlocked_today': 0,
            'late_fees_applied_today': 0,
            'reminders_sent_today': 0,
            'status': 'failed',
            'error_message': str(e)
        }
    

# fees/views.py में ये functions add करें

def get_daily_task_info():
    """Get information about today's automated tasks"""
    from .models import DailyTaskLog
    
    today = date.today()
    
    try:
        # Get today's task log
        task_log = DailyTaskLog.objects.filter(run_date=today).first()
        
        if task_log:
            return {
                'last_run_time': task_log.run_time,
                'courses_locked_today': task_log.courses_locked,
                'courses_unlocked_today': task_log.courses_unlocked,
                'late_fees_applied_today': task_log.late_fees_applied,
                'reminders_sent_today': task_log.reminders_sent,
                'status': task_log.status,
                'error_message': task_log.error_message
            }
        else:
            return {
                'last_run_time': None,
                'courses_locked_today': 0,
                'courses_unlocked_today': 0,
                'late_fees_applied_today': 0,
                'reminders_sent_today': 0,
                'status': 'pending',
                'error_message': None
            }
    except Exception as e:
        return {
            'last_run_time': None,
            'courses_locked_today': 0,
            'courses_unlocked_today': 0,
            'late_fees_applied_today': 0,
            'reminders_sent_today': 0,
            'status': 'error',
            'error_message': str(e)
        }


def get_recent_system_activity():
    """Get recent system activity for dashboard"""
    activities = []
    today = timezone.now()
    yesterday = today - timedelta(days=1)
    
    try:
        # Recent payments
        recent_payments = PaymentRecord.objects.filter(
            created_at__gte=yesterday,
            status='completed'
        ).count()
        
        if recent_payments > 0:
            activities.append({
                'title': f'{recent_payments} Payment(s) Received',
                'description': 'New payments were processed successfully',
                'timestamp': today - timedelta(hours=2),
                'type': 'success'
            })
        
        # Recently locked courses
        locked_today = StudentFeeAssignment.objects.filter(
            updated_at__gte=yesterday,
            is_course_locked=True
        ).count()
        
        if locked_today > 0:
            activities.append({
                'title': f'{locked_today} Course(s) Locked',
                'description': 'Courses locked due to overdue payments',
                'timestamp': today - timedelta(hours=6),
                'type': 'danger'
            })
        
        # Recently unlocked courses  
        unlocked_today = StudentFeeAssignment.objects.filter(
            updated_at__gte=yesterday,
            is_course_locked=False
        ).count()
        
        if unlocked_today > 0:
            activities.append({
                'title': f'{unlocked_today} Course(s) Unlocked',
                'description': 'Courses unlocked after payment clearance',
                'timestamp': today - timedelta(hours=4),
                'type': 'success'
            })
        
        # New assignments
        new_assignments = StudentFeeAssignment.objects.filter(
            assigned_date__gte=yesterday.date()
        ).count()
        
        if new_assignments > 0:
            activities.append({
                'title': f'{new_assignments} Fee(s) Assigned',
                'description': 'New fee structures assigned to students',
                'timestamp': today - timedelta(hours=8),
                'type': 'info'
            })
    
    except Exception as e:
        # Return empty activities if any error
        pass
    
    return sorted(activities, key=lambda x: x['timestamp'], reverse=True)[:5]
# ==================== FEE STRUCTURE MANAGEMENT ====================

@login_required
def manage_fee_structures(request):
    """Manage fee structures"""
    if not check_admin_permission(request.user):
        messages.error(request, "Access denied")
        return redirect('admin_dashboard')
    
    search = request.GET.get('search', '')
    
    fee_structures = FeeStructure.objects.all()
    
    if search:
        fee_structures = fee_structures.filter(
            Q(name__icontains=search) |
            Q(code__icontains=search) |
            Q(description__icontains=search)
        )
    
    fee_structures = fee_structures.order_by('-created_at')
    
    # Pagination
    paginator = Paginator(fee_structures, 10)
    page_number = request.GET.get('page')
    fee_structures = paginator.get_page(page_number)
    
    context = {
        'fee_structures': fee_structures,
        'search': search,
    }
    
    return render(request, 'fees/manage_fee_structures.html', context)


@login_required
def create_fee_structure(request):
    """Create new fee structure"""
    if not check_admin_permission(request.user):
        messages.error(request, "Access denied")
        return redirect('admin_dashboard')
    
    if request.method == 'POST':
        form = FeeStructureForm(request.POST)
        if form.is_valid():
            fee_structure = form.save(commit=False)
            fee_structure.created_by = request.user
            fee_structure.save()
            messages.success(request, f"Fee structure '{fee_structure.name}' created successfully!")
            return redirect('fees:manage_fee_structures')
    else:
        form = FeeStructureForm()  # Yahan instance=fee_structure nahi chahiye
    
    context = {
        'form': form,
        'title': 'Create Fee Structure',  # Title bhi change karo
    }
    
    return render(request, 'fees/fee_structure_form.html', context)


@login_required
@require_http_methods(["POST"])
def delete_fee_structure(request, structure_id):
    """Delete fee structure"""
    if not check_admin_permission(request.user):
        return JsonResponse({'success': False, 'message': 'Access denied'})
    
    fee_structure = get_object_or_404(FeeStructure, id=structure_id)
    
    # Check if fee structure is being used
    if fee_structure.studentfeeassignment_set.exists():
        return JsonResponse({
            'success': False, 
            'message': 'Cannot delete fee structure that is assigned to students'
        })
    
    fee_structure.delete()
    return JsonResponse({'success': True, 'message': 'Fee structure deleted successfully'})

# ==================== STUDENT FEE ASSIGNMENT ====================

@login_required
def manage_student_fees(request):
    """Manage student fee assignments"""
    if not check_admin_permission(request.user):
        messages.error(request, "Access denied")
        return redirect('admin_dashboard')
    
    # Filter form
    filter_form = FeeFilterForm(request.GET)
    
    assignments = StudentFeeAssignment.objects.select_related(
        'student', 'course', 'fee_structure'
    ).all()
    
    # Apply filters
    if filter_form.is_valid():
        search = filter_form.cleaned_data.get('search')
        course = filter_form.cleaned_data.get('course')
        status = filter_form.cleaned_data.get('status')
        payment_status = filter_form.cleaned_data.get('payment_status')
        fee_structure = filter_form.cleaned_data.get('fee_structure')
        date_from = filter_form.cleaned_data.get('date_from')
        date_to = filter_form.cleaned_data.get('date_to')
        
        if search:
            assignments = assignments.filter(
                Q(student__first_name__icontains=search) |
                Q(student__last_name__icontains=search) |
                Q(student__email__icontains=search) |
                Q(course__title__icontains=search)
            )
        
        if course:
            assignments = assignments.filter(course=course)
        
        if status:
            assignments = assignments.filter(status=status)
        
        if fee_structure:
            assignments = assignments.filter(fee_structure=fee_structure)
        
        if date_from:
            assignments = assignments.filter(assigned_date__gte=date_from)
        
        if date_to:
            assignments = assignments.filter(assigned_date__lte=date_to)
        
        if payment_status:
            if payment_status == 'paid':
                assignments = assignments.filter(amount_pending=0)
            elif payment_status == 'partial':
                assignments = assignments.filter(amount_paid__gt=0, amount_pending__gt=0)
            elif payment_status == 'pending':
                assignments = assignments.filter(amount_paid=0)
            elif payment_status == 'overdue':
                overdue_assignment_ids = EMISchedule.objects.filter(
                    status='overdue',
                    due_date__lt=date.today()
                ).values_list('fee_assignment_id', flat=True)
                assignments = assignments.filter(id__in=overdue_assignment_ids)
    
    assignments = assignments.order_by('-assigned_date')
    
    # Pagination
    paginator = Paginator(assignments, 15)
    page_number = request.GET.get('page')
    assignments = paginator.get_page(page_number)
    
    context = {
        'assignments': assignments,
        'filter_form': filter_form,
    }
    
    return render(request, 'fees/manage_student_fees.html', context)

@login_required
def assign_fee_to_student(request):
    """Assign fee structure to student"""
    if not check_admin_permission(request.user):
        messages.error(request, "Access denied")
        return redirect('admin_dashboard')
    
    if request.method == 'POST':
        form = StudentFeeAssignmentForm(request.POST)
        if form.is_valid():
            assignment = form.save(commit=False)
            assignment.assigned_by = request.user
            assignment.save()
            messages.success(request, f"Fee assigned to {assignment.student.get_full_name()} for {assignment.course.title}")
            return redirect('fees:manage_student_fees')
    else:
        form = StudentFeeAssignmentForm()
    
    context = {
        'form': form,
        'title': 'Assign Fee to Student',
    }
    
    return render(request, 'fees/student_fee_assignment_form.html', context)

@login_required
def student_fee_detail(request, assignment_id):
    """View detailed fee information for a student"""
    if not check_admin_permission(request.user):
        messages.error(request, "Access denied")
        return redirect('admin_dashboard')
    
    assignment = get_object_or_404(
        StudentFeeAssignment.objects.select_related('student', 'course', 'fee_structure'),
        id=assignment_id
    )
    
    # Calculate total paid amount
    total_paid = PaymentRecord.objects.filter(
        fee_assignment=assignment,
        status='completed'
    ).aggregate(total=Sum('amount'))['total'] or 0
    
    # Check if payment is complete
    is_payment_complete = total_paid >= assignment.total_amount
    
    # Get EMI schedule - only show if payment is not complete
    if is_payment_complete:
        emi_schedules = EMISchedule.objects.none()  # Empty queryset
        overdue_emis = EMISchedule.objects.none()
        overdue_amount = 0
    else:
        emi_schedules = assignment.emi_schedules.all().order_by('installment_number')
        # Calculate overdue information
        overdue_emis = emi_schedules.filter(status='overdue')
        overdue_amount = overdue_emis.aggregate(total=Sum('amount'))['total'] or 0
    
    # Get payment history
    payments = assignment.payments.filter(status='completed').order_by('-payment_date')
    
    # Get batch access controls
    batch_controls = BatchAccessControl.objects.filter(
        student=assignment.student
    ).select_related('batch')
    
    context = {
        'assignment': assignment,
        'emi_schedules': emi_schedules,
        'payments': payments,
        'batch_controls': batch_controls,
        'overdue_emis': overdue_emis,
        'overdue_amount': overdue_amount,
        'is_payment_complete': is_payment_complete,  # Template me use karo
        'total_paid': total_paid,
    }
    
    return render(request, 'fees/student_fee_detail.html', context)


# ==================== PAYMENT MANAGEMENT ====================

# fees/views.py - Updated views with AJAX endpoints

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.db.models import Sum, Q
from django.utils import timezone
from datetime import date
import json

# fees/views.py में record_payment view में यह add करें

@login_required
def record_payment(request):
    """Record a new payment"""
    if not check_admin_permission(request.user):
        messages.error(request, "Access denied")
        return redirect('admin_dashboard')
    
    if request.method == 'POST':
        form = PaymentRecordForm(request.POST)
        
        # Dynamically set EMI queryset based on selected fee assignment
        fee_assignment_id = request.POST.get('fee_assignment')
        if fee_assignment_id:
            try:
                fee_assignment = StudentFeeAssignment.objects.get(id=fee_assignment_id)
                form.fields['emi_schedule'].queryset = EMISchedule.objects.filter(
                    fee_assignment=fee_assignment
                )
            except StudentFeeAssignment.DoesNotExist:
                pass
        
        if form.is_valid():
            payment = form.save(commit=False)
            payment.recorded_by = request.user
            payment.save()
            messages.success(request, f"Payment of ${payment.amount} recorded successfully!")
            return redirect('fees:manage_student_fees')
        else:
            # Debug form errors
            print("Form errors:", form.errors)
    else:
        form = PaymentRecordForm()
        
        # Pre-fill if student is specified
        student_id = request.GET.get('student')
        if student_id:
            form.fields['fee_assignment'].queryset = StudentFeeAssignment.objects.filter(
                student_id=student_id,
                status='active'
            )
    
    context = {
        'form': form,
        'title': 'Record Payment',
    }
    
    return render(request, 'fees/payment_form.html', context)

# fees/views.py में add करें
from django.http import JsonResponse


# fees/views.py में add करें
# fees/views.py में replace करें

from django.db.models import Sum
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required

@login_required
def get_emi_schedules_ajax(request):
    """Get EMI schedules for a fee assignment"""
    assignment_id = request.GET.get('assignment_id')
    
    if not assignment_id:
        return JsonResponse({'success': False, 'error': 'Assignment ID required'})
    
    try:
        assignment = StudentFeeAssignment.objects.get(id=assignment_id)
        emi_schedules = EMISchedule.objects.filter(
            fee_assignment=assignment
        ).order_by('due_date')
        
        # Build EMI data without using amount_paid field
        emis_data = []
        for emi in emi_schedules:
            # Calculate amount paid for this EMI from PaymentRecord
            emi_payments = PaymentRecord.objects.filter(
                fee_assignment=assignment,
                emi_schedule=emi,
                status='completed'
            ).aggregate(total=Sum('amount'))['total'] or 0
            
            # Determine status based on payments and due date
            if emi_payments >= emi.amount:
                status = 'paid'
            elif emi.due_date < timezone.now().date():
                status = 'overdue'
            else:
                status = 'pending'
            
            emis_data.append({
                'id': emi.id,
                'text': f"EMI {emi.installment_number} - ${emi.amount} (Due: {emi.due_date.strftime('%d %b %Y')}) - {status.title()}",
                'amount': float(emi.amount),
                'due_date': emi.due_date.strftime('%Y-%m-%d'),
                'status': status,
                'installment_number': emi.installment_number
            })
        
        # Calculate assignment totals
        total_paid = PaymentRecord.objects.filter(
            fee_assignment=assignment,
            status='completed'
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        data = {
            'success': True,
            'emis': emis_data,
            'assignment_info': {
                'student_name': assignment.student.get_full_name(),
                'course_title': assignment.course.title,
                'total_amount': float(assignment.total_amount),
                'amount_paid': float(total_paid),
                'amount_pending': float(assignment.total_amount - total_paid),
                'is_course_locked': assignment.is_course_locked
            }
        }
        
        return JsonResponse(data)
        
    except StudentFeeAssignment.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Assignment not found'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
def calculate_payment_ajax(request):
    """Calculate payment amount for different scenarios"""
    assignment_id = request.GET.get('assignment_id')
    payment_type = request.GET.get('payment_type')
    
    if not assignment_id or not payment_type:
        return JsonResponse({'success': False, 'error': 'Missing parameters'})
    
    try:
        assignment = StudentFeeAssignment.objects.get(id=assignment_id)
        amount = 0
        
        if payment_type == 'current_emi':
            # Get current due EMI that hasn't been fully paid
            current_emis = EMISchedule.objects.filter(
                fee_assignment=assignment,
                due_date__lte=timezone.now().date()
            ).order_by('due_date')
            
            for emi in current_emis:
                # Check how much has been paid for this EMI
                emi_payments = PaymentRecord.objects.filter(
                    fee_assignment=assignment,
                    emi_schedule=emi,
                    status='completed'
                ).aggregate(total=Sum('amount'))['total'] or 0
                
                if emi_payments < emi.amount:
                    amount = float(emi.amount - emi_payments)
                    break
                    
        elif payment_type == 'overdue_emis':
            # Get all overdue EMIs
            overdue_emis = EMISchedule.objects.filter(
                fee_assignment=assignment,
                due_date__lt=timezone.now().date()
            )
            
            for emi in overdue_emis:
                # Check how much has been paid for this EMI
                emi_payments = PaymentRecord.objects.filter(
                    fee_assignment=assignment,
                    emi_schedule=emi,
                    status='completed'
                ).aggregate(total=Sum('amount'))['total'] or 0
                
                if emi_payments < emi.amount:
                    amount += float(emi.amount - emi_payments)
                    
        elif payment_type == 'full_course':
            # Calculate total pending amount
            total_paid = PaymentRecord.objects.filter(
                fee_assignment=assignment,
                status='completed'
            ).aggregate(total=Sum('amount'))['total'] or 0
            
            amount = float(assignment.total_amount - total_paid)
        
        # Ensure amount is not negative
        amount = max(0, amount)
        
        return JsonResponse({
            'success': True,
            'amount': amount
        })
        
    except StudentFeeAssignment.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Assignment not found'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@login_required
@require_http_methods(["GET"])
def get_emi_schedules(request):
    """AJAX endpoint to get EMI schedules for a fee assignment"""
    if not check_admin_permission(request.user):
        return JsonResponse({'success': False, 'error': 'Access denied'})
    
    assignment_id = request.GET.get('assignment_id')
    
    if not assignment_id:
        return JsonResponse({'success': False, 'error': 'Assignment ID is required'})
    
    try:
        assignment = StudentFeeAssignment.objects.get(id=assignment_id)
        emi_schedules = EMISchedule.objects.filter(
            fee_assignment=assignment
        ).order_by('installment_number')
        
        emi_data = []
        for emi in emi_schedules:
            # Determine status
            status = 'pending'
            if emi.amount_paid >= emi.amount:
                status = 'paid'
            elif emi.due_date < date.today() and emi.amount_paid < emi.amount:
                status = 'overdue'
            
            emi_data.append({
                'id': emi.id,
                'installment_number': emi.installment_number,
                'installment_type': emi.installment_type,
                'amount': float(emi.amount),
                'amount_paid': float(emi.amount_paid),
                'due_date': emi.due_date.strftime('%Y-%m-%d'),
                'status': status
            })
        
        return JsonResponse({
            'success': True,
            'emi_schedules': emi_data
        })
        
    except StudentFeeAssignment.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Fee assignment not found'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@require_http_methods(["GET"])
def get_student_fee_info(request):
    """AJAX endpoint to get student fee information"""
    if not check_admin_permission(request.user):
        return JsonResponse({'success': False, 'error': 'Access denied'})
    
    assignment_id = request.GET.get('assignment_id')
    
    if not assignment_id:
        return JsonResponse({'success': False, 'error': 'Assignment ID is required'})
    
    try:
        assignment = StudentFeeAssignment.objects.select_related(
            'student', 'course', 'fee_structure'
        ).get(id=assignment_id)
        
        # Calculate amounts
        total_paid = PaymentRecord.objects.filter(
            fee_assignment=assignment,
            status='completed'
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        pending_amount = assignment.total_amount - total_paid
        
        # Check if course is locked
        is_locked = assignment.is_course_locked()
        
        return JsonResponse({
            'success': True,
            'assignment': {
                'student_name': assignment.student.get_full_name(),
                'course_name': assignment.course.title,
                'fee_structure_name': assignment.fee_structure.name,
                'total_amount': float(assignment.total_amount),
                'amount_paid': float(total_paid),
                'amount_pending': float(pending_amount),
                'is_course_locked': is_locked
            }
        })
        
    except StudentFeeAssignment.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Fee assignment not found'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@require_http_methods(["GET"])
def calculate_payment_amount(request):
    """AJAX endpoint to calculate payment amounts for quick selection"""
    if not check_admin_permission(request.user):
        return JsonResponse({'success': False, 'error': 'Access denied'})
    
    assignment_id = request.GET.get('assignment_id')
    payment_type = request.GET.get('payment_type')
    
    if not assignment_id or not payment_type:
        return JsonResponse({'success': False, 'error': 'Assignment ID and payment type are required'})
    
    try:
        assignment = StudentFeeAssignment.objects.get(id=assignment_id)
        amount = 0
        
        if payment_type == 'current_emi':
            # Get the next unpaid EMI
            current_emi = EMISchedule.objects.filter(
                fee_assignment=assignment,
                amount_paid__lt=models.F('amount')
            ).order_by('due_date').first()
            
            if current_emi:
                amount = float(current_emi.amount - current_emi.amount_paid)
        
        elif payment_type == 'overdue_emis':
            # Calculate total overdue amount
            overdue_emis = EMISchedule.objects.filter(
                fee_assignment=assignment,
                due_date__lt=date.today(),
                amount_paid__lt=models.F('amount')
            )
            
            for emi in overdue_emis:
                amount += float(emi.amount - emi.amount_paid)
        
        elif payment_type == 'full_course':
            # Calculate total pending amount
            total_paid = PaymentRecord.objects.filter(
                fee_assignment=assignment,
                status='completed'
            ).aggregate(total=Sum('amount'))['total'] or 0
            
            amount = float(assignment.total_amount - total_paid)
        
        return JsonResponse({
            'success': True,
            'amount': amount
        })
        
    except StudentFeeAssignment.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Fee assignment not found'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})




@login_required
def quick_payment(request, assignment_id):
    """Quick payment recording for specific assignment"""
    if not check_admin_permission(request.user):
        messages.error(request, "Access denied")
        return redirect('admin_dashboard')
    
    assignment = get_object_or_404(StudentFeeAssignment, id=assignment_id)
    
    if request.method == 'POST':
        form = QuickPaymentForm(request.POST)
        form.fields['fee_assignment'].initial = assignment
        
        if form.is_valid():
            # Process quick payment
            payment_type = form.cleaned_data['payment_type']
            custom_amount = form.cleaned_data.get('custom_amount')
            payment_method = form.cleaned_data['payment_method']
            payment_date = form.cleaned_data['payment_date']
            transaction_id = form.cleaned_data.get('transaction_id')
            notes = form.cleaned_data.get('notes')
            
            # Calculate payment amount based on type
            if payment_type == 'full_course':
                amount = assignment.amount_pending
            elif payment_type == 'current_emi':
                current_emi = assignment.emi_schedules.filter(status='pending').first()
                amount = current_emi.amount if current_emi else 0
            elif payment_type == 'overdue_emis':
                overdue_amount = assignment.emi_schedules.filter(
                    status='overdue'
                ).aggregate(total=Sum('amount'))['total'] or 0
                amount = overdue_amount
            else:  # custom
                amount = custom_amount
            
            if amount > 0:
                # Create payment record
                payment = PaymentRecord.objects.create(
                    fee_assignment=assignment,
                    amount=amount,
                    payment_method=payment_method,
                    payment_date=payment_date,
                    transaction_id=transaction_id or '',
                    notes=notes or '',
                    status='completed',
                    recorded_by=request.user
                )
                
                messages.success(request, f"Payment of ${amount} recorded successfully!")
                return redirect('fees:student_fee_detail', assignment_id=assignment.id)
            else:
                messages.error(request, "Invalid payment amount")
    else:
        form = QuickPaymentForm()
        form.fields['fee_assignment'].initial = assignment
    
    context = {
        'form': form,
        'assignment': assignment,
        'title': f'Quick Payment - {assignment.student.get_full_name()}',
    }
    
    return render(request, 'fees/quick_payment_form.html', context)

@login_required
def payment_history(request):
    """View all payment history"""
    if not check_admin_permission(request.user):
        messages.error(request, "Access denied")
        return redirect('admin_dashboard')
    
    search = request.GET.get('search', '')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    payment_method = request.GET.get('payment_method')
    status = request.GET.get('status')
    
    payments = PaymentRecord.objects.select_related(
        'fee_assignment__student',
        'fee_assignment__course',
        'recorded_by'
    ).all()
    
    # Apply filters
    if search:
        payments = payments.filter(
            Q(fee_assignment__student__first_name__icontains=search) |
            Q(fee_assignment__student__last_name__icontains=search) |
            Q(fee_assignment__course__title__icontains=search) |
            Q(transaction_id__icontains=search) |
            Q(reference_number__icontains=search)
        )
    
    if date_from:
        payments = payments.filter(payment_date__gte=date_from)
    
    if date_to:
        payments = payments.filter(payment_date__lte=date_to)
    
    if payment_method:
        payments = payments.filter(payment_method=payment_method)
    
    if status:
        payments = payments.filter(status=status)
    
    payments = payments.order_by('-payment_date', '-payment_time')
    
    # Pagination
    paginator = Paginator(payments, 20)
    page_number = request.GET.get('page')
    payments = paginator.get_page(page_number)
    
    context = {
        'payments': payments,
        'search': search,
        'date_from': date_from,
        'date_to': date_to,
        'payment_method': payment_method,
        'status': status,
        'payment_methods': PaymentRecord.PAYMENT_METHOD_CHOICES,
        'statuses': PaymentRecord.STATUS_CHOICES,
    }
    
    return render(request, 'fees/payment_history.html', context)

# ==================== OVERDUE MANAGEMENT ====================

@login_required
def overdue_payments(request):
    """Manage overdue payments"""
    if not check_admin_permission(request.user):
        messages.error(request, "Access denied")
        return redirect('admin_dashboard')
    
    # Get overdue EMIs
    overdue_emis = EMISchedule.objects.filter(
        status__in=['pending', 'overdue'],
        due_date__lt=date.today()
    ).select_related(
        'fee_assignment__student',
        'fee_assignment__course'
    ).order_by('due_date')
    
    # Update status to overdue
    overdue_emis.update(status='overdue')
    
    # Group by student for better display
    student_overdue = {}
    for emi in overdue_emis:
        student = emi.fee_assignment.student
        if student not in student_overdue:
            student_overdue[student] = {
                'emis': [],
                'total_overdue': 0,
                'course': emi.fee_assignment.course,
                'assignment': emi.fee_assignment
            }
        student_overdue[student]['emis'].append(emi)
        student_overdue[student]['total_overdue'] += emi.amount
    
    # Calculate totals
    total_overdue_students = len(student_overdue)
    total_overdue_amount = sum(data['total_overdue'] for data in student_overdue.values())
    average_overdue = (total_overdue_amount / total_overdue_students) if total_overdue_students > 0 else 0
    
    # Handle bulk operations
    if request.method == 'POST':
        form = BulkPaymentUpdateForm(request.POST)
        if form.is_valid():
            result = process_bulk_payment_update(form.cleaned_data, request.user)
            if result['success']:
                messages.success(request, result['message'])
            else:
                messages.error(request, result['message'])
            return redirect('fees:overdue_payments')
    else:
        form = BulkPaymentUpdateForm()
        form.fields['emi_schedules'].queryset = overdue_emis
    
    context = {
        'student_overdue': student_overdue,
        'total_overdue_students': total_overdue_students,
        'total_overdue_amount': total_overdue_amount,
        'average_overdue': average_overdue,  # Add this line
        'bulk_form': form,
    }
    
    return render(request, 'fees/overdue_payments.html', context)


@login_required
def lock_course_for_student(request, assignment_id):
    """Lock course for student due to payment issues"""
    if not check_admin_permission(request.user):
        return JsonResponse({'success': False, 'message': 'Access denied'})
    
    assignment = get_object_or_404(StudentFeeAssignment, id=assignment_id)
    assignment.lock_course()
    
    return JsonResponse({
        'success': True, 
        'message': f'Course locked for {assignment.student.get_full_name()}'
    })

@login_required
def unlock_course_for_student(request, assignment_id):
    """Unlock course for student"""
    if not check_admin_permission(request.user):
        return JsonResponse({'success': False, 'message': 'Access denied'})
    
    assignment = get_object_or_404(StudentFeeAssignment, id=assignment_id)
    
    # Get unlock date from request
    unlock_date = request.POST.get('unlock_date')
    if unlock_date:
        assignment.unlock_date = unlock_date
        assignment.save()
    
    assignment.unlock_course()
    
    return JsonResponse({
        'success': True, 
        'message': f'Course unlocked for {assignment.student.get_full_name()}'
    })

# ==================== BATCH ACCESS CONTROL ====================

@login_required
def manage_batch_access(request):
    """Manage batch-level access control"""
    if not check_admin_permission(request.user):
        messages.error(request, "Access denied")
        return redirect('admin_dashboard')
    
    course_id = request.GET.get('course')
    
    batch_controls = BatchAccessControl.objects.select_related(
        'student', 'batch__course', 'created_by'
    ).all()
    
    if course_id:
        batch_controls = batch_controls.filter(batch__course_id=course_id)
    
    batch_controls = batch_controls.order_by('-created_at')
    
    # Get courses for filter
    courses = Course.objects.filter(is_active=True).order_by('title')
    
    # Pagination
    paginator = Paginator(batch_controls, 15)
    page_number = request.GET.get('page')
    batch_controls = paginator.get_page(page_number)
    
    context = {
        'batch_controls': batch_controls,
        'courses': courses,
        'selected_course': course_id,
    }
    
    return render(request, 'fees/manage_batch_access.html', context)

@login_required
def create_batch_access_control(request):
    """Create batch access control"""
    if not check_admin_permission(request.user):
        messages.error(request, "Access denied")
        return redirect('admin_dashboard')
    
    if request.method == 'POST':
        form = BatchAccessControlForm(request.POST)
        if form.is_valid():
            batch_control = form.save(commit=False)
            batch_control.created_by = request.user
            batch_control.save()
            messages.success(request, "Batch access control created successfully!")
            return redirect('fees:manage_batch_access')
    else:
        course_id = request.GET.get('course')
        form = BatchAccessControlForm()
        if course_id:
            form = BatchAccessControlForm(course=Course.objects.get(id=course_id))
    
    context = {
        'form': form,
        'title': 'Create Batch Access Control',
    }
    
    return render(request, 'fees/batch_access_form.html', context)

# ==================== REPORTS ====================

@login_required
def fee_reports(request):
    """Generate various fee reports"""
    if not check_admin_permission(request.user):
        messages.error(request, "Access denied")
        return redirect('admin_dashboard')
    
    if request.method == 'POST':
        form = FeeReportForm(request.POST)
        if form.is_valid():
            report_data = generate_fee_report(form.cleaned_data)
            
            # Return as JSON for AJAX requests
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse(report_data)
            
            context = {
                'form': form,
                'report_data': report_data,
            }
            return render(request, 'fees/fee_reports.html', context)
    else:
        form = FeeReportForm()
    
    context = {
        'form': form,
    }
    
    return render(request, 'fees/fee_reports.html', context)

# ==================== AJAX ENDPOINTS ====================



@login_required
def update_emi_status_ajax(request):
    """Update EMI status via AJAX"""
    if not check_admin_permission(request.user):
        return JsonResponse({'success': False, 'message': 'Access denied'})
    
    if request.method == 'POST':
        emi_id = request.POST.get('emi_id')
        status = request.POST.get('status')
        payment_date = request.POST.get('payment_date')
        
        try:
            emi = EMISchedule.objects.get(id=emi_id)
            
            if status == 'paid':
                emi.mark_as_paid(payment_date)
                message = 'EMI marked as paid successfully'
            elif status in ['pending', 'overdue', 'waived']:
                emi.status = status
                emi.save()
                message = f'EMI status updated to {status}'
            else:
                return JsonResponse({'success': False, 'message': 'Invalid status'})
            
            return JsonResponse({'success': True, 'message': message})
            
        except EMISchedule.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'EMI not found'})
    
    return JsonResponse({'success': False, 'message': 'Invalid request'})

@login_required
def send_payment_reminder_ajax(request):
    """Send payment reminder to student"""
    if not check_admin_permission(request.user):
        return JsonResponse({'success': False, 'message': 'Access denied'})
    
    if request.method == 'POST':
        assignment_id = request.POST.get('assignment_id')
        
        try:
            assignment = StudentFeeAssignment.objects.get(id=assignment_id)
            result = send_payment_reminder(assignment)
            
            return JsonResponse(result)
            
        except StudentFeeAssignment.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Assignment not found'})
    
    return JsonResponse({'success': False, 'message': 'Invalid request'})

# ==================== DISCOUNT MANAGEMENT ====================

@login_required
def manage_discounts(request):
    """Manage fee discounts"""
    if not check_admin_permission(request.user):
        messages.error(request, "Access denied")
        return redirect('admin_dashboard')
    
    discounts = FeeDiscount.objects.all().order_by('-created_at')
    
    # Pagination
    paginator = Paginator(discounts, 10)
    page_number = request.GET.get('page')
    discounts = paginator.get_page(page_number)
    
    context = {
        'discounts': discounts,
    }
    
    return render(request, 'fees/manage_discounts.html', context)

@login_required
def create_discount(request):
    """Create new discount"""
    if not check_admin_permission(request.user):
        messages.error(request, "Access denied")
        return redirect('admin_dashboard')
    
    if request.method == 'POST':
        form = FeeDiscountForm(request.POST)
        if form.is_valid():
            discount = form.save(commit=False)
            discount.created_by = request.user
            discount.save()
            form.save_m2m()  # Save many-to-many relationships
            messages.success(request, f"Discount '{discount.name}' created successfully!")
            return redirect('fees:manage_discounts')
    else:
        form = FeeDiscountForm()
    
    context = {
        'form': form,
        'title': 'Create Discount',
    }
    
    return render(request, 'fees/discount_form.html', context)

@login_required
def edit_discount(request, discount_id):
    """Edit discount"""
    if not check_admin_permission(request.user):
        messages.error(request, "Access denied")
        return redirect('admin_dashboard')
    
    discount = get_object_or_404(FeeDiscount, id=discount_id)
    
    if request.method == 'POST':
        form = FeeDiscountForm(request.POST, instance=discount)
        if form.is_valid():
            form.save()
            messages.success(request, f"Discount '{discount.name}' updated successfully!")
            return redirect('fees:manage_discounts')
    else:
        form = FeeDiscountForm(instance=discount)
    
    context = {
        'form': form,
        'discount': discount,
        'title': 'Edit Discount',
    }
    
    return render(request, 'fees/discount_form.html', context)

@login_required
@require_http_methods(["POST"])
def delete_discount(request, discount_id):
    """Delete discount"""
    if not check_admin_permission(request.user):
        return JsonResponse({'success': False, 'message': 'Access denied'})
    
    discount = get_object_or_404(FeeDiscount, id=discount_id)
    
    # Check if discount is being used
    if discount.usages.exists():
        return JsonResponse({
            'success': False, 
            'message': 'Cannot delete discount that has been used'
        })
    
    discount.delete()
    return JsonResponse({'success': True, 'message': 'Discount deleted successfully'})

# ==================== STUDENT ACCESS VIEWS ====================


# ==================== CRON JOB RELATED VIEWS ====================

# fees/views.py में run_daily_fee_tasks view को update करें

from django.views.decorators.csrf import ensure_csrf_cookie
from django.http import JsonResponse
import logging

logger = logging.getLogger(__name__)

@login_required
@ensure_csrf_cookie
def run_daily_fee_tasks(request):
    """Manually run daily fee management tasks"""
    if not check_admin_permission(request.user):
        return JsonResponse({
            'success': False, 
            'message': 'Access denied'
        }, status=403)
    
    if request.method != 'POST':
        return JsonResponse({
            'success': False,
            'message': 'Only POST requests are allowed'
        }, status=405)
    
    try:
        # Log the attempt
        logger.info(f"Daily fee tasks initiated by user: {request.user.email}")
        
        # Import utils functions
        from .utils import check_and_lock_courses, auto_unlock_courses, calculate_late_fees_for_overdue
        
        results = {}
        
        # Lock courses for overdue payments
        try:
            locked_count = check_and_lock_courses()
            results['locked_courses'] = locked_count
        except Exception as e:
            logger.error(f"Error locking courses: {str(e)}")
            results['locked_courses'] = 0
        
        # Auto-unlock courses based on unlock dates
        try:
            unlocked_count = auto_unlock_courses()
            results['unlocked_courses'] = unlocked_count
        except Exception as e:
            logger.error(f"Error unlocking courses: {str(e)}")
            results['unlocked_courses'] = 0
        
        # Calculate late fees
        try:
            late_fee_result = calculate_late_fees_for_overdue()
            results['late_fees_processed'] = late_fee_result.get("processed_count", 0)
        except Exception as e:
            logger.error(f"Error processing late fees: {str(e)}")
            results['late_fees_processed'] = 0
        
        # Create success message
        message = f"""Daily tasks completed successfully:
• Courses locked: {results['locked_courses']}
• Courses unlocked: {results['unlocked_courses']}
• Late fees processed: {results['late_fees_processed']}"""
        
        logger.info(f"Daily fee tasks completed: {results}")
        
        return JsonResponse({
            'success': True,
            'message': message,
            'results': results
        })
        
    except Exception as e:
        error_msg = f'Error running daily tasks: {str(e)}'
        logger.error(error_msg)
        
        return JsonResponse({
            'success': False,
            'message': error_msg
        }, status=500)
    
# ==================== EXPORT FUNCTIONS ====================

@login_required
def export_payment_report(request):
    """Export payment report to CSV"""
    if not check_admin_permission(request.user):
        messages.error(request, "Access denied")
        return redirect('admin_dashboard')
    
    import csv
    from django.http import HttpResponse
    
    # Get parameters from request
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    course_id = request.GET.get('course')
    
    # Build queryset
    payments = PaymentRecord.objects.filter(status='completed').select_related(
        'fee_assignment__student',
        'fee_assignment__course'
    )
    
    if date_from:
        payments = payments.filter(payment_date__gte=date_from)
    if date_to:
        payments = payments.filter(payment_date__lte=date_to)
    if course_id:
        payments = payments.filter(fee_assignment__course_id=course_id)
    
    # Create CSV response
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="payment_report_{date.today()}.csv"'
    
    writer = csv.writer(response)
    writer.writerow([
        'Date', 'Student Name', 'Student Email', 'Course', 
        'Amount', 'Payment Method', 'Transaction ID', 'Status'
    ])
    
    for payment in payments:
        writer.writerow([
            payment.payment_date,
            payment.fee_assignment.student.get_full_name(),
            payment.fee_assignment.student.email,
            payment.fee_assignment.course.title,
            payment.amount,
            payment.get_payment_method_display(),
            payment.transaction_id,
            payment.get_status_display()
        ])
    
    return response

@login_required
def export_overdue_report(request):
    """Export overdue payments report to CSV"""
    if not check_admin_permission(request.user):
        messages.error(request, "Access denied")
        return redirect('admin_dashboard')
    
    import csv
    from django.http import HttpResponse
    
    # Get overdue EMIs
    overdue_emis = EMISchedule.objects.filter(
        status='overdue',
        due_date__lt=date.today()
    ).select_related(
        'fee_assignment__student',
        'fee_assignment__course'
    ).order_by('due_date')
    
    # Create CSV response
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="overdue_report_{date.today()}.csv"'
    
    writer = csv.writer(response)
    writer.writerow([
        'Student Name', 'Student Email', 'Course', 'EMI Number',
        'Amount', 'Due Date', 'Days Overdue', 'Late Fee Applied'
    ])
    
    for emi in overdue_emis:
        days_overdue = (date.today() - emi.due_date).days
        writer.writerow([
            emi.fee_assignment.student.get_full_name(),
            emi.fee_assignment.student.email,
            emi.fee_assignment.course.title,
            emi.installment_number,
            emi.amount,
            emi.due_date,
            days_overdue,
            emi.late_fee_applied
        ])
    
    return response

# ==================== API ENDPOINTS FOR AJAX ====================

@login_required
def get_student_fee_info_ajax(request):
    """Get student fee information via AJAX"""
    student_id = request.GET.get('student_id')
    
    if not student_id:
        return JsonResponse({'assignments': []})
    
    try:
        assignments = StudentFeeAssignment.objects.filter(
            student_id=student_id,
            status='active'
        ).select_related('course', 'fee_structure').values(
            'id', 'course__title', 'fee_structure__name',
            'total_amount', 'amount_paid', 'amount_pending',
            'is_course_locked'
        )
        
        return JsonResponse({'assignments': list(assignments)})
    except Exception as e:
        return JsonResponse({'assignments': [], 'error': str(e)})

@login_required
def get_fee_structure_details_ajax(request):
    """Get fee structure details via AJAX"""
    structure_id = request.GET.get('structure_id')
    
    if not structure_id:
        return JsonResponse({'structure': {}})
    
    try:
        structure = FeeStructure.objects.get(id=structure_id)
        
        return JsonResponse({
            'structure': {
                'id': structure.id,
                'name': structure.name,
                'total_amount': float(structure.total_amount),
                'payment_type': structure.payment_type,
                'emi_duration_months': structure.emi_duration_months,
                'emi_amount': float(structure.emi_amount) if structure.emi_amount else 0,
                'down_payment': float(structure.down_payment),
                'grace_period_days': structure.grace_period_days
            }
        })
    except FeeStructure.DoesNotExist:
        return JsonResponse({'structure': {}, 'error': 'Fee structure not found'})

@login_required
def calculate_payment_amount_ajax(request):
    """Calculate payment amount for different payment types"""
    assignment_id = request.GET.get('assignment_id')
    payment_type = request.GET.get('payment_type')
    
    try:
        assignment = StudentFeeAssignment.objects.get(id=assignment_id)
        
        if payment_type == 'full_course':
            amount = assignment.amount_pending
        elif payment_type == 'current_emi':
            current_emi = assignment.emi_schedules.filter(status='pending').first()
            amount = float(current_emi.amount) if current_emi else 0
        elif payment_type == 'overdue_emis':
            overdue_amount = assignment.emi_schedules.filter(
                status='overdue'
            ).aggregate(total=Sum('amount'))['total'] or 0
            amount = float(overdue_amount)
        else:
            amount = 0
        
        return JsonResponse({
            'success': True,
            'amount': amount
        })
        
    except StudentFeeAssignment.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Assignment not found'
        })

# ==================== STUDENT PORTAL VIEWS ====================
@login_required
def student_fee_dashboard(request):
    """Student dashboard for viewing their fee information"""
    if request.user.role != 'student':
        messages.error(request, "Access denied")
        return redirect('dashboard')
    
    # Get student's fee assignments
    assignments = StudentFeeAssignment.objects.filter(
        student=request.user,
        status='active'
    ).select_related('course', 'fee_structure')
    
    # Get payment history
    payment_history = PaymentRecord.objects.filter(
        fee_assignment__student=request.user,
        status='completed'
    ).select_related('fee_assignment__course').order_by('-payment_date')[:10]
    
    # Get upcoming EMIs (only for assignments with pending payments)
    upcoming_emis = EMISchedule.objects.filter(
        fee_assignment__student=request.user,
        fee_assignment__amount_pending__gt=0,  # Only if payment pending
        status='pending',
        due_date__gte=date.today(),
        due_date__lte=date.today() + timedelta(days=30)
    ).select_related('fee_assignment__course').order_by('due_date')
    
    # Get overdue EMIs (only for assignments with pending payments)
    overdue_emis = EMISchedule.objects.filter(
        fee_assignment__student=request.user,
        fee_assignment__amount_pending__gt=0,  # Only if payment pending
        status='overdue'
    ).select_related('fee_assignment__course').order_by('due_date')
    
    context = {
        'assignments': assignments,
        'payment_history': payment_history,
        'upcoming_emis': upcoming_emis,
        'overdue_emis': overdue_emis,
    }
    
    return render(request, 'fees/student_dashboard.html', context)


@login_required
def student_course_fees(request, assignment_id):
    """View detailed fee information for a specific course"""
    if request.user.role != 'student':
        messages.error(request, "Access denied")
        return redirect('dashboard')
    
    assignment = get_object_or_404(
        StudentFeeAssignment.objects.select_related('course', 'fee_structure'),
        id=assignment_id,
        student=request.user
    )
    
    # Calculate total paid amount
    total_paid = PaymentRecord.objects.filter(
        fee_assignment=assignment,
        status='completed'
    ).aggregate(total=Sum('amount'))['total'] or 0
    
    # Check if payment is complete
    is_payment_complete = total_paid >= assignment.total_amount
    
    # Get EMI schedule - only show if payment is not complete
    if is_payment_complete:
        emi_schedules = EMISchedule.objects.none()  # Empty queryset
    else:
        emi_schedules = assignment.emi_schedules.all().order_by('installment_number')
    
    # Get payment history for this course
    payments = assignment.payments.filter(status='completed').order_by('-payment_date')
    
    # Add today's date for template comparisons
    today = date.today()
    
    context = {
        'assignment': assignment,
        'emi_schedules': emi_schedules,
        'payments': payments,
        'is_payment_complete': is_payment_complete,
        'total_paid': total_paid,
        'today': today,
    }
    
    return render(request, 'fees/student_course_fees.html', context)


@login_required  
def make_online_payment(request, assignment_id):
    """Initiate online payment for student"""
    if request.user.role != 'student':
        messages.error(request, "Access denied")
        return redirect('dashboard')
    
    assignment = get_object_or_404(
        StudentFeeAssignment,
        id=assignment_id,
        student=request.user
    )
    
    # Check if payment is already complete
    if assignment.amount_pending <= 0:
        messages.info(request, "Payment for this course is already complete!")
        return redirect('fees:student_course_fees', assignment_id=assignment.id)
    
    if request.method == 'POST':
        amount = request.POST.get('amount')
        payment_type = request.POST.get('payment_type')
        
        # Validate amount
        try:
            amount = float(amount)
            if amount <= 0 or amount > assignment.amount_pending:
                messages.error(request, "Invalid payment amount!")
                return redirect('fees:make_online_payment', assignment_id=assignment.id)
        except (ValueError, TypeError):
            messages.error(request, "Invalid payment amount!")
            return redirect('fees:make_online_payment', assignment_id=assignment.id)
        
        # Here you would integrate with payment gateway
        # For now, just create a pending payment record
        payment = PaymentRecord.objects.create(
            fee_assignment=assignment,
            amount=amount,
            payment_method='online',
            payment_date=date.today(),
            status='pending',
            notes=f"Online payment - {payment_type}"
        )
        
        # Redirect to payment gateway or success page
        messages.success(request, "Payment initiated successfully!")
        return redirect('fees:student_course_fees', assignment_id=assignment.id)
    
    # Get payment options (only if payment is pending)
    current_emi = assignment.emi_schedules.filter(
        status='pending',
        amount_paid__lt=models.F('amount')  # EMI not fully paid
    ).first()
    
    overdue_emis = assignment.emi_schedules.filter(status='overdue')
    overdue_amount = overdue_emis.aggregate(total=Sum('amount'))['total'] or 0
    
    # Add today's date for template comparisons
    today = date.today()
    
    context = {
        'assignment': assignment,
        'current_emi': current_emi,
        'overdue_amount': overdue_amount,
        'full_amount': assignment.amount_pending,
        'today': today,
    }
    
    return render(request, 'fees/make_payment.html', context)


@login_required
def edit_fee_structure(request, structure_id):
    """Edit fee structure"""
    if not check_admin_permission(request.user):
        messages.error(request, "Access denied")
        return redirect('admin_dashboard')
    
    fee_structure = get_object_or_404(FeeStructure, id=structure_id)
    
    if request.method == 'POST':
        form = FeeStructureForm(request.POST, instance=fee_structure)
        if form.is_valid():
            form.save()
            messages.success(request, f"Fee structure '{fee_structure.name}' updated successfully!")
            return redirect('fees:manage_fee_structures')
    else:
        form = FeeStructureForm(instance=fee_structure)
    
    context = {
        'form': form,
        'fee_structure': fee_structure,
        'title': 'Edit Fee Structure',
    }
    
    return render(request, 'fees/fee_structure_form.html', context)



# views.py - Student Course Management Views

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.db.models import Q, Sum, Count, Exists, OuterRef
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
import json
from datetime import date, datetime

from userss.models import CustomUser
from courses.models import Course, Batch, Enrollment, BatchEnrollment
from fees.models import StudentFeeAssignment, EMISchedule, BatchAccessControl

def is_admin_or_instructor(user):
    """Check if user is admin or instructor"""
    return user.is_authenticated and user.role in ['superadmin', 'instructor']

@login_required
@user_passes_test(is_admin_or_instructor)
def student_course_management(request):
    """Main view for student course management"""
    
    # Get all students with their course enrollments
    students_query = CustomUser.objects.filter(role='student').select_related().prefetch_related(
        'enrollments__course__fee_assignments',
        'batch_enrollments__batch__course'
    )
    
    # Search functionality
    search = request.GET.get('search', '').strip()
    if search:
        students_query = students_query.filter(
            Q(first_name__icontains=search) |
            Q(last_name__icontains=search) |
            Q(email__icontains=search) |
            Q(username__icontains=search)
        )
    
    # Course filter
    course_filter = request.GET.get('course', '').strip()
    if course_filter:
        students_query = students_query.filter(
            enrollments__course_id=course_filter
        )
    
    # Status filter
    status_filter = request.GET.get('status', '').strip()
    if status_filter == 'locked':
        students_query = students_query.filter(
            fee_assignments__is_course_locked=True
        )
    elif status_filter == 'unlocked':
        students_query = students_query.filter(
            fee_assignments__is_course_locked=False
        )
    elif status_filter == 'overdue':
        students_query = students_query.filter(
            fee_assignments__emi_schedules__status='overdue'
        )
    
    # Remove duplicates
    students_query = students_query.distinct()
    
    # Pagination
    paginator = Paginator(students_query, 10)  # 10 students per page
    page_number = request.GET.get('page')
    students = paginator.get_page(page_number)
    
    # Add additional data for each student
    for student in students:
        # Calculate total overdue amount
        overdue_amount = EMISchedule.objects.filter(
            fee_assignment__student=student,
            status='overdue'
        ).aggregate(
            total=Sum('amount')
        )['total'] or 0
        
        student.total_overdue_amount = overdue_amount
        
        # Get active enrollments with fee assignments
        enrollments = student.enrollments.filter(is_active=True).select_related('course')
        for enrollment in enrollments:
            try:
                fee_assignment = StudentFeeAssignment.objects.get(
                    student=student,
                    course=enrollment.course
                )
                enrollment.fee_assignment = fee_assignment
                enrollment.is_course_locked = fee_assignment.is_course_locked
            except StudentFeeAssignment.DoesNotExist:
                enrollment.fee_assignment = None
                enrollment.is_course_locked = False
            
            # Get batch enrollments for this course
            batch_enrollments = []
            for batch in enrollment.course.batches.filter(is_active=True):
                try:
                    batch_enrollment = BatchEnrollment.objects.get(
                        student=student,
                        batch=batch
                    )
                    batch.batch_enrollment = batch_enrollment
                    batch.is_batch_active = batch_enrollment.is_active
                except BatchEnrollment.DoesNotExist:
                    batch.batch_enrollment = None
                    batch.is_batch_active = False
                batch_enrollments.append(batch)
            
            enrollment.batch_enrollments = batch_enrollments
        
        student.active_enrollments = enrollments
    
    # Get all courses for filter dropdown
    courses = Course.objects.filter(is_active=True, status='published').order_by('title')
    
    context = {
        'students': students,
        'courses': courses,
        'search': search,
        'course_filter': course_filter,
        'status_filter': status_filter,
    }
    
    return render(request, 'fees/student_course_management.html', context)


@require_POST
@login_required
@user_passes_test(is_admin_or_instructor)
def student_course_management_action(request):
    """Handle individual lock/unlock actions"""
    
    if not request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'success': False, 'message': 'Invalid request'})
    
    try:
        action = request.POST.get('action')
        reason = request.POST.get('reason', '').strip()
        
        if not reason:
            return JsonResponse({'success': False, 'message': 'Reason is required'})
        
        if action == 'lock_course':
            return handle_lock_course(request, reason)
        elif action == 'unlock_course':
            return handle_unlock_course(request, reason)
        elif action == 'lock_batch':
            return handle_lock_batch(request, reason)
        elif action == 'unlock_batch':
            return handle_unlock_batch(request, reason)
        else:
            return JsonResponse({'success': False, 'message': 'Invalid action'})
    
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Error: {str(e)}'})




def handle_unlock_course(request, reason):
    """Unlock course access for student"""
    student_id = request.POST.get('student_id')
    course_id = request.POST.get('course_id')
    unlock_until = request.POST.get('unlock_until', '').strip()
    
    try:
        student = get_object_or_404(CustomUser, id=student_id, role='student')
        course = get_object_or_404(Course, id=course_id)
        
        # Get fee assignment
        fee_assignment = StudentFeeAssignment.objects.filter(
            student=student,
            course=course
        ).first()
        
        if fee_assignment:
            # Unlock the course
            fee_assignment.unlock_course()
            
            # Set unlock date if provided
            if unlock_until:
                try:
                    unlock_date = datetime.strptime(unlock_until, '%Y-%m-%d').date()
                    fee_assignment.unlock_date = unlock_date
                    fee_assignment.save()
                except ValueError:
                    pass
        
        # Update batch access control
        BatchAccessControl.objects.filter(
            student=student,
            batch__course=course
        ).update(
            access_type='unlocked',
            reason=reason,
            created_by=request.user,
            effective_from=date.today(),
            override_access=True,
            override_reason=reason,
            override_until=datetime.strptime(unlock_until, '%Y-%m-%d').date() if unlock_until else None
        )
        
        return JsonResponse({
            'success': True,
            'message': f'Course access unlocked for {student.get_full_name()}'
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Error unlocking course: {str(e)}'})

# fees/views.py - Updated with debugging

def handle_lock_batch(request, reason):
    """Lock ONLY this specific batch - NOT course"""
    student_id = request.POST.get('student_id')
    batch_id = request.POST.get('batch_id')
    
    print(f"\n{'='*60}")
    print(f"HANDLE LOCK BATCH Called")
    print(f"Student ID: {student_id}")
    print(f"Batch ID: {batch_id}")
    print(f"Reason: {reason}")
    print(f"{'='*60}\n")
    
    try:
        student = get_object_or_404(CustomUser, id=student_id, role='student')
        batch = get_object_or_404(Batch, id=batch_id)
        
        print(f"Student found: {student.username}")
        print(f"Batch found: {batch.name}")
        
        # METHOD 1: Use BatchAccessControl (RECOMMENDED)
        batch_control, created = BatchAccessControl.objects.update_or_create(
            student=student,
            batch=batch,
            defaults={
                'access_type': 'locked',
                'is_access_allowed': False,  # THIS is the lock
                'reason': reason,
                'created_by': request.user,
                'effective_from': date.today()
            }
        )
        
        print(f"BatchAccessControl {'created' if created else 'updated'}")
        print(f"is_access_allowed: {batch_control.is_access_allowed}")
        
        # Optional: Also deactivate enrollment for extra safety
        enrollment = BatchEnrollment.objects.filter(
            student=student,
            batch=batch
        ).first()
        
        if enrollment:
            enrollment.is_active = False
            enrollment.save()
            print(f"BatchEnrollment deactivated: {enrollment.is_active}")
        
        return JsonResponse({
            'success': True,
            'message': f'Batch "{batch.name}" locked for {student.get_full_name()}',
            'debug': {
                'batch_id': batch.id,
                'student_id': student.id,
                'is_access_allowed': batch_control.is_access_allowed,
                'enrollment_active': enrollment.is_active if enrollment else None
            }
        })
        
    except Exception as e:
        print(f"ERROR in handle_lock_batch: {str(e)}")
        import traceback
        traceback.print_exc()
        return JsonResponse({'success': False, 'message': f'Error: {str(e)}'})


def handle_unlock_batch(request, reason):
    """Unlock ONLY this specific batch"""
    student_id = request.POST.get('student_id')
    batch_id = request.POST.get('batch_id')
    
    print(f"\n{'='*60}")
    print(f"HANDLE UNLOCK BATCH Called")
    print(f"Student ID: {student_id}")
    print(f"Batch ID: {batch_id}")
    print(f"{'='*60}\n")
    
    try:
        student = get_object_or_404(CustomUser, id=student_id, role='student')
        batch = get_object_or_404(Batch, id=batch_id)
        
        # METHOD 1: Update BatchAccessControl
        batch_control, created = BatchAccessControl.objects.update_or_create(
            student=student,
            batch=batch,
            defaults={
                'access_type': 'unlocked',
                'is_access_allowed': True,  # THIS unlocks it
                'reason': reason,
                'created_by': request.user,
                'override_access': True,
                'override_reason': reason
            }
        )
        
        print(f"BatchAccessControl unlocked: {batch_control.is_access_allowed}")
        
        # METHOD 2: Activate enrollment
        enrollment = BatchEnrollment.objects.filter(
            student=student,
            batch=batch
        ).first()
        
        if enrollment:
            enrollment.is_active = True
            enrollment.save()
            print(f"BatchEnrollment activated: {enrollment.is_active}")
        
        return JsonResponse({
            'success': True,
            'message': f'Batch "{batch.name}" unlocked for {student.get_full_name()}',
            'debug': {
                'is_access_allowed': batch_control.is_access_allowed,
                'enrollment_active': enrollment.is_active if enrollment else None
            }
        })
        
    except Exception as e:
        print(f"ERROR: {str(e)}")
        return JsonResponse({'success': False, 'message': f'Error: {str(e)}'})


def handle_lock_course(request, reason):
    """Lock course - does NOT lock individual batches"""
    student_id = request.POST.get('student_id')
    course_id = request.POST.get('course_id')
    
    print(f"\n{'='*60}")
    print(f"HANDLE LOCK COURSE Called")
    print(f"Course ID: {course_id}")
    print(f"{'='*60}\n")
    
    try:
        student = get_object_or_404(CustomUser, id=student_id, role='student')
        course = get_object_or_404(Course, id=course_id)
        
        # Get/create fee assignment and lock course
        fee_assignment, created = StudentFeeAssignment.objects.get_or_create(
            student=student,
            course=course,
            defaults={
                'fee_structure_id': 1,
                'total_amount': course.price,
                'amount_paid': 0,
                'amount_pending': course.price,
                'payment_start_date': date.today(),
                'assigned_by': request.user
            }
        )
        
        # Lock ONLY the course (not batches)
        fee_assignment.is_course_locked = True
        fee_assignment.locked_at = timezone.now()
        fee_assignment.save()
        
        print(f"Course locked: {fee_assignment.is_course_locked}")
        print(f"Batches NOT affected - they remain independent")
        
        return JsonResponse({
            'success': True,
            'message': f'Course "{course.title}" locked (batches independent)'
        })
        
    except Exception as e:
        print(f"ERROR: {str(e)}")
        return JsonResponse({'success': False, 'message': f'Error: {str(e)}'})

@require_POST
@login_required
@user_passes_test(is_admin_or_instructor)
def bulk_course_action(request):
    """Handle bulk actions for multiple students"""
    
    if not request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'success': False, 'message': 'Invalid request'})
    
    try:
        bulk_action = request.POST.get('bulk_action')
        course_id = request.POST.get('course_id')
        reason = request.POST.get('reason', '').strip()
        
        if not all([bulk_action, course_id, reason]):
            return JsonResponse({'success': False, 'message': 'All fields are required'})
        
        course = get_object_or_404(Course, id=course_id)
        
        if bulk_action == 'lock_course':
            return bulk_lock_course(course, reason, request.user)
        elif bulk_action == 'unlock_course':
            return bulk_unlock_course(course, reason, request.user)
        elif bulk_action == 'lock_overdue':
            return bulk_lock_overdue(course, reason, request.user)
        elif bulk_action == 'unlock_paid':
            return bulk_unlock_paid(course, reason, request.user)
        else:
            return JsonResponse({'success': False, 'message': 'Invalid bulk action'})
    
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Error: {str(e)}'})


def bulk_lock_course(course, reason, admin_user):
    """Lock course for all enrolled students"""
    try:
        enrollments = Enrollment.objects.filter(course=course, is_active=True)
        count = 0
        
        for enrollment in enrollments:
            fee_assignment, created = StudentFeeAssignment.objects.get_or_create(
                student=enrollment.student,
                course=course,
                defaults={
                    'fee_structure_id': 1,
                    'total_amount': course.price,
                    'amount_paid': 0,
                    'amount_pending': course.price,
                    'payment_start_date': date.today(),
                    'assigned_by': admin_user
                }
            )
            
            if not fee_assignment.is_course_locked:
                fee_assignment.lock_course()
                count += 1
        
        return JsonResponse({
            'success': True,
            'message': f'Course locked for {count} students'
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Error in bulk lock: {str(e)}'})


def bulk_unlock_course(course, reason, admin_user):
    """Unlock course for all enrolled students"""
    try:
        fee_assignments = StudentFeeAssignment.objects.filter(
            course=course,
            is_course_locked=True
        )
        
        count = fee_assignments.count()
        
        for fee_assignment in fee_assignments:
            fee_assignment.unlock_course()
        
        return JsonResponse({
            'success': True,
            'message': f'Course unlocked for {count} students'
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Error in bulk unlock: {str(e)}'})


def bulk_lock_overdue(course, reason, admin_user):
    """Lock course for students with overdue payments"""
    try:
        overdue_assignments = StudentFeeAssignment.objects.filter(
            course=course,
            emi_schedules__status='overdue',
            is_course_locked=False
        ).distinct()
        
        count = 0
        for assignment in overdue_assignments:
            assignment.lock_course()
            count += 1
        
        return JsonResponse({
            'success': True,
            'message': f'Course locked for {count} students with overdue payments'
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Error in bulk lock overdue: {str(e)}'})


def bulk_unlock_paid(course, reason, admin_user):
    """Unlock course for students who have cleared payments"""
    try:
        paid_assignments = StudentFeeAssignment.objects.filter(
            course=course,
            amount_pending__lte=0,
            is_course_locked=True
        )
        
        count = paid_assignments.count()
        
        for assignment in paid_assignments:
            assignment.unlock_course()
        
        return JsonResponse({
            'success': True,
            'message': f'Course unlocked for {count} students with cleared payments'
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Error in bulk unlock paid: {str(e)}'})


@login_required
@user_passes_test(is_admin_or_instructor)
def student_fee_details(request, student_id, course_id):
    """Detailed fee view for specific student and course - wrapper for existing view"""
    student = get_object_or_404(CustomUser, id=student_id, role='student')
    course = get_object_or_404(Course, id=course_id)
    
    try:
        fee_assignment = StudentFeeAssignment.objects.get(
            student=student,
            course=course
        )
        
        # Redirect to existing detailed view
        from django.urls import reverse
        return redirect(reverse('student_fee_detail', args=[fee_assignment.id]))
        
    except StudentFeeAssignment.DoesNotExist:
        messages.error(request, 'Fee assignment not found for this student and course.')
        return redirect('student_course_management')