from allauth.core.exceptions import ImmediateHttpResponse
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from allauth.socialaccount.providers.base.constants import AuthProcess
from django.conf import settings
from django.http import HttpResponseRedirect

from core.google_link import google_controls_email, validate_connection, verified_user
from core.models import User


class SocialAccountAdapter(DefaultSocialAccountAdapter):
    def authenticate_by_email(self, sociallogin):
        if sociallogin.account.provider != 'google' or sociallogin.state.get('process') != AuthProcess.LOGIN:
            return None
        for address in sociallogin.email_addresses:
            if not address.verified or not google_controls_email(address.email, sociallogin):
                continue
            user = User.objects.filter(email__iexact=address.email).first()
            if user and verified_user(user):
                return user, address.email
        return None

    def pre_social_login(self, request, sociallogin):
        super().pre_social_login(request, sociallogin)
        if sociallogin.state.get('process') == AuthProcess.CONNECT:
            validate_connection(request, sociallogin)
        elif sociallogin.account.provider == 'google' and not sociallogin.is_existing:
            if any(
                User.objects.filter(email__iexact=address.email).exists() for address in sociallogin.email_addresses
            ):
                next_url = sociallogin.state.get('next')
                allowed_callbacks = {f'{origin}/auth/callback' for origin in settings.FRONTEND_ALLOWED_ORIGINS}
                if next_url not in allowed_callbacks:
                    next_url = settings.LOGIN_REDIRECT_URL
                raise ImmediateHttpResponse(
                    HttpResponseRedirect(f'{next_url}?error=google_account_confirmation_required')
                )

    def populate_user(self, request, sociallogin, data):
        user = super().populate_user(request, sociallogin, data)
        user.name = data.get('name') or ' '.join(
            part for part in (data.get('first_name'), data.get('last_name')) if part
        )
        return user
