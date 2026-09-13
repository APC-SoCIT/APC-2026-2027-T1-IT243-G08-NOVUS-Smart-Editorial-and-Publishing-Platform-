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


class UpdateProfileSerializer(serializers.ModelSerializer):
    """UC-6.4 Update Profile Information.

    Email is the sign-in identifier, so changing it changes how the account
    authenticates. Requiring the current password means an unattended session
    cannot quietly move an account to an address its owner does not control —
    which is the usual first step in taking one over.

    Name changes need no password: they identify the person to colleagues,
    not to the system.
    """

    current_password = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = User
        fields = ["first_name", "last_name", "email", "current_password"]

    def validate(self, attrs):
        user = self.instance
        new_email = attrs.get("email")

        if new_email and new_email.lower() != user.email.lower():
            password = attrs.get("current_password")
            if not password:
                raise serializers.ValidationError({
                    "current_password":
                        "Enter your current password to change your email address."
                })
            if not user.check_password(password):
                raise serializers.ValidationError({
                    "current_password": "That password is not correct."
                })
            if User.objects.filter(email__iexact=new_email).exclude(pk=user.pk).exists():
                raise serializers.ValidationError({
                    "email": "An account already uses that email address."
                })

        attrs.pop("current_password", None)
        return attrs
