import re
from django.contrib.auth import password_validation
from django.db import IntegrityError, transaction
from rest_framework import serializers
from .models import User


class RegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[password_validation.validate_password])
    confirm_password = serializers.CharField(write_only=True)
    first_name = serializers.CharField(required=True, allow_blank=False, max_length=150)
    last_name = serializers.CharField(required=True, allow_blank=False, max_length=150)
    mobile_number = serializers.CharField(required=True, allow_blank=False, max_length=20)

    class Meta:
        model = User
        fields = ('id', 'email', 'first_name', 'last_name', 'mobile_number', 'password', 'confirm_password')
        read_only_fields = ('id',)

    def validate_mobile_number(self, value):
        normalized = re.sub(r'[\s().-]', '', value.strip())
        if not re.fullmatch(r'\+?[0-9]{7,15}', normalized):
            raise serializers.ValidationError('Enter a valid mobile number with 7 to 15 digits.')
        return normalized

    def validate_email(self, value):
        normalized = value.strip().lower()
        if User.objects.filter(email__iexact=normalized).exists():
            raise serializers.ValidationError('A user with this email address already exists.')
        return normalized

    def validate(self, attrs):
        if attrs['password'] != attrs['confirm_password']:
            raise serializers.ValidationError({'confirm_password': 'Passwords do not match.'})
        return attrs

    def create(self, validated_data):
        validated_data.pop('confirm_password')
        try:
            with transaction.atomic():
                return User.objects.create_user(**validated_data, role=User.Role.CITIZEN)
        except IntegrityError as exc:
            if User.objects.filter(email__iexact=validated_data['email']).exists():
                raise serializers.ValidationError({
                    'email': 'A user with this email address already exists.',
                }) from exc
            raise


class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'email', 'first_name', 'last_name', 'mobile_number', 'role')
        read_only_fields = ('id', 'email', 'role')
