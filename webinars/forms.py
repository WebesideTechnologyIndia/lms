# webinars/forms.py

from django import forms
from django.contrib.auth import get_user_model
from .models import Webinar, WebinarRegistration, WebinarCategory, WebinarFeedback

User = get_user_model()

class WebinarRegistrationForm(forms.Form):
    """Public registration form for webinars"""
    
    first_name = forms.CharField(
        max_length=50,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Your first name',
            'required': True
        })
    )
    
    last_name = forms.CharField(
        max_length=50,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Your last name',
            'required': True
        })
    )
    
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Your email address',
            'required': True
        })
    )
    
    phone_number = forms.CharField(
        max_length=15,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Your phone number (optional)'
        })
    )
    
    company = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Company name (optional)'
        })
    )
    
    designation = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Your designation (optional)'
        })
    )
    
    agree_terms = forms.BooleanField(
        required=True,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        }),
        label="I agree to receive webinar updates and promotional emails"
    )
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email:
            return email.lower()
        return email



class WebinarForm(forms.ModelForm):
    """Admin form for creating/editing webinars"""
    
    class Meta:
        model = Webinar
        fields = [
            'title', 'category', 'webinar_type', 'price',
            'description', 'short_description', 'learning_outcomes', 'prerequisites',
            'scheduled_date', 'duration_minutes', 'max_attendees',
            'instructor', 'thumbnail', 'webinar_link', 'status',
            'send_reminder_emails', 'reminder_hours_before'
        ]
        
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter webinar title',
                'maxlength': '200'
            }),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'webinar_type': forms.Select(attrs={'class': 'form-select'}),
            'price': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Detailed webinar description'
            }),
            'short_description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Brief description for cards',
                'maxlength': '300'
            }),
            'learning_outcomes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'What attendees will learn'
            }),
            'prerequisites': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'What attendees should know (optional)'
            }),
            'scheduled_date': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local'
            }),
            'duration_minutes': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '15',
                'max': '480'
            }),
            'max_attendees': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '1',
                'value': '100'
            }),
            'instructor': forms.Select(attrs={'class': 'form-select'}),
            'thumbnail': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*'
            }),
            'webinar_link': forms.URLInput(attrs={
                'class': 'form-control',
                'placeholder': 'Zoom/Meet/Teams link'
            }),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'send_reminder_emails': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'reminder_hours_before': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '1',
                'max': '168',
                'value': '24'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Filter instructors
        self.fields['instructor'].queryset = User.objects.filter(
            role__in=['instructor', 'superadmin'],
            is_active=True
        )
        
        # Make some fields optional
        self.fields['price'].required = False
        self.fields['webinar_link'].required = False
        self.fields['prerequisites'].required = False
        self.fields['send_reminder_emails'].required = False
        self.fields['reminder_hours_before'].required = False
        
        # Set default values for new forms
        if not self.instance.pk:
            self.fields['max_attendees'].initial = 100
            self.fields['reminder_hours_before'].initial = 24
            self.fields['send_reminder_emails'].initial = True
    
    def clean(self):
        cleaned_data = super().clean()
        webinar_type = cleaned_data.get('webinar_type')
        price = cleaned_data.get('price')
        
        # Handle pricing
        if webinar_type == 'free':
            cleaned_data['price'] = 0
        elif webinar_type == 'paid' and (not price or price <= 0):
            raise forms.ValidationError("Paid webinars must have a price greater than 0")
        
        # Validate scheduled date
        scheduled_date = cleaned_data.get('scheduled_date')
        if scheduled_date:
            from django.utils import timezone
            if scheduled_date <= timezone.now():
                raise forms.ValidationError("Scheduled date must be in the future")
        
        return cleaned_data




class WebinarFeedbackForm(forms.ModelForm):
    """Feedback form for webinar attendees"""
    
    class Meta:
        model = WebinarFeedback
        fields = [
            'content_rating', 'instructor_rating', 'overall_rating',
            'what_you_liked', 'suggestions_for_improvement',
            'would_recommend', 'interested_in_similar_webinars', 'interested_in_paid_courses'
        ]
        
        widgets = {
            'content_rating': forms.Select(attrs={'class': 'form-select'}),
            'instructor_rating': forms.Select(attrs={'class': 'form-select'}),
            'overall_rating': forms.Select(attrs={'class': 'form-select'}),
            'what_you_liked': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'What did you like most about this webinar?'
            }),
            'suggestions_for_improvement': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'How can we improve future webinars?'
            }),
            'would_recommend': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'interested_in_similar_webinars': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'interested_in_paid_courses': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }


class WebinarSearchForm(forms.Form):
    """Search form for webinar listing"""
    
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search webinars...'
        })
    )
    
    category = forms.ModelChoiceField(
        queryset=WebinarCategory.objects.filter(is_active=True),
        required=False,
        empty_label="All Categories",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    webinar_type = forms.ChoiceField(
        choices=[('', 'All Types')] + Webinar.WEBINAR_TYPE_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    status = forms.ChoiceField(
        choices=[('', 'All Status')] + Webinar.STATUS_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
