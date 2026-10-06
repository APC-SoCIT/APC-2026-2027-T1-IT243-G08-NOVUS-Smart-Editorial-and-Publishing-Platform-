from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractUser
from datetime import timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.common.models import TimeStampedModel


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
    # Password policy (PCI DSS 8.3.9): a password expires a set number of
    # days after this. Expiry sets must_reset_password, which locks the
    # account until the password is changed.
    password_changed_at = models.DateTimeField(null=True, blank=True)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["first_name", "last_name"]

    def set_password(self, raw_password):
        super().set_password(raw_password)
        # Recorded on save, once the hash is final and the row has an id.
        self._password_was_set = True

    def save(self, *args, **kwargs):
        changed = getattr(self, "_password_was_set", False) and self.has_usable_password()
        if changed:
            self.password_changed_at = timezone.now()
            fields = kwargs.get("update_fields")
            if fields is not None:
                kwargs["update_fields"] = set(fields) | {"password_changed_at"}
        super().save(*args, **kwargs)
        if changed:
            self._password_was_set = False
            PasswordHistory.record(self)

    @property
    def password_expired(self):
        if not self.password_changed_at:
            return False
        days = getattr(settings, "PASSWORD_EXPIRY_DAYS", 90)
        return timezone.now() - self.password_changed_at > timedelta(days=days)

    @property
    def must_change_password(self):
        return self.must_reset_password or self.password_expired

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


class PasswordHistory(TimeStampedModel):
    """Every password an account has held, as a hash (PCI DSS 8.3.7).

    Separate from the reset-token table because a history row is needed for
    every change, including the forced 90-day ones, while a reset token
    exists only when someone forgets their password. Only hashes are kept,
    made with the same algorithm as the live password.

    At least the last PASSWORD_HISTORY_COUNT entries are kept, and anything
    from the past year, so a user changing every three months keeps four.
    """

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="password_history")
    password_hash = models.CharField(max_length=128)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["user", "created_at"], name="password_history_by_user")]
        verbose_name_plural = "password history"

    def __str__(self):
        return f"PasswordHistory<{self.user_id}> {self.created_at:%Y-%m-%d}"

    @classmethod
    def record(cls, user):
        cls.objects.create(user=user, password_hash=user.password)
        keep = getattr(settings, "PASSWORD_HISTORY_COUNT", 4)
        year_ago = timezone.now() - timedelta(days=365)
        rows = cls.objects.filter(user=user).order_by("-created_at", "-id").values_list("id", "created_at")
        stale = [pk for n, (pk, at) in enumerate(rows) if n >= keep and at < year_ago]
        if stale:
            cls.objects.filter(id__in=stale).delete()
