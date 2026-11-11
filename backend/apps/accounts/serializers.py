from django.contrib.auth import password_validation
from rest_framework import serializers
from .models import User


class RegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[password_validation.validate_password])

    class Meta:
        model = User
        fields = ('id', 'email', 'first_name', 'last_name', 'mobile_number', 'password')
        read_only_fields = ('id',)

    def create(self, validated_data):
        return User.objects.create_user(**validated_data, role=User.Role.CITIZEN)


class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'email', 'first_name', 'last_name', 'mobile_number', 'role')
        read_only_fields = ('id', 'email', 'role')
