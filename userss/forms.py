# userss/forms.py - COMPLETELY CLEAN VERSION

from django import forms
from django.core.exceptions import ValidationError
from .models import CustomUser, UserProfile

class UserCreationForm(forms.Form):
    """Completely independent user creation form - NOT inheriting from ModelForm"""
    
    username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Username'
        })
    )
    first_name = forms.CharField(
        max_length=30,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'First Name'
        })
    )
    last_name = forms.CharField(
        max_length=30,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Last Name'
        })
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Email Address'
        })
    )
    role = forms.ChoiceField(
        choices=CustomUser.ROLE_CHOICES,
        widget=forms.Select(attrs={
            'class': 'form-control'
        })
    )
    password1 = forms.CharField(
        min_length=8,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Password'
        })
    )
    password2 = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirm Password'
        })
    )

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if not username:
            raise ValidationError("Username is required.")
        
        # Direct database query using CustomUser
        if CustomUser.objects.filter(username__iexact=username).exists():
            raise ValidationError("A user with this username already exists.")
        
        return username

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if not email:
            raise ValidationError("Email is required.")
        
        # Direct database query using CustomUser
        if CustomUser.objects.filter(email__iexact=email).exists():
            raise ValidationError("A user with this email address already exists.")
        
        return email.lower()

    def clean_password2(self):
        password1 = self.cleaned_data.get('password1')
        password2 = self.cleaned_data.get('password2')
        
        if not password2:
            raise ValidationError("Please confirm your password.")
        
        if password1 and password2 and password1 != password2:
            raise ValidationError("The two password fields didn't match.")
        
        return password2

    def save(self):
        """Create and return a new CustomUser"""
        cleaned_data = self.cleaned_data
        
        user = CustomUser(
            username=cleaned_data['username'].lower(),
            first_name=cleaned_data['first_name'],
            last_name=cleaned_data['last_name'],
            email=cleaned_data['email'].lower(),
            role=cleaned_data['role']
        )
        
        # Set password properly
        user.set_password(cleaned_data['password1'])
        user.save()
        
        return user


class UserUpdateForm(forms.ModelForm):
    """Form for updating existing users"""
    
    email = forms.EmailField(required=True)
    first_name = forms.CharField(max_length=30, required=True)
    last_name = forms.CharField(max_length=30, required=True)
    role = forms.ChoiceField(choices=CustomUser.ROLE_CHOICES, required=True)
    is_active = forms.BooleanField(required=False, label="Active User")

    class Meta:
        model = CustomUser
        fields = ('username', 'first_name', 'last_name', 'email', 'role', 'is_active')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add CSS classes for better styling
        for field_name, field in self.fields.items():
            if field_name != 'is_active':
                field.widget.attrs['class'] = 'form-control'
            else:
                field.widget.attrs['class'] = 'form-check-input'
        
        # Add placeholders
        self.fields['username'].widget.attrs['placeholder'] = 'Enter username'
        self.fields['first_name'].widget.attrs['placeholder'] = 'First Name'
        self.fields['last_name'].widget.attrs['placeholder'] = 'Last Name'
        self.fields['email'].widget.attrs['placeholder'] = 'Email address'


class StudentProfileForm(forms.ModelForm):
    """Form for student profile completion/update"""
    
    class Meta:
        model = CustomUser
        fields = [
            'first_name', 'last_name', 'email', 
            'phone_number', 'profile_picture', 
            'bio', 'date_of_birth', 'address'
        ]
        widgets = {
            'first_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter your first name',
                'required': True
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter your last name',
                'required': True
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter your email address',
                'required': True
            }),
            'phone_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter your phone number (optional)'
            }),
            'profile_picture': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*'
            }),
            'bio': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Tell us about yourself (optional)',
                'rows': 3
            }),
            'date_of_birth': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'address': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Enter your address (optional)',
                'rows': 2
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Mark required fields
        self.fields['first_name'].required = True
        self.fields['last_name'].required = True
        self.fields['email'].required = True


class UserProfileForm(forms.ModelForm):
    """Form for UserProfile model"""
    
    class Meta:
        model = UserProfile
        fields = [
            'student_id', 'department', 'year_of_study',
            'emergency_contact_name', 'emergency_contact_phone'
        ]
        widgets = {
            'student_id': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Student ID (auto-generated if left blank)',
                'readonly': 'readonly'
            }),
            'department': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter your department (optional)'
            }),
            'year_of_study': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Year of study (1-4)',
                'min': 1,
                'max': 10
            }),
            'emergency_contact_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Emergency contact name'
            }),
            'emergency_contact_phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Emergency contact phone'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # If student_id exists, make it readonly
        if self.instance and self.instance.student_id:
            self.fields['student_id'].widget.attrs['readonly'] = True