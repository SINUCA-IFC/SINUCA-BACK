import json

from allauth.decorators import rate_limit
from allauth.headless.account.inputs import LoginInput
from allauth.socialaccount.adapter import get_adapter
from allauth.socialaccount.providers.base.constants import AuthProcess
from django.conf import settings
from django.contrib.auth import login, logout
from django.http import HttpResponseRedirect, JsonResponse
from django.middleware.csrf import get_token, rotate_token
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie
from django.views.decorators.debug import sensitive_post_parameters
from django.views.decorators.http import require_GET, require_POST

from core.google_link import PENDING_KEY, READY_KEY, RESULT_KEY, connection_user, create_proof, verified_user


@require_GET
@never_cache
@ensure_csrf_cookie
def csrf_token(request):
    return JsonResponse({'csrfToken': get_token(request)})


@require_POST
@never_cache
@csrf_protect
def google_login(request):
    provider = get_adapter().get_provider(request, 'google')
    origin = request.headers.get('Origin', '')
    next_url = (
        f'{origin}/auth/callback'
        if origin in settings.FRONTEND_ALLOWED_ORIGINS
        else settings.LOGIN_REDIRECT_URL
    )
    return provider.redirect(request, AuthProcess.LOGIN, next_url=next_url, headless=True)


@require_POST
@never_cache
@csrf_protect
def logout_session(request):
    logout(request)
    return JsonResponse({'detail': 'Sessão encerrada.'})


@require_POST
@never_cache
@csrf_protect
@sensitive_post_parameters('password')
@rate_limit(action='login')
def prepare_google_connection(request):
    request.session.pop(READY_KEY, None)
    request.session.pop(PENDING_KEY, None)
    request.session.pop(RESULT_KEY, None)
    try:
        payload = json.loads(request.body)
    except (ValueError, UnicodeDecodeError):
        return JsonResponse({'detail': 'Informe e-mail e senha.'}, status=400)
    if not isinstance(payload, dict):
        return JsonResponse({'detail': 'Informe e-mail e senha.'}, status=400)
    form = LoginInput(data={'email': payload.get('email'), 'password': payload.get('password')})
    if not form.is_valid():
        return JsonResponse({'detail': 'E-mail ou senha inválidos. Confira os dados e tente novamente.'}, status=400)
    user = form.login.user
    email_pending = not verified_user(user)
    logout(request)
    if email_pending:
        # Keep this browser anonymous until Google proves ownership of the address.
        rotate_token(request)
    else:
        login(request, user, backend=user.backend)
    request.session[READY_KEY] = create_proof(user, verify_email=email_pending)
    return JsonResponse({'detail': 'Senha confirmada. Continue com sua conta Google.'})


@require_POST
@never_cache
@csrf_protect
def connect_google(request):
    proof = request.session.pop(READY_KEY, None)
    if connection_user(proof, request.user) is None:
        return HttpResponseRedirect(f'{settings.FRONTEND_URL}/auth/callback?flow=connect&error=link_expired')
    request.session[PENDING_KEY] = proof
    provider = get_adapter().get_provider(request, 'google')
    return provider.redirect(
        request,
        AuthProcess.CONNECT,
        next_url=f'{settings.FRONTEND_URL}/auth/callback?flow=connect',
        data=proof,
        headless=True,
        auth_params={'prompt': 'select_account'},
    )
