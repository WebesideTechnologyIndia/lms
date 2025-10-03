from django.db import models

# Create your models here.
# fees/models.py - Complete Fees Management System

from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from decimal import Decimal
from datetime import date, timedelta
import uuid

User = get_user_model()

class FeeStructure(models.Model):
    """Define different fee plans and structures"""
    
    PAYMENT_TYPE_CHOICES = [
        ('full', 'Full Payment'),
        ('emi', 'EMI (Installments)'),
        ('custom', 'Custom Plan'),
    ]
    
    DURATION_CHOICES = [
        (1, '1 Month'),
        (3, '3 Months'),
        (6, '6 Months'),
        (12, '12 Months'),
        (24, '24 Months'),
    ]
    
    # Basic Details
    name = models.CharField(max_length=200, help_text="e.g., Standard EMI Plan, Full Payment Plan")
    code = models.CharField(max_length=50, unique=True, help_text="e.g., STD_EMI_6M")
    description = models.TextField(blank=True)
    
    # Fee Structure
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_type = models.CharField(max_length=20, choices=PAYMENT_TYPE_CHOICES, default='full')
    
    # EMI Details (only for EMI plans)
    emi_duration_months = models.IntegerField(choices=DURATION_CHOICES, null=True, blank=True)
    emi_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    down_payment = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    
    # Settings
    grace_period_days = models.IntegerField(default=3, help_text="Days after due date before locking")
    late_fee_amount = models.DecimalField(max_digits=8, decimal_places=2, default=0.00)
    late_fee_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    
    # Discounts
    early_payment_discount = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    bulk_discount = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    
    # Status
    is_active = models.BooleanField(default=True)
    is_default = models.BooleanField(default=False)
    
    # Tracking
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True,
        limit_choices_to={'role__in': ['superadmin', 'instructor']}
    )
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Fee Structure"
        verbose_name_plural = "Fee Structures"
    
    def __str__(self):
        return f"{self.name} - ${self.total_amount}"
    
    def save(self, *args, **kwargs):
        # Auto-calculate EMI amount if not provided
        if self.payment_type == 'emi' and self.emi_duration_months and not self.emi_amount:
            remaining_amount = self.total_amount - self.down_payment
            self.emi_amount = remaining_amount / self.emi_duration_months
        
        # Ensure only one default plan
        if self.is_default:
            FeeStructure.objects.filter(is_default=True).update(is_default=False)
        
        super().save(*args, **kwargs)
    
    def get_monthly_amount(self):
        """Get monthly payment amount"""
        if self.payment_type == 'emi':
            return self.emi_amount
        return self.total_amount

class StudentFeeAssignment(models.Model):
    """Assign fee structure to students for specific courses"""
    
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('completed', 'Completed'),
        ('suspended', 'Suspended'),
        ('cancelled', 'Cancelled'),
    ]
    
    # Assignment Details
    student = models.ForeignKey(
        User, on_delete=models.CASCADE,
        limit_choices_to={'role': 'student'},
        related_name='fee_assignments'
    )
    course = models.ForeignKey(
        'courses.Course', on_delete=models.CASCADE,
        related_name='fee_assignments'
    )
    fee_structure = models.ForeignKey(FeeStructure, on_delete=models.CASCADE)
    
    # Payment Details
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    amount_pending = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Dates
    assigned_date = models.DateField(auto_now_add=True)
    payment_start_date = models.DateField()
    payment_end_date = models.DateField(null=True, blank=True)
    
    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    is_course_locked = models.BooleanField(default=False)
    locked_at = models.DateTimeField(null=True, blank=True)
    unlock_date = models.DateField(null=True, blank=True, help_text="Admin can set future unlock date")
    
    # Tracking
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    assigned_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True,
        related_name='assigned_fees'
    )
    
    class Meta:
        unique_together = ['student', 'course']
        ordering = ['-created_at']
        verbose_name = "Student Fee Assignment"
        verbose_name_plural = "Student Fee Assignments"
    
    def __str__(self):
        return f"{self.student.get_full_name()} - {self.course.title}"
    
    def save(self, *args, **kwargs):
        is_new = self._state.adding
        
        from decimal import Decimal
        self.amount_pending = self.total_amount - Decimal(str(self.amount_paid))
        
        if self.fee_structure.payment_type == 'emi' and not self.payment_end_date:
            months = self.fee_structure.emi_duration_months or 12
            self.payment_end_date = self.payment_start_date + timedelta(days=months * 30)
        
        super().save(*args, **kwargs)
        
        if is_new and self.fee_structure.payment_type == 'emi':
            self.create_emi_schedule()
    
    def create_emi_schedule(self):
        """Create EMI schedule for this assignment"""
        if self.fee_structure.payment_type != 'emi':
            return
        
        self.emi_schedules.all().delete()
        
        duration = self.fee_structure.emi_duration_months
        emi_amount = self.fee_structure.emi_amount
        start_date = self.payment_start_date
        
        if self.fee_structure.down_payment > 0:
            EMISchedule.objects.create(
                fee_assignment=self,
                installment_number=0,
                due_date=start_date,
                amount=self.fee_structure.down_payment,
                installment_type='down_payment'
            )
        
        for i in range(1, duration + 1):
            due_date = start_date + timedelta(days=i * 30)
            EMISchedule.objects.create(
                fee_assignment=self,
                installment_number=i,
                due_date=due_date,
                amount=emi_amount,
                installment_type='emi'
            )
    
    def get_completion_percentage(self):
        """Calculate payment completion percentage"""
        if self.total_amount == 0:
            return 100
        return round((self.amount_paid / self.total_amount) * 100, 2)
    
    def is_payment_due(self):
        """Check if any payment is overdue"""
        overdue_emis = self.emi_schedules.filter(
            status='pending',
            due_date__lt=date.today()
        )
        return overdue_emis.exists()
    
    def is_batch_locked(self, batch):
        """Check if specific batch is locked due to payment issues"""
        # If admin set unlock date and it's not passed
        if self.unlock_date and date.today() <= self.unlock_date:
            return False
        
        # Check if course-level lock is enabled
        if self.is_course_locked:
            return True
        
        # Check overdue EMIs beyond grace period
        grace_days = self.fee_structure.grace_period_days
        overdue_emis = self.emi_schedules.filter(
            status='pending',
            due_date__lt=date.today() - timedelta(days=grace_days)
        )
        
        return overdue_emis.exists()
    
    def should_lock_course(self):
        """Check if course should be locked due to payment"""
        if self.unlock_date and date.today() <= self.unlock_date:
            return False
        
        overdue_emis = self.emi_schedules.filter(
            status='pending',
            due_date__lt=date.today() - timedelta(days=self.fee_structure.grace_period_days)
        )
        return overdue_emis.exists()
    
    def lock_course(self):
        """Lock the course due to payment issues (course-level)"""
        self.is_course_locked = True
        self.locked_at = timezone.now()
        self.save()
        
        # NOTE: This doesn't change is_active anymore
        # Lock is checked via is_batch_locked() method
    
    def unlock_course(self):
        """Unlock the course"""
        self.is_course_locked = False
        self.locked_at = None
        self.save()


class EMISchedule(models.Model):
    """EMI payment schedule for students"""
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('overdue', 'Overdue'),
        ('waived', 'Waived'),
    ]
    
    INSTALLMENT_TYPE_CHOICES = [
        ('down_payment', 'Down Payment'),
        ('emi', 'EMI'),
        ('late_fee', 'Late Fee'),
        ('adjustment', 'Adjustment'),
    ]
    
    # Basic Details
    fee_assignment = models.ForeignKey(
        StudentFeeAssignment, on_delete=models.CASCADE,
        related_name='emi_schedules'
    )
    installment_number = models.IntegerField()
    installment_type = models.CharField(max_length=20, choices=INSTALLMENT_TYPE_CHOICES, default='emi')
    
    # Payment Details
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)  # Add this line

    due_date = models.DateField()
    paid_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Late Fee
    late_fee_applied = models.DecimalField(max_digits=8, decimal_places=2, default=0.00)
    days_overdue = models.IntegerField(default=0)
    
    # Tracking
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_reminder_sent = models.DateField(null=True, blank=True)
    late_fee_applied = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['installment_number']
        unique_together = ['fee_assignment', 'installment_number']
        verbose_name = "EMI Schedule"
        verbose_name_plural = "EMI Schedules"
    
    def __str__(self):
        return f"{self.fee_assignment.student.get_full_name()} - EMI {self.installment_number}"
    
    def save(self, *args, **kwargs):
        # Calculate days overdue
        if self.status == 'pending' and self.due_date < date.today():
            self.days_overdue = (date.today() - self.due_date).days
            self.status = 'overdue'
        
        super().save(*args, **kwargs)
    
    def mark_as_paid(self, payment_date=None):
        """Mark this EMI as paid"""
        self.status = 'paid'
        self.paid_date = payment_date or date.today()
        self.save()
        
        # Update fee assignment amount paid
        assignment = self.fee_assignment
        assignment.amount_paid += self.amount
        assignment.save()
    
    def calculate_late_fee(self):
        """Calculate late fee if overdue"""
        if self.status != 'overdue' or self.late_fee_applied > 0:
            return 0
        
        fee_structure = self.fee_assignment.fee_structure
        
        # Fixed late fee
        late_fee = fee_structure.late_fee_amount
        
        # Percentage-based late fee
        if fee_structure.late_fee_percentage > 0:
            percentage_fee = (self.amount * fee_structure.late_fee_percentage) / 100
            late_fee += percentage_fee
        
        self.late_fee_applied = late_fee
        self.save()
        
        return late_fee

# fees/models.py में add करें

class DailyTaskLog(models.Model):
    """Log daily automated task results"""
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('running', 'Running'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]
    
    run_date = models.DateField(default=date.today)
    run_time = models.TimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Task results
    courses_locked = models.IntegerField(default=0)
    courses_unlocked = models.IntegerField(default=0)
    late_fees_applied = models.IntegerField(default=0)
    reminders_sent = models.IntegerField(default=0)
    
    # Additional info
    total_overdue_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    error_message = models.TextField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['run_date']
        ordering = ['-run_date']
    
    def __str__(self):
        return f"Daily Tasks - {self.run_date} ({self.status})"
    
class PaymentRecord(models.Model):
    """Track all payments made by students"""
    
    PAYMENT_METHOD_CHOICES = [
        ('online', 'Online Payment'),
        ('cash', 'Cash'),
        ('cheque', 'Cheque'),
        ('bank_transfer', 'Bank Transfer'),
        ('upi', 'UPI'),
        ('card', 'Credit/Debit Card'),
        ('other', 'Other'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
    ]
    
    # Basic Details
    payment_id = models.CharField(max_length=50, unique=True, default=uuid.uuid4)
    fee_assignment = models.ForeignKey(
        StudentFeeAssignment, on_delete=models.CASCADE,
        related_name='payments'
    )
    emi_schedule = models.ForeignKey(
        EMISchedule, on_delete=models.SET_NULL, null=True, blank=True,
        help_text="Link to specific EMI if applicable"
    )
    
    # Payment Details
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES)
    payment_date = models.DateField()
    payment_time = models.DateTimeField(auto_now_add=True)
    
    # Transaction Details
    transaction_id = models.CharField(max_length=100, blank=True)
    reference_number = models.CharField(max_length=100, blank=True)
    bank_name = models.CharField(max_length=100, blank=True)
    cheque_number = models.CharField(max_length=50, blank=True)
    
    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Admin Notes
    notes = models.TextField(blank=True, help_text="Admin notes about this payment")
    receipt_number = models.CharField(max_length=50, blank=True)
    
    # Tracking
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    recorded_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True,
        related_name='recorded_payments'
    )
    
    class Meta:
        ordering = ['-payment_date', '-payment_time']
        verbose_name = "Payment Record"
        verbose_name_plural = "Payment Records"
    
    def __str__(self):
        return f"{self.fee_assignment.student.get_full_name()} - ${self.amount} ({self.payment_date})"
    
    def save(self, *args, **kwargs):
        # Generate receipt number if not provided
        if not self.receipt_number and self.status == 'completed':
            self.receipt_number = f"RCP{self.payment_date.strftime('%Y%m%d')}{self.id or '001'}"
        
        super().save(*args, **kwargs)
        
        # Update fee assignment if payment is completed
        if self.status == 'completed':
            self.update_fee_assignment()
    
    def update_fee_assignment(self):
        """Update fee assignment with this payment"""
        assignment = self.fee_assignment
        assignment.amount_paid += self.amount
        assignment.save()
        
        # Mark corresponding EMI as paid if linked
        if self.emi_schedule:
            self.emi_schedule.mark_as_paid(self.payment_date)


class BatchAccessControl(models.Model):
    """Control access to specific batches for fee defaulters"""
    
    ACCESS_TYPE_CHOICES = [
        ('locked', 'Locked'),
        ('unlocked', 'Unlocked'),
        ('restricted', 'Restricted'),
    ]
    
    # Basic Details
    student = models.ForeignKey(
        User, on_delete=models.CASCADE,
        limit_choices_to={'role': 'student'},
        related_name='batch_access_controls'
    )
    batch = models.ForeignKey(
        'courses.Batch', on_delete=models.CASCADE,
        related_name='access_controls'
    )
    
    # Access Control
    access_type = models.CharField(max_length=20, choices=ACCESS_TYPE_CHOICES, default='unlocked')
    reason = models.TextField(help_text="Reason for access control")
    
    # Dates
    effective_from = models.DateField(default=date.today)
    effective_until = models.DateField(null=True, blank=True)
    
    # Admin Control
    override_access = models.BooleanField(default=False, help_text="Admin override to unlock")
    override_reason = models.TextField(blank=True)
    override_until = models.DateField(null=True, blank=True)
    
    # Tracking
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True,
        related_name='created_batch_controls'
    )
    
    class Meta:
        unique_together = ['student', 'batch']
        ordering = ['-created_at']
        verbose_name = "Batch Access Control"
        verbose_name_plural = "Batch Access Controls"
    
    def __str__(self):
        return f"{self.student.get_full_name()} - {self.batch.name} ({self.access_type})"
    
    def is_access_allowed(self):
        """Check if student can access this batch"""
        today = date.today()
        
        # Check admin override first
        if self.override_access:
            if not self.override_until or today <= self.override_until:
                return True
        
        # Check regular access control
        if self.access_type == 'unlocked':
            return True
        elif self.access_type == 'locked':
            return False
        elif self.access_type == 'restricted':
            # Custom logic for restricted access
            return False
        
        return True


class PaymentReminder(models.Model):
    """Track payment reminders sent to students"""
    
    REMINDER_TYPE_CHOICES = [
        ('due_soon', 'Payment Due Soon'),
        ('overdue', 'Payment Overdue'),
        ('final_notice', 'Final Notice'),
        ('course_lock_warning', 'Course Lock Warning'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('sent', 'Sent'),
        ('failed', 'Failed'),
    ]
    
    # Basic Details
    emi_schedule = models.ForeignKey(
        EMISchedule, on_delete=models.CASCADE,
        related_name='reminders'
    )
    reminder_type = models.CharField(max_length=20, choices=REMINDER_TYPE_CHOICES)
    
    # Reminder Details
    scheduled_date = models.DateField()
    sent_date = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Content
    subject = models.CharField(max_length=200)
    message = models.TextField()
    
    # Tracking
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-scheduled_date']
        verbose_name = "Payment Reminder"
        verbose_name_plural = "Payment Reminders"
    
    def __str__(self):
        return f"{self.emi_schedule.fee_assignment.student.get_full_name()} - {self.reminder_type}"
    
    def mark_as_sent(self):
        """Mark reminder as sent"""
        self.status = 'sent'
        self.sent_date = timezone.now()
        self.save()


class FeeDiscount(models.Model):
    """Manage discounts for students"""
    
    DISCOUNT_TYPE_CHOICES = [
        ('percentage', 'Percentage'),
        ('fixed', 'Fixed Amount'),
    ]
    
    # Basic Details
    name = models.CharField(max_length=200)
    code = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True)
    
    # Discount Details
    discount_type = models.CharField(max_length=20, choices=DISCOUNT_TYPE_CHOICES)
    discount_value = models.DecimalField(max_digits=10, decimal_places=2)
    max_discount_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
    # Validity
    valid_from = models.DateField()
    valid_until = models.DateField()
    usage_limit = models.IntegerField(null=True, blank=True, help_text="Max number of uses")
    used_count = models.IntegerField(default=0)
    
    # Conditions
    minimum_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    applicable_courses = models.ManyToManyField('courses.Course', blank=True)
    
    # Status
    is_active = models.BooleanField(default=True)
    
    # Tracking
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True
    )
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Fee Discount"
        verbose_name_plural = "Fee Discounts"
    
    def __str__(self):
        return f"{self.name} ({self.code})"
    
    def is_valid(self):
        """Check if discount is currently valid"""
        today = date.today()
        return (
            self.is_active and
            self.valid_from <= today <= self.valid_until and
            (not self.usage_limit or self.used_count < self.usage_limit)
        )
    
    def calculate_discount(self, amount):
        """Calculate discount amount"""
        if not self.is_valid() or amount < self.minimum_amount:
            return 0
        
        if self.discount_type == 'percentage':
            discount = (amount * self.discount_value) / 100
            if self.max_discount_amount:
                discount = min(discount, self.max_discount_amount)
        else:
            discount = self.discount_value
        
        return min(discount, amount)


class DiscountUsage(models.Model):
    """Track discount usage by students"""
    
    discount = models.ForeignKey(FeeDiscount, on_delete=models.CASCADE, related_name='usages')
    fee_assignment = models.ForeignKey(StudentFeeAssignment, on_delete=models.CASCADE)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2)
    applied_date = models.DateTimeField(auto_now_add=True)
    applied_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    
    class Meta:
        unique_together = ['discount', 'fee_assignment']
        verbose_name = "Discount Usage"
        verbose_name_plural = "Discount Usages"
    
    def __str__(self):
        return f"{self.discount.name} - {self.fee_assignment.student.get_full_name()}"