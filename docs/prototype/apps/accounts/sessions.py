"""
Session versions: ending every sign-in for an account at once.
 
A JWT cannot be recalled once issued, so each one carries the account's
session_version at the time it was issued, under the claim "sv". The value
travels from the refresh token to every access token made from it. When the
account's number moves on, tokens with the old number are refused, both on
an ordinary request and on refresh, so a stolen refresh token cannot mint
new access tokens either.
 
Tokens issued before this claim existed carry none and are read as 0, the
starting value, so deploying it signs nobody out.
"""
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.exceptions import InvalidToken
from rest_framework_simplejwt.serializers import (
    TokenObtainPairSerializer, TokenRefreshSerializer,
)
from rest_framework_simplejwt.settings import api_settings
 
CLAIM = "sv"
ENDED = "This session has ended. Sign in again."
 
 
def is_current(token, user):
    return token.get(CLAIM, 0) == user.session_version
 
 
class SessionTokenObtainSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token[CLAIM] = user.session_version
        return token
 
 
class SessionTokenRefreshSerializer(TokenRefreshSerializer):
    def validate(self, attrs):
        refresh = self.token_class(attrs["refresh"])
        user = get_user_model().objects.filter(
            pk=refresh.get(api_settings.USER_ID_CLAIM), is_active=True).first()
        if user is None or not is_current(refresh, user):
            raise InvalidToken(ENDED)
        return super().validate(attrs)
