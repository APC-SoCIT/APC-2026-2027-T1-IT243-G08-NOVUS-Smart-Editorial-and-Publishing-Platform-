from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
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
    must_change_password = serializers.SerializerMethodField()
    password_expires_at = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id", "email", "first_name", "last_name", "role",
            "is_suspended", "reader_profile", "must_change_password", "password_expires_at",
        ]
        read_only_fields = ["role", "is_suspended"]

    def get_must_change_password(self, obj):
        return obj.must_change_password

    def get_password_expires_at(self, obj):
        if not obj.password_changed_at:
            return None
        return obj.password_changed_at + timedelta(days=getattr(settings, "PASSWORD_EXPIRY_DAYS", 90))


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


class ChangePasswordSerializer(serializers.Serializer):
    """Change one's own password. The current password proves it is the owner;
    the new one runs every configured validator, including the history rule."""

    current_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        user = self.context["request"].user
        if not user.check_password(attrs["current_password"]):
            raise serializers.ValidationError({"current_password": "That password is not correct."})
        try:
            validate_password(attrs["new_password"], user)
        except DjangoValidationError as exc:
            raise serializers.ValidationError({"new_password": list(exc.messages)})
        return attrs
