from http import HTTPStatus
from unittest.mock import patch
from urllib.parse import parse_qs, urlparse

from allauth.account.models import EmailAddress
from allauth.socialaccount.models import SocialAccount
from django.conf import settings
from django.core.cache import cache
from django.test import Client, TestCase, override_settings

from core.models import User


@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')  # noqa: PLR0904
class GoogleFrontendTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = Client(enforce_csrf_checks=True, HTTP_HOST='localhost:8000')

    def _csrf(self):
        return self.client.get('/api/auth/csrf/', HTTP_ORIGIN='http://localhost:5173').json()['csrfToken']

    def _start_google(self):
        response = self.client.post(
            '/api/auth/google/',
            {'csrfmiddlewaretoken': self._csrf()},
            HTTP_ORIGIN='http://localhost:5173',
        )
        assert response.status_code == HTTPStatus.FOUND
        query = parse_qs(urlparse(response.url).query)
        assert query['redirect_uri'] == ['http://localhost:8000/accounts/google/login/callback/']
        assert urlparse(response.url).hostname == 'accounts.google.com'
        return query['state'][0]

    def _complete_google(
        self, state, email='google@example.com', verified=True, subject='google-subject-123', hosted_domain=None
    ):
        # Somente a comunicação externa é simulada; callback, state, cadastro,
        # vínculo, sessão e emissão do JWT passam pelo código real do allauth.
        with (
            patch(
                'allauth.socialaccount.providers.google.views.GoogleOAuth2Adapter.get_access_token_data',
                return_value={
                    'access_token': 'google-test-access',
                    'id_token': 'google-test-id',
                    'token_type': 'Bearer',
                },
            ),
            patch(
                'allauth.socialaccount.providers.google.views._verify_and_decode',
                return_value={
                    'sub': subject,
                    'email': email,
                    'email_verified': verified,
                    'hd': hosted_domain,
                    'given_name': 'Pessoa',
                    'family_name': 'Google',
                },
            ),
        ):
            return self.client.get('/accounts/google/login/callback/', {'code': 'external-test-code', 'state': state})

    def test_google_signup_callback_jwt_logout_and_repeat_login(self):
        response = self._complete_google(self._start_google())
        assert response.status_code == HTTPStatus.FOUND
        assert response.url == settings.LOGIN_REDIRECT_URL
        user = User.objects.get(email='google@example.com')
        assert user.country_id is None
        assert user.role == User.Role.STUDENT
        assert not user.is_staff
        assert not user.is_superuser
        assert user.name == 'Pessoa Google'
        assert not user.has_usable_password()
        assert EmailAddress.objects.get(user=user).verified
        assert SocialAccount.objects.filter(user=user, provider='google').exists()
        tokens = self.client.post('/api/token/session/', HTTP_X_CSRFTOKEN=self._csrf())
        assert tokens.status_code == HTTPStatus.OK
        assert set(tokens.json()) == {'access', 'refresh'}
        api_client = Client()
        profile = api_client.get('/api/usuarios/me/', HTTP_AUTHORIZATION=f'Bearer {tokens.json()["access"]}')
        assert profile.json()['id'] == user.pk
        logout = self.client.post('/api/auth/logout/', HTTP_X_CSRFTOKEN=self._csrf())
        assert logout.status_code == HTTPStatus.OK
        assert (
            self.client.post('/api/token/session/', HTTP_X_CSRFTOKEN=self._csrf()).status_code == HTTPStatus.FORBIDDEN
        )
        response = self._complete_google(self._start_google())
        assert response.url == settings.LOGIN_REDIRECT_URL
        assert User.objects.filter(email=user.email).count() == 1
        assert SocialAccount.objects.filter(user=user).count() == 1

    def test_google_cancellation_returns_to_frontend_without_login(self):
        state = self._start_google()
        response = self.client.get('/accounts/google/login/callback/', {'error': 'access_denied', 'state': state})
        assert response.status_code == HTTPStatus.FOUND
        assert response.url.startswith(settings.LOGIN_REDIRECT_URL + '?')
        assert 'error' in parse_qs(urlparse(response.url).query)
        assert not SocialAccount.objects.exists()
        assert (
            self.client.post('/api/token/session/', HTTP_X_CSRFTOKEN=self._csrf()).status_code == HTTPStatus.FORBIDDEN
        )

    def test_invalid_oauth_state_cannot_log_in(self):
        response = self._complete_google('invalid-state')
        assert response.status_code == HTTPStatus.FOUND
        assert 'error' in parse_qs(urlparse(response.url).query)
        assert not SocialAccount.objects.exists()

    def test_existing_email_is_not_silently_linked(self):
        user = User.objects.create_user('google@example.com', 'Existing-Password-739!')
        response = self._complete_google(self._start_google())
        assert response.status_code == HTTPStatus.FOUND
        assert 'error=google_account_confirmation_required' in response.url
        assert not SocialAccount.objects.filter(user=user).exists()
        assert (
            self.client.post('/api/token/session/', HTTP_X_CSRFTOKEN=self._csrf()).status_code == HTTPStatus.FORBIDDEN
        )

    def test_csrf_and_cors_for_frontend(self):
        response = self.client.get('/api/auth/csrf/', HTTP_ORIGIN='http://localhost:5173')
        assert response['Access-Control-Allow-Origin'] == 'http://localhost:5173'
        assert response['Access-Control-Allow-Credentials'] == 'true'
        rejected = self.client.get('/api/auth/csrf/', HTTP_ORIGIN='https://untrusted.example')
        assert 'Access-Control-Allow-Origin' not in rejected
        assert self.client.post('/api/auth/google/').status_code == HTTPStatus.FORBIDDEN
        assert self.client.post('/api/auth/logout/').status_code == HTTPStatus.FORBIDDEN
        response = self.client.post(
            '/api/auth/google/', {'csrfmiddlewaretoken': self._csrf()}, HTTP_ORIGIN='https://untrusted.example'
        )
        assert response.status_code == HTTPStatus.FORBIDDEN

    def _local_account(self, email='google@example.com', verified=True):
        user = User.objects.create_user(email, 'Existing-Password-739!', name='Nome preservado')
        EmailAddress.objects.create(user=user, email=email, verified=verified, primary=True)
        return user

    def _prepare_connection(self, email='google@example.com', password='Existing-Password-739!'):
        return self.client.post(
            '/api/auth/google/vincular/',
            {'email': email, 'password': password},
            content_type='application/json',
            HTTP_X_CSRFTOKEN=self._csrf(),
            HTTP_ORIGIN='http://localhost:5173',
        )

    def _start_connection(self):
        response = self.client.post(
            '/api/auth/google/conectar/',
            {'csrfmiddlewaretoken': self._csrf()},
            HTTP_ORIGIN='http://localhost:5173',
        )
        assert response.status_code == HTTPStatus.FOUND
        query = parse_qs(urlparse(response.url).query)
        assert urlparse(response.url).hostname == 'accounts.google.com'
        assert query['prompt'] == ['select_account']
        return query['state'][0]

    def _exchange_connection(self):
        return self.client.post(
            '/api/token/session/',
            {'purpose': 'google_connect'},
            content_type='application/json',
            HTTP_X_CSRFTOKEN=self._csrf(),
        )

    def test_password_authorized_connection_preserves_user_and_allows_future_google_login(self):
        user = self._local_account()
        original_role = user.role
        old_csrf = self._csrf()
        assert self._prepare_connection().status_code == HTTPStatus.OK
        assert self._csrf() != old_csrf
        response = self._complete_google(self._start_connection())
        assert response.url == settings.LOGIN_REDIRECT_URL + '?flow=connect'
        assert SocialAccount.objects.get(provider='google').user_id == user.pk
        user.refresh_from_db()
        assert user.name == 'Nome preservado'
        assert user.role == original_role
        assert user.check_password('Existing-Password-739!')
        assert User.objects.count() == 1
        tokens = self._exchange_connection()
        assert tokens.status_code == HTTPStatus.OK
        assert tokens.json()['google_connected'] is True
        assert {'access', 'refresh'} <= tokens.json().keys()
        assert self._exchange_connection().status_code == HTTPStatus.CONFLICT
        self.client.post('/api/auth/logout/', HTTP_X_CSRFTOKEN=self._csrf())
        response = self._complete_google(self._start_google())
        assert response.url == settings.LOGIN_REDIRECT_URL
        assert self.client.post('/api/token/session/', HTTP_X_CSRFTOKEN=self._csrf()).status_code == HTTPStatus.OK
        assert User.objects.count() == 1

    def test_connection_requires_password_even_with_existing_session(self):
        user = self._local_account()
        self.client.force_login(user)
        assert self._prepare_connection(password='wrong').status_code == HTTPStatus.BAD_REQUEST
        assert 'sinuca_google_link_ready' not in self.client.session
        response = self.client.post('/api/auth/google/conectar/', HTTP_X_CSRFTOKEN=self._csrf())
        assert 'error=link_expired' in response.url
        assert not SocialAccount.objects.exists()

    def test_pending_gmail_account_is_confirmed_only_after_password_and_google(self):
        email = 'pending@gmail.com'
        user = self._local_account(email, verified=False)
        assert self._prepare_connection(email).status_code == HTTPStatus.OK
        assert '_auth_user_id' not in self.client.session
        assert self._exchange_connection().status_code == HTTPStatus.FORBIDDEN
        response = self._complete_google(self._start_connection(), email=email)
        assert response.url == settings.LOGIN_REDIRECT_URL + '?flow=connect'
        assert EmailAddress.objects.get(user=user).verified
        assert SocialAccount.objects.get(user=user).provider == 'google'
        assert self._exchange_connection().json()['google_connected'] is True
        assert User.objects.count() == 1
        user.refresh_from_db()
        assert user.check_password('Existing-Password-739!')
        assert user.name == 'Nome preservado'

    def test_pending_external_account_stays_unverified_and_unauthenticated(self):
        user = self._local_account(verified=False)
        assert self._prepare_connection().status_code == HTTPStatus.OK
        response = self._complete_google(self._start_connection())
        assert 'error=local_email_confirmation_required' in response.url
        assert not EmailAddress.objects.get(user=user).verified
        assert '_auth_user_id' not in self.client.session
        assert not SocialAccount.objects.exists()

    def test_connection_rejects_wrong_or_unverified_google_email(self):
        self._local_account()
        for email, verified in [('other@example.com', True), ('google@example.com', False)]:
            assert self._prepare_connection().status_code == HTTPStatus.OK
            response = self._complete_google(self._start_connection(), email=email, verified=verified)
            assert 'error=google_email_mismatch' in response.url
            assert not SocialAccount.objects.exists()
            assert self._exchange_connection().status_code == HTTPStatus.CONFLICT

    def test_connection_cannot_move_google_identity_from_another_user(self):
        self._local_account()
        other = self._local_account('other@example.com')
        account = SocialAccount.objects.create(user=other, provider='google', uid='google-subject-123')
        assert self._prepare_connection().status_code == HTTPStatus.OK
        response = self._complete_google(self._start_connection())
        assert 'error=google_already_connected' in response.url
        account.refresh_from_db()
        assert account.user_id == other.pk
        assert self._exchange_connection().status_code == HTTPStatus.CONFLICT

    def test_connection_expires_and_direct_connect_routes_cannot_bypass_password(self):
        user = self._local_account()
        self.client.force_login(user)
        response = self.client.post('/api/auth/google/conectar/', HTTP_X_CSRFTOKEN=self._csrf())
        assert 'error=link_expired' in response.url
        assert self._prepare_connection().status_code == HTTPStatus.OK
        state = self._start_connection()
        session = self.client.session
        session['sinuca_google_link_pending']['issued_at'] -= 301
        session.save()
        response = self._complete_google(state)
        assert 'error=link_expired' in response.url
        assert not SocialAccount.objects.exists()

    def test_connection_cancellation_and_replay_do_not_create_a_link(self):
        self._local_account()
        assert self._prepare_connection().status_code == HTTPStatus.OK
        state = self._start_connection()
        response = self.client.get('/accounts/google/login/callback/', {'error': 'access_denied', 'state': state})
        assert 'error' in parse_qs(urlparse(response.url).query)
        assert self._exchange_connection().status_code == HTTPStatus.CONFLICT
        response = self._complete_google(state)
        assert 'error' in parse_qs(urlparse(response.url).query)
        assert not SocialAccount.objects.exists()
        assert self._prepare_connection().status_code == HTTPStatus.OK
        assert 'error' not in self._complete_google(self._start_connection()).url
        assert self._exchange_connection().json()['google_connected'] is True

    def test_connection_requires_same_browser_session_at_callback(self):
        self._local_account()
        assert self._prepare_connection().status_code == HTTPStatus.OK
        state = self._start_connection()
        self.client.post('/api/auth/logout/', HTTP_X_CSRFTOKEN=self._csrf())
        response = self._complete_google(state)
        assert 'error' in response.url
        assert not SocialAccount.objects.exists()

    def test_connection_endpoints_enforce_csrf(self):
        self._local_account()
        assert (
            self.client.post('/api/auth/google/vincular/', {}, content_type='application/json').status_code
            == HTTPStatus.FORBIDDEN
        )
        assert self.client.post('/api/auth/google/conectar/').status_code == HTTPStatus.FORBIDDEN

    @override_settings(ACCOUNT_RATE_LIMITS={'login': '2/m/ip'})
    def test_connection_password_attempts_are_rate_limited(self):
        self._local_account()
        assert self._prepare_connection(password='wrong').status_code == HTTPStatus.BAD_REQUEST
        assert self._prepare_connection(password='wrong').status_code == HTTPStatus.BAD_REQUEST
        assert self._prepare_connection(password='wrong').status_code == HTTPStatus.TOO_MANY_REQUESTS

    def test_native_connect_endpoint_cannot_skip_password_authorization(self):
        user = self._local_account()
        self.client.force_login(user)
        response = self.client.post(
            '/_allauth/browser/v1/auth/provider/redirect',
            {
                'provider': 'google',
                'callback_url': '/auth/callback',
                'process': 'connect',
                'csrfmiddlewaretoken': self._csrf(),
            },
        )
        assert response.status_code == HTTPStatus.FOUND, (response.status_code, response.content[:300])
        state = parse_qs(urlparse(response.url).query)['state'][0]
        response = self._complete_google(state)
        assert 'error=link_expired' in response.url
        assert not SocialAccount.objects.exists()

    def test_repeated_connection_is_idempotent_for_the_same_user(self):
        self._local_account()
        for _ in range(2):
            assert self._prepare_connection().status_code == HTTPStatus.OK
            response = self._complete_google(self._start_connection())
            assert 'error' not in response.url
            assert self._exchange_connection().json()['google_connected'] is True
        assert SocialAccount.objects.count() == 1
        assert User.objects.count() == 1

    def test_verified_gmail_or_workspace_enters_existing_account_and_creates_session(self):
        for email, hosted_domain, subject in [
            ('existing@gmail.com', None, 'gmail-subject'),
            ('existing@example.com', 'example.com', 'workspace-subject'),
        ]:
            with self.subTest(email=email):
                user = self._local_account(email)
                response = self._complete_google(
                    self._start_google(), email=email, subject=subject, hosted_domain=hosted_domain
                )
                assert response.url == settings.LOGIN_REDIRECT_URL
                assert SocialAccount.objects.get(uid=subject).user_id == user.pk
                assert User.objects.filter(email=email).count() == 1
                user.refresh_from_db()
                assert user.check_password('Existing-Password-739!')
                assert user.name == 'Nome preservado'
                tokens = self.client.post('/api/token/session/', HTTP_X_CSRFTOKEN=self._csrf())
                assert tokens.status_code == HTTPStatus.OK
                profile = Client().get('/api/usuarios/me/', HTTP_AUTHORIZATION=f'Bearer {tokens.json()["access"]}')
                assert profile.json()['id'] == user.pk
                self.client.post('/api/auth/logout/', HTTP_X_CSRFTOKEN=self._csrf())

    def test_automatic_connection_requires_verified_local_and_google_addresses(self):
        for email, local_verified, google_verified in [
            ('local-pending@gmail.com', False, True),
            ('google-pending@gmail.com', True, False),
            ('external@example.com', True, True),
        ]:
            with self.subTest(email=email):
                self._local_account(email, verified=local_verified)
                response = self._complete_google(self._start_google(), email=email, verified=google_verified)
                assert 'error=google_account_confirmation_required' in response.url
                assert not SocialAccount.objects.exists()
                assert (
                    self.client.post('/api/token/session/', HTTP_X_CSRFTOKEN=self._csrf()).status_code
                    == HTTPStatus.FORBIDDEN
                )
