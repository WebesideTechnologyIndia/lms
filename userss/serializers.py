from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from .models import CustomUser, PasswordResetOTP


class PasswordResetRequestSerializer(serializers.Serializer):
    """Serializer for password reset request"""
    email = serializers.EmailField()
    
    def validate_email(self, value):
        try:
            user = CustomUser.objects.get(email=value)
        except CustomUser.DoesNotExist:
            raise serializers.ValidationError("User with this email does not exist.")
        return value


class PasswordResetVerifySerializer(serializers.Serializer):
    """Serializer for OTP verification"""
    email = serializers.EmailField()
    otp = serializers.CharField(max_length=6, min_length=6)
    
    def validate(self, attrs):
        email = attrs.get('email')
        otp = attrs.get('otp')
        
        try:
            user = CustomUser.objects.get(email=email)
        except CustomUser.DoesNotExist:
            raise serializers.ValidationError("User with this email does not exist.")
        
        try:
            otp_instance = PasswordResetOTP.objects.get(
                user=user, 
                otp=otp, 
                is_used=False
            )
            
            if not otp_instance.is_valid():
                raise serializers.ValidationError("OTP has expired or is invalid.")
                
        except PasswordResetOTP.DoesNotExist:
            raise serializers.ValidationError("Invalid OTP.")
        
        attrs['user'] = user
        attrs['otp_instance'] = otp_instance
        return attrs


class PasswordResetConfirmSerializer(serializers.Serializer):
    """Serializer for password reset confirmation"""
    email = serializers.EmailField()
    otp = serializers.CharField(max_length=6, min_length=6)
    new_password = serializers.CharField(write_only=True, min_length=8)
    confirm_password = serializers.CharField(write_only=True, min_length=8)
    
    def validate_new_password(self, value):
        try:
            validate_password(value)
        except ValidationError as e:
            raise serializers.ValidationError(list(e.messages))
        return value
    
    def validate(self, attrs):
        email = attrs.get('email')
        otp = attrs.get('otp')
        new_password = attrs.get('new_password')
        confirm_password = attrs.get('confirm_password')
        
        if new_password != confirm_password:
            raise serializers.ValidationError("Passwords do not match.")
        
        try:
            user = CustomUser.objects.get(email=email)
        except CustomUser.DoesNotExist:
            raise serializers.ValidationError("User with this email does not exist.")
        
        try:
            otp_instance = PasswordResetOTP.objects.get(
                user=user, 
                otp=otp, 
                is_used=False
            )
            
            if not otp_instance.is_valid():
                raise serializers.ValidationError("OTP has expired or is invalid.")
                
        except PasswordResetOTP.DoesNotExist:
            raise serializers.ValidationError("Invalid OTP.")
        
        attrs['user'] = user
        attrs['otp_instance'] = otp_instance
        return attrs