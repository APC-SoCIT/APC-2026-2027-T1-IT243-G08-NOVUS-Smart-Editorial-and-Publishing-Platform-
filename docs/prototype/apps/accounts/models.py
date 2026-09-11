from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractUser
from django.db import models


class UserManager(BaseUserManager):
    """Custom manager required because we log in by email, not username."""

    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError("Users must have an email address")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        extra_fields.setdefault("role", User.Role.READER)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("role", User.Role.ADMIN)
        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True")
        return self._create_user(email, password, **extra_fields)


class User(AbstractUser):
    """
    Single identity table for every actor in NOVUS (UC-6.2 + ERD decision).
    Django's AUTH_USER_MODEL supports exactly one user table, and staff /
    reader accounts share the same login + session flow, so role-specific
    data (billing, subscription tier) lives in extension tables — see
    ReaderProfile — rather than a second identity table.
    """

    class Role(models.TextChoices):
        READER = "READER", "Reader"
        WRITER = "WRITER", "Writer"
        EDITOR = "EDITOR", "Editor"
        PUBLISHER = "PUBLISHER", "Publisher"
        GRAPHIC_DESIGNER = "GRAPHIC_DESIGNER", "Graphics Designer"
        ADMIN = "ADMIN", "Admin"

    username = None  # login is by email, not username
    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.READER)

    # UC-5.2.2 Suspend User Account
    is_suspended = models.BooleanField(default=False)
    # UC-5.2.3 Force Password Reset
    must_reset_password = models.BooleanField(default=False)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["first_name", "last_name"]

    def __str__(self):
        return f"{self.get_full_name()} <{self.email}> ({self.role})"


class ReaderProfile(models.Model):
    """
    Reader/Subscriber-only attributes (UC-6.3 Subscribe), split from User
    per the ERD's supertype/subtype pattern rather than a second identity
    table. Created automatically on registration (see accounts/serializers.py).
    """

    class Tier(models.TextChoices):
        FREE = "FREE", "Free Reader"
        SUBSCRIBER = "SUBSCRIBER", "Subscriber"

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="reader_profile")
    tier = models.CharField(max_length=20, choices=Tier.choices, default=Tier.FREE)
    subscription_started_at = models.DateTimeField(null=True, blank=True)
    subscription_renews_at = models.DateTimeField(null=True, blank=True)
    # PayMongo customer/subscription reference — wired in Phase 2 (Module 9)
    payment_gateway_customer_id = models.CharField(max_length=100, blank=True)

    def __str__(self):
        return f"ReaderProfile<{self.user.email}> [{self.tier}]"
