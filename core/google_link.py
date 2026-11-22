"""Short-lived, password-authorized Google connection; never match users by email alone."""

import secrets
import time

from allauth.account.models import EmailAddress
from allauth.core.exceptions import ImmediateHttpResponse
from allauth.socialaccount.models import SocialAccount
from django.conf import settings
from django.contrib.auth import login
from django.db import IntegrityError, transaction
from django.http import HttpResponseRedirect
from django.utils.crypto import constant_time_compare

from core.models import User

LINK_TTL_SECONDS = 300
READY_KEY = 'sinuca_google_link_ready'
PENDING_KEY = 'sinuca_google_link_pending'
RESULT_KEY = 'sinuca_google_link_result'


def verified_user(user):
    return (
        user.is_authenticated
        and user.is_active
        and EmailAddress.objects.filter(user=user, email__iexact=user.email, verified=True).exists()
    )


def fresh_proof(proof, user):
    return (
        isinstance(proof, dict)
        and verified_user(user)
        and proof.get('user_id') == str(user.pk)
        and 0 <= time.time() - proof.get('issued_at', 0) <= LINK_TTL_SECONDS
    )


def google_controls_email(email, sociallogin):
    return email.lower().endswith('@gmail.com') or bool(sociallogin.account.extra_data.get('hd'))


def connection_user(proof, session_user):
    if not isinstance(proof, dict):
        return None
    if not proof.get('verify_email'):
        return session_user if fresh_proof(proof, session_user) else None
    if session_user.is_authenticated or not 0 <= time.time() - proof['issued_at'] <= LINK_TTL_SECONDS:
        return None
    user = User.objects.filter(pk=proof['user_id'], is_active=True).first()
    if (
        user
        and proof.get('email') == user.email.casefold()
        and constant_time_compare(proof['password_proof'], user.get_session_auth_hash())
    ):
        return user
    return None


def create_proof(user, *, verify_email=False):
    proof = {'user_id': str(user.pk), 'issued_at': time.time(), 'nonce': secrets.token_urlsafe(32)}
    if verify_email:
        proof.update(verify_email=True, email=user.email.casefold(), password_proof=user.get_session_auth_hash())
    return proof


def reject_connection(code):
    raise ImmediateHttpResponse(
        HttpResponseRedirect(f'{settings.FRONTEND_URL}/auth/callback?flow=connect&error={code}')
    )


def validate_connection(request, sociallogin):
    proof = request.session.pop(PENDING_KEY, None)
    request.session.pop(RESULT_KEY, None)
    state_proof = sociallogin.state.get('data') or {}
    user = connection_user(proof, request.user)
    if user is None or state_proof != proof:
        reject_connection('link_expired')
    if sociallogin.account.provider != 'google':
        reject_connection('invalid_provider')
    if not any(
        address.verified and address.email.casefold() == user.email.casefold()
        for address in sociallogin.email_addresses
    ):
        reject_connection('google_email_mismatch')
    if sociallogin.is_existing and sociallogin.user.pk != user.pk:
        reject_connection('google_already_connected')
    if proof.get('verify_email'):
        confirm_pending_account(request, sociallogin, user, proof)
    record_result(request, sociallogin, user)


def record_result(request, sociallogin, user):
    # Only consumed after allauth has actually persisted the connection.
    request.session[RESULT_KEY] = {
        'user_id': str(user.pk),
        'uid': sociallogin.account.uid,
        'issued_at': time.time(),
    }


def confirm_pending_account(request, sociallogin, user, proof):
    if not google_controls_email(user.email, sociallogin):
        reject_connection('local_email_confirmation_required')
    try:
        with transaction.atomic():
            locked_user = User.objects.select_for_update().get(pk=user.pk)
            if (
                not locked_user.is_active
                or locked_user.email.casefold() != user.email.casefold()
                or not constant_time_compare(proof['password_proof'], locked_user.get_session_auth_hash())
            ):
                reject_connection('link_expired')
            address = EmailAddress.objects.filter(user=locked_user, email__iexact=locked_user.email).first()
            if address is None:
                address = EmailAddress.objects.create(user=locked_user, email=locked_user.email.lower(), primary=True)
            if not address.set_verified():
                reject_connection('google_email_mismatch')
            if not sociallogin.is_existing:
                sociallogin.connect(request, locked_user)
    except IntegrityError:
        reject_connection('google_already_connected')
    login(request, locked_user, backend='django.contrib.auth.backends.ModelBackend')
    record_result(request, sociallogin, locked_user)
    raise ImmediateHttpResponse(HttpResponseRedirect(f'{settings.FRONTEND_URL}/auth/callback?flow=connect'))


def consume_connection_result(request):
    result = request.session.pop(RESULT_KEY, None)
    return (
        fresh_proof(result, request.user)
        and SocialAccount.objects.filter(provider='google', uid=result['uid'], user=request.user).exists()
    )
