# fees/forms.py - Complete Fees Management Forms

from django import forms
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils import timezone
from .models import (
    FeeStructure, StudentFeeAssignment, PaymentRecord, 
    EMISchedule, BatchAccessControl, FeeDiscount,
    DiscountUsage
)
from courses.models import Course, Batch
from datetime import date, timedelta

User = get_user_model()


class FeeStructureForm(forms.ModelForm):
    """Form for creating and editing fee structures"""
    
    class Meta:
        model = FeeStructure
        fields = [
            'name', 'code', 'description', 'total_amount', 'payment_type',
            'emi_duration_months', 'emi_amount', 'down_payment',
            'grace_period_days', 'late_fee_amount', 'late_fee_percentage',
            'early_payment_discount', 'bulk_discount', 'is_active', 'is_default'
        ]
        
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., Standard EMI Plan, Full Payment Plan'
            }),
            'code': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., STD_EMI_6M'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Description of this fee structure...'
            }),
            'total_amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0'
            }),
            'payment_type': forms.Select(attrs={'class': 'form-select'}),
            'emi_duration_months': forms.Select(attrs={'class': 'form-select'}),
            'emi_amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0'
            }),
            'down_payment': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0',
                'value': '0.00'
            }),
            'grace_period_days': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'value': '3'
            }),
            'late_fee_amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0',
                'value': '0.00'
            }),
            'late_fee_percentage': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0',
                'max': '100',
                'value': '0.00'
            }),
            'early_payment_discount': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0',
                'max': '100',
                'value': '0.00'
            }),
            'bulk_discount': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0',
                'max': '100',
                'value': '0.00'
            }),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_default': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add help text
        self.fields['payment_type'].help_text = "Select payment method type"
        self.fields['emi_duration_months'].help_text = "Required for EMI plans"
        self.fields['emi_amount'].help_text = "Auto-calculated if left empty for EMI plans"
        self.fields['grace_period_days'].help_text = "Days after due date before course lock"
        
        # Make fields conditional based on payment type
        self.fields['emi_duration_months'].required = False
        self.fields['emi_amount'].required = False
    
    def clean(self):
        cleaned_data = super().clean()
        payment_type = cleaned_data.get('payment_type')
        total_amount = cleaned_data.get('total_amount', 0)
        emi_duration = cleaned_data.get('emi_duration_months')
        emi_amount = cleaned_data.get('emi_amount')
        down_payment = cleaned_data.get('down_payment', 0)
        
        # Validation for EMI plans
        if payment_type == 'emi':
            if not emi_duration:
                raise ValidationError("EMI duration is required for EMI payment plans")
            
            # Auto-calculate EMI amount if not provided
            if not emi_amount:
                remaining_amount = total_amount - down_payment
                if remaining_amount > 0 and emi_duration:
                    cleaned_data['emi_amount'] = remaining_amount / emi_duration
        
        # Validate down payment
        if down_payment >= total_amount:
            raise ValidationError("Down payment cannot be greater than or equal to total amount")
        
        return cleaned_data


class StudentFeeAssignmentForm(forms.ModelForm):
    """Form for assigning fee structure to students"""
    
    class Meta:
        model = StudentFeeAssignment
        fields = [
            'student', 'course', 'fee_structure', 'total_amount',
            'payment_start_date', 'status', 'unlock_date'
        ]
        
        widgets = {
            'student': forms.Select(attrs={'class': 'form-select'}),
            'course': forms.Select(attrs={'class': 'form-select'}),
            'fee_structure': forms.Select(attrs={'class': 'form-select'}),
            'total_amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0'
            }),
            'payment_start_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'unlock_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Filter students - only active students
        self.fields['student'].queryset = User.objects.filter(
            role='student',
            is_active=True
        ).order_by('first_name', 'last_name')
        
        # Filter courses - only active courses
        self.fields['course'].queryset = Course.objects.filter(
            is_active=True,
            status='published'
        ).order_by('title')
        
        # Filter fee structures - only active ones
        self.fields['fee_structure'].queryset = FeeStructure.objects.filter(
            is_active=True
        ).order_by('name')
        
        # Set default payment start date
        self.fields['payment_start_date'].initial = date.today()
        
        # Help text
        self.fields['unlock_date'].help_text = "Set future date to unlock course even if payment pending"
    
    def clean(self):
        cleaned_data = super().clean()
        student = cleaned_data.get('student')
        course = cleaned_data.get('course')
        
        # Check if student is already assigned to this course
        if student and course:
            existing = StudentFeeAssignment.objects.filter(
                student=student,
                course=course
            ).exclude(pk=self.instance.pk if self.instance else None)
            
            if existing.exists():
                raise ValidationError(
                    f"Fee assignment already exists for {student.get_full_name()} in {course.title}"
                )
        
        return cleaned_data

class PaymentRecordForm(forms.ModelForm):
    """Form for recording payments"""
    
    class Meta:
        model = PaymentRecord
        fields = [
            'fee_assignment', 'emi_schedule', 'amount', 'payment_method',
            'payment_date', 'transaction_id', 'reference_number',
            'bank_name', 'cheque_number', 'status', 'notes'
        ]
        
        widgets = {
            'fee_assignment': forms.Select(attrs={'class': 'form-select'}),
            'emi_schedule': forms.Select(attrs={'class': 'form-select'}),
            'amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0.01'
            }),
            'payment_method': forms.Select(attrs={'class': 'form-select'}),
            'payment_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'transaction_id': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Transaction ID (for online payments)'
            }),
            'reference_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Reference number'
            }),
            'bank_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Bank name (for cheque/transfer)'
            }),
            'cheque_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Cheque number'
            }),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Additional notes about this payment...'
            }),
        }
    
    def __init__(self, *args, student=None, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Set default payment date
        self.fields['payment_date'].initial = date.today()
        
        # Filter fee assignments based on student
        if student:
            self.fields['fee_assignment'].queryset = StudentFeeAssignment.objects.filter(
                student=student,
                status='active'
            ).select_related('course', 'fee_structure')
        else:
            self.fields['fee_assignment'].queryset = StudentFeeAssignment.objects.filter(
                status='active'
            ).select_related('student', 'course')
        
        # EMI schedule will be populated via AJAX based on fee assignment
        self.fields['emi_schedule'].queryset = EMISchedule.objects.none()
        self.fields['emi_schedule'].required = False
        
        # Help text
        self.fields['emi_schedule'].help_text = "Select specific EMI (optional)"
        self.fields['transaction_id'].help_text = "Required for online payments"
    
    def clean_emi_schedule(self):
        """Custom validation for EMI schedule"""
        emi_schedule = self.cleaned_data.get('emi_schedule')
        fee_assignment = self.cleaned_data.get('fee_assignment')
        
        # If EMI schedule is selected, validate it belongs to the fee assignment
        if emi_schedule and fee_assignment:
            if emi_schedule.fee_assignment != fee_assignment:
                raise ValidationError("Selected EMI does not belong to the chosen fee assignment.")
        
        return emi_schedule
    
    def clean(self):
        cleaned_data = super().clean()
        payment_method = cleaned_data.get('payment_method')
        transaction_id = cleaned_data.get('transaction_id')
        cheque_number = cleaned_data.get('cheque_number')
        bank_name = cleaned_data.get('bank_name')
        fee_assignment = cleaned_data.get('fee_assignment')
        emi_schedule = cleaned_data.get('emi_schedule')
        
        # Validation based on payment method
        if payment_method in ['online', 'upi', 'card'] and not transaction_id:
            raise ValidationError("Transaction ID is required for online payments")
        
        if payment_method == 'cheque' and not cheque_number:
            raise ValidationError("Cheque number is required for cheque payments")
        
        if payment_method in ['cheque', 'bank_transfer'] and not bank_name:
            raise ValidationError("Bank name is required for cheque/bank transfer payments")
        
        # Validate EMI schedule belongs to fee assignment if both are selected
        if emi_schedule and fee_assignment:
            if emi_schedule.fee_assignment != fee_assignment:
                raise ValidationError("Selected EMI does not belong to the chosen fee assignment.")
        
        return cleaned_data

class QuickPaymentForm(forms.Form):
    """Quick payment form for common scenarios"""
    
    PAYMENT_TYPE_CHOICES = [
        ('full_course', 'Full Course Payment'),
        ('current_emi', 'Current EMI Payment'),
        ('overdue_emis', 'All Overdue EMIs'),
        ('custom', 'Custom Amount'),
    ]
    
    fee_assignment = forms.ModelChoiceField(
        queryset=StudentFeeAssignment.objects.filter(status='active'),
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    payment_type = forms.ChoiceField(
        choices=PAYMENT_TYPE_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    custom_amount = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': '0.01',
            'min': '0.01'
        })
    )
    
    payment_method = forms.ChoiceField(
        choices=PaymentRecord.PAYMENT_METHOD_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    payment_date = forms.DateField(
        initial=date.today,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
    
    transaction_id = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Transaction ID'
        })
    )
    
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 2,
            'placeholder': 'Payment notes...'
        })
    )
    
    def __init__(self, *args, student=None, **kwargs):
        super().__init__(*args, **kwargs)
        
        if student:
            self.fields['fee_assignment'].queryset = StudentFeeAssignment.objects.filter(
                student=student,
                status='active'
            ).select_related('course', 'fee_structure')
    
    def clean(self):
        cleaned_data = super().clean()
        payment_type = cleaned_data.get('payment_type')
        custom_amount = cleaned_data.get('custom_amount')
        
        if payment_type == 'custom' and not custom_amount:
            raise ValidationError("Custom amount is required when payment type is 'Custom Amount'")
        
        return cleaned_data


class BatchAccessControlForm(forms.ModelForm):
    """Form for controlling batch access"""
    
    class Meta:
        model = BatchAccessControl
        fields = [
            'student', 'batch', 'access_type', 'reason',
            'effective_from', 'effective_until', 'override_access',
            'override_reason', 'override_until'
        ]
        
        widgets = {
            'student': forms.Select(attrs={'class': 'form-select'}),
            'batch': forms.Select(attrs={'class': 'form-select'}),
            'access_type': forms.Select(attrs={'class': 'form-select'}),
            'reason': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Reason for access control...'
            }),
            'effective_from': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'effective_until': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'override_access': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'override_reason': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Admin override reason...'
            }),
            'override_until': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
        }
    
    def __init__(self, *args, course=None, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Filter students
        self.fields['student'].queryset = User.objects.filter(
            role='student',
            is_active=True
        ).order_by('first_name', 'last_name')
        
        # Filter batches based on course
        if course:
            self.fields['batch'].queryset = Batch.objects.filter(
                course=course,
                is_active=True
            ).order_by('name')
        else:
            self.fields['batch'].queryset = Batch.objects.filter(
                is_active=True
            ).order_by('course__title', 'name')
        
        # Set default dates
        self.fields['effective_from'].initial = date.today()
        
        # Help text
        self.fields['override_access'].help_text = "Admin can temporarily unlock access"
        self.fields['override_until'].help_text = "Override valid until this date"


class FeeDiscountForm(forms.ModelForm):
    """Form for creating fee discounts"""
    
    class Meta:
        model = FeeDiscount
        fields = [
            'name', 'code', 'description', 'discount_type', 'discount_value',
            'max_discount_amount', 'valid_from', 'valid_until', 'usage_limit',
            'minimum_amount', 'applicable_courses', 'is_active'
        ]
        
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., Early Bird Discount, Student Discount'
            }),
            'code': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., EARLY2024, STUDENT10'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Description of this discount...'
            }),
            'discount_type': forms.Select(attrs={'class': 'form-select'}),
            'discount_value': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0'
            }),
            'max_discount_amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0'
            }),
            'valid_from': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'valid_until': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'usage_limit': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '1'
            }),
            'minimum_amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0',
                'value': '0.00'
            }),
            'applicable_courses': forms.SelectMultiple(attrs={
                'class': 'form-select',
                'size': '4'
            }),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Filter courses
        self.fields['applicable_courses'].queryset = Course.objects.filter(
            is_active=True,
            status='published'
        ).order_by('title')
        
        # Set default dates
        self.fields['valid_from'].initial = date.today()
        self.fields['valid_until'].initial = date.today() + timedelta(days=30)
        
        # Help text
        self.fields['max_discount_amount'].help_text = "Maximum discount amount (for percentage discounts)"
        self.fields['usage_limit'].help_text = "Leave empty for unlimited usage"
        self.fields['applicable_courses'].help_text = "Leave empty to apply to all courses"
    
    def clean(self):
        cleaned_data = super().clean()
        valid_from = cleaned_data.get('valid_from')
        valid_until = cleaned_data.get('valid_until')
        discount_type = cleaned_data.get('discount_type')
        discount_value = cleaned_data.get('discount_value')
        
        # Date validation
        if valid_from and valid_until and valid_from >= valid_until:
            raise ValidationError("Valid until date must be after valid from date")
        
        # Discount value validation
        if discount_type == 'percentage' and discount_value > 100:
            raise ValidationError("Percentage discount cannot be more than 100%")
        
        return cleaned_data


class FeeReportForm(forms.Form):
    """Form for generating fee reports"""
    
    REPORT_TYPE_CHOICES = [
        ('payment_summary', 'Payment Summary'),
        ('overdue_payments', 'Overdue Payments'),
        ('collection_report', 'Collection Report'),
        ('student_wise', 'Student-wise Report'),
        ('course_wise', 'Course-wise Report'),
    ]
    
    report_type = forms.ChoiceField(
        choices=REPORT_TYPE_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    date_from = forms.DateField(
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
    
    date_to = forms.DateField(
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
    
    course = forms.ModelChoiceField(
        queryset=Course.objects.filter(is_active=True),
        required=False,
        empty_label="All Courses",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    student = forms.ModelChoiceField(
        queryset=User.objects.filter(role='student', is_active=True),
        required=False,
        empty_label="All Students",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    status = forms.ChoiceField(
        choices=[('', 'All Status')] + list(StudentFeeAssignment.STATUS_CHOICES),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Set default date range (last 30 days)
        self.fields['date_to'].initial = date.today()
        self.fields['date_from'].initial = date.today() - timedelta(days=30)
    
    def clean(self):
        cleaned_data = super().clean()
        date_from = cleaned_data.get('date_from')
        date_to = cleaned_data.get('date_to')
        
        if date_from and date_to and date_from > date_to:
            raise ValidationError("From date cannot be after to date")
        
        return cleaned_data


class BulkPaymentUpdateForm(forms.Form):
    """Form for bulk payment operations"""
    
    ACTION_CHOICES = [
        ('mark_paid', 'Mark as Paid'),
        ('send_reminder', 'Send Payment Reminder'),
        ('apply_late_fee', 'Apply Late Fee'),
        ('waive_late_fee', 'Waive Late Fee'),
        ('extend_due_date', 'Extend Due Date'),
    ]
    
    emi_schedules = forms.ModelMultipleChoiceField(
        queryset=EMISchedule.objects.all(),
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'})
    )
    
    action = forms.ChoiceField(
        choices=ACTION_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    payment_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
    
    new_due_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
    
    payment_method = forms.ChoiceField(
        choices=[('', 'Select Method')] + list(PaymentRecord.PAYMENT_METHOD_CHOICES),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Notes for this bulk operation...'
        })
    )
    
    def clean(self):
        cleaned_data = super().clean()
        action = cleaned_data.get('action')
        payment_date = cleaned_data.get('payment_date')
        new_due_date = cleaned_data.get('new_due_date')
        payment_method = cleaned_data.get('payment_method')
        
        # Action-specific validations
        if action == 'mark_paid':
            if not payment_date:
                raise ValidationError("Payment date is required for marking as paid")
            if not payment_method:
                raise ValidationError("Payment method is required for marking as paid")
        
        if action == 'extend_due_date' and not new_due_date:
            raise ValidationError("New due date is required for extending due date")
        
        return cleaned_data


class FeeFilterForm(forms.Form):
    """Form for filtering fee assignments and payments"""
    
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search students, courses...'
        })
    )
    
    course = forms.ModelChoiceField(
        queryset=Course.objects.filter(is_active=True),
        required=False,
        empty_label="All Courses",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    status = forms.ChoiceField(
        choices=[('', 'All Status')] + list(StudentFeeAssignment.STATUS_CHOICES),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    payment_status = forms.ChoiceField(
        choices=[
            ('', 'All Payment Status'),
            ('paid', 'Fully Paid'),
            ('partial', 'Partially Paid'),
            ('pending', 'Payment Pending'),
            ('overdue', 'Overdue'),
        ],
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    fee_structure = forms.ModelChoiceField(
        queryset=FeeStructure.objects.filter(is_active=True),
        required=False,
        empty_label="All Fee Structures",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
    
    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )