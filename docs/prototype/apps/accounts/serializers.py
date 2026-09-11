from django.contrib.auth import get_user_model
from rest_framework import serializers

from .models import ReaderProfile

User = get_user_model()


class RegisterSerializer(serializers.ModelSerializer):
    """UC-6.1 Register Account — always creates a plain Reader + ReaderProfile.
    Staff accounts are provisioned by an Admin via UC-5.1 Add New User, not
    self-registration."""

    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = ["id", "email", "password", "first_name", "last_name"]

    def create(self, validated_data):
        password = validated_data.pop("password")
        user = User.objects.create_user(password=password, role=User.Role.READER, **validated_data)
        ReaderProfile.objects.create(user=user)
        return user


class ReaderProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReaderProfile
        fields = ["tier", "subscription_started_at", "subscription_renews_at"]
        read_only_fields = fields


class UserSerializer(serializers.ModelSerializer):
    """UC-6.4 Update Profile Information + `me` endpoint."""

    reader_profile = ReaderProfileSerializer(read_only=True)

    class Meta:
        model = User
        fields = [
            "id", "email", "first_name", "last_name", "role",
            "is_suspended", "reader_profile",
        ]
        read_only_fields = ["role", "is_suspended"]
