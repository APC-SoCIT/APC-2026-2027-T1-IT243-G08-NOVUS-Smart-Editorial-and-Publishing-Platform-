"""
Sign-in verification code: password first, then a 6-digit code by email.

  POST auth/token/          password accepted → 202 with a challenge, and
                            the code is emailed (or 200 with tokens when no
                            code is needed)
  POST auth/token/code/     the challenge and the code → 200 with tokens
  POST auth/token/resend/   the challenge → a fresh code, at most 3 sends

Staff always need a code. Readers need one if they turned it on in their
account. SIGNIN_CODE_REQUIRED=0 in the environment switches codes off, for
a local practice server or if email delivery fails; it is on by default.
"""
import hashlib
import hmac
import secrets
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.models import update_last_login
from django.db import transaction
from django.utils import timezone
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.views import TokenObtainPairView

from apps.notifications.email import send_email

from .models import SignInChallenge, User
from .sessions import SessionTokenObtainSerializer
from .throttles import LoginRateThrottle, SignInCodeThrottle

MINUTES = 10
RESEND_WAIT = timedelta(seconds=30)
EXPIRED = {"detail": "This code has expired. Sign in again.", "code": "code_expired"}


def code_required(user):
    if not getattr(settings, "SIGNIN_CODE_REQUIRED", True):
        return False
    return user.role != User.Role.READER or user.signin_code_enabled


def _hash(raw):
    return hashlib.sha256(raw.encode()).hexdigest()


def _hmac(challenge_hash, code):
    key = settings.SECRET_KEY.encode()
    return hmac.new(key, f"{challenge_hash}:{code}".encode(), hashlib.sha256).hexdigest()


def _new_code():
    return f"{secrets.randbelow(10**6):06d}"


def mask(email):
    """r***@boss.ph — enough to recognise, not enough to harvest."""
    name, _, domain = email.partition("@")
    return f"{name[:1]}{'*' * max(2, len(name) - 1)}@{domain}"


def _send(user, code):
    send_email(user, "signin_code", "Your sign-in code",
               {"code": code, "minutes": MINUTES})


def issue(user):
    """Start a challenge for this user, email the code, return the challenge."""
    now = timezone.now()
    SignInChallenge.objects.filter(user=user, used_at__isnull=True).update(used_at=now)
    raw = secrets.token_urlsafe(24)
    code = _new_code()
    h = _hash(raw)
    SignInChallenge.objects.create(user=user, challenge_hash=h, code_hmac=_hmac(h, code),
                                   expires_at=now + timedelta(minutes=MINUTES), last_sent_at=now)
    _send(user, code)
    return raw


def _open(raw):
    if not raw or len(raw) > 128:
        return None
    return (SignInChallenge.objects.select_related("user")
            .filter(challenge_hash=_hash(raw), used_at__isnull=True, expires_at__gt=timezone.now())
            .first())


def tokens_for(user):
    refresh = SessionTokenObtainSerializer.get_token(user)
    update_last_login(None, user)
    return {"refresh": str(refresh), "access": str(refresh.access_token)}


class SignInView(TokenObtainPairView):
    """UC-5.1 step 1: the password. A correct one either signs in at once or,
    when a code is needed, starts the second step."""

    serializer_class = SessionTokenObtainSerializer
    throttle_classes = [LoginRateThrottle]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
        except TokenError as e:
            raise InvalidToken(e.args[0]) from e
        user = serializer.user
        if not code_required(user):
            return Response(serializer.validated_data, status=status.HTTP_200_OK)
        return Response({
            "code_required": True,
            "challenge": issue(user),
            "sent_to": mask(user.email),
            "expires_in": MINUTES * 60,
            # Lets each sign-in page say at once when it is the wrong one.
            "staff": user.role != User.Role.READER,
        }, status=status.HTTP_202_ACCEPTED)


class SignInCodeView(APIView):
    """UC-5.1 step 2: the emailed code. Five wrong codes end the challenge."""

    permission_classes = [permissions.AllowAny]
    authentication_classes = []
    throttle_classes = [SignInCodeThrottle]

    def post(self, request):
        code = str(request.data.get("code", "")).strip().replace(" ", "")
        with transaction.atomic():
            found = _open(str(request.data.get("challenge", "")))
            ch = (SignInChallenge.objects.select_for_update().filter(pk=found.pk).first()
                  if found else None)
            if ch is None or ch.used_at or ch.attempts >= SignInChallenge.MAX_ATTEMPTS:
                return Response(EXPIRED, status=status.HTTP_400_BAD_REQUEST)
            if not (code.isdigit() and len(code) == 6
                    and hmac.compare_digest(ch.code_hmac, _hmac(ch.challenge_hash, code))):
                ch.attempts += 1
                left = SignInChallenge.MAX_ATTEMPTS - ch.attempts
                if left <= 0:
                    ch.used_at = timezone.now()
                ch.save(update_fields=["attempts", "used_at", "updated_at"])
                if left <= 0:
                    return Response({"detail": "Too many wrong codes. Sign in again.",
                                     "code": "too_many_attempts"},
                                    status=status.HTTP_400_BAD_REQUEST)
                return Response({"detail": "That code is not right.", "code": "wrong_code",
                                 "attempts_left": left}, status=status.HTTP_400_BAD_REQUEST)
            ch.used_at = timezone.now()
            ch.save(update_fields=["used_at", "updated_at"])
            user = ch.user
        # The account may have been suspended between the two steps.
        if not user.is_active or user.is_suspended:
            return Response(EXPIRED, status=status.HTTP_400_BAD_REQUEST)
        return Response(tokens_for(user))


class SignInResendView(APIView):
    """A fresh code for the same challenge: at most 3 sends, 30 s apart.
    Wrong guesses still count against the same five."""

    permission_classes = [permissions.AllowAny]
    authentication_classes = []
    throttle_classes = [SignInCodeThrottle]

    def post(self, request):
        with transaction.atomic():
            found = _open(str(request.data.get("challenge", "")))
            ch = (SignInChallenge.objects.select_for_update().filter(pk=found.pk).first()
                  if found else None)
            if ch is None or ch.attempts >= SignInChallenge.MAX_ATTEMPTS:
                return Response(EXPIRED, status=status.HTTP_400_BAD_REQUEST)
            now = timezone.now()
            if ch.sends >= SignInChallenge.MAX_SENDS:
                return Response({"detail": "No more codes can be sent. Sign in again.",
                                 "code": "too_many_sends"}, status=status.HTTP_400_BAD_REQUEST)
            if now - ch.last_sent_at < RESEND_WAIT:
                wait = int((RESEND_WAIT - (now - ch.last_sent_at)).total_seconds()) + 1
                return Response({"detail": f"Wait {wait} seconds before asking again.",
                                 "code": "wait", "wait": wait},
                                status=status.HTTP_429_TOO_MANY_REQUESTS)
            code = _new_code()
            ch.code_hmac = _hmac(ch.challenge_hash, code)
            ch.sends += 1
            ch.last_sent_at = now
            ch.expires_at = now + timedelta(minutes=MINUTES)
            ch.save(update_fields=["code_hmac", "sends", "last_sent_at", "expires_at", "updated_at"])
            user = ch.user
        _send(user, code)
        return Response({"sent_to": mask(user.email), "expires_in": MINUTES * 60,
                         "sends_left": SignInChallenge.MAX_SENDS - ch.sends})
