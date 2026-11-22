import io
import re
import time
from contextlib import redirect_stdout
from http import HTTPStatus
from smtplib import SMTPAuthenticationError, SMTPServerDisconnected
from unittest.mock import patch

from allauth.account.models import EmailAddress
from django.core import mail
from django.core.cache import cache
from django.test import Client, TestCase, override_settings
from drf_spectacular.generators import SchemaGenerator

from core.models import User
from core.views.auth_api import log_smtp_failure


@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class JWTAuthenticationTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = Client(enforce_csrf_checks=True)
        self.credentials = {'email': 'jwt@example.com', 'password': 'Local-Password-739!'}

    def post(self, path, data, session_token=None):
        headers = {'HTTP_X_SESSION_TOKEN': session_token} if session_token else {}
        return self.client.post(path, data, content_type='application/json', **headers)

    def signup(self):
        response = self.post('/api/registro/', {**self.credentials, 'name': 'Nome original', 'matriculation': '123'})
        assert response.status_code == HTTPStatus.CREATED, response.content
        assert response.json()['name'] == 'Nome original'
        assert response.json()['email_verification_required']
        assert response.json()['session_token']
        assert 'password' not in response.json()
        assert len(mail.outbox) == 1
        message = mail.outbox[-1]
        code = re.search(r'(?<!\d)\d{6}(?!\d)', message.body).group()
        html, mime_type = message.alternatives[0]
        assert mime_type == 'text/html'
        assert code in html
        assert '10 minutos' in html
        assert 'SINUCA' in message.subject
        return response.json()['session_token'], code

    def test_original_registration_confirm_login_refresh_verify_and_bearer(self):
        session_token, code = self.signup()
        response = self.post('/api/registro/confirmar-email/', {'key': code}, session_token)
        assert response.status_code == HTTPStatus.OK, response.content
        assert set(response.json()) == {'access', 'refresh'}
        assert EmailAddress.objects.get(email=self.credentials['email']).verified
        response = self.post('/api/token/', self.credentials)
        assert response.status_code == HTTPStatus.OK, response.content
        tokens = response.json()
        assert set(tokens) == {'access', 'refresh'}
        self.client.cookies.clear()
        profile = self.client.get('/api/usuarios/me/', HTTP_AUTHORIZATION=f'Bearer {tokens["access"]}')
        assert profile.status_code == HTTPStatus.OK
        assert profile.json()['email'] == self.credentials['email']
        assert self.post('/api/token/verify/', {'token': tokens['access']}).status_code == HTTPStatus.OK
        refreshed = self.post('/api/token/refresh/', {'refresh': tokens['refresh']})
        assert refreshed.status_code == HTTPStatus.OK
        assert 'access' in refreshed.json()

    def test_unverified_login_sends_code_and_does_not_issue_jwt(self):
        User.objects.create_user(**self.credentials)
        response = self.post('/api/token/', self.credentials)
        assert response.status_code == HTTPStatus.UNAUTHORIZED, response.content
        assert response.json()['email_verification_required']
        assert 'access' not in response.json()
        assert len(mail.outbox) == 1
        code = re.search(r'(?<!\d)\d{6}(?!\d)', mail.outbox[-1].body).group()
        response = self.post('/api/registro/confirmar-email/', {'key': code}, response.json()['session_token'])
        assert response.status_code == HTTPStatus.OK, response.content

    @override_settings(
        EMAIL_HOST='smtp.gmail.com', EMAIL_PORT=465, EMAIL_USE_TLS=False,
        EMAIL_USE_SSL=True, EMAIL_HOST_USER='sinuca.ifc.no.reply@gmail.com',
        EMAIL_HOST_PASSWORD='sensitive secret', EMAIL_TIMEOUT=15,
    )
    def test_smtp_diagnostic_reports_transport_and_timeout_without_secrets(self):
        with self.assertLogs('core.auth.password', level='ERROR') as captured:
            log_smtp_failure(SMTPServerDisconnected('Connection unexpectedly closed: timed out'))
        diagnostic = '\n'.join(captured.output)
        assert 'reason=timeout' in diagnostic
        assert 'port=465 tls=False ssl=True' in diagnostic
        assert 'password_has_whitespace=True' in diagnostic
        assert 'sensitive secret' not in diagnostic
        assert 'sinuca.ifc.no.reply@gmail.com' not in diagnostic

    def test_wrong_password_does_not_send_verification(self):
        User.objects.create_user(**self.credentials)
        response = self.post('/api/token/', {**self.credentials, 'password': 'wrong'})
        assert response.status_code != HTTPStatus.OK
        assert len(mail.outbox) == 0
        assert 'access' not in response.json()

    def test_password_login_failure_logs_diagnostic_without_credentials(self):
        User.objects.create_user(**self.credentials)
        with (
            patch(
                'django.core.mail.message.EmailMultiAlternatives.send',
                side_effect=SMTPAuthenticationError(535, b'sensitive-provider-message'),
            ),
            self.assertLogs('core.auth.password', level='ERROR') as captured,
            self.assertRaises(SMTPAuthenticationError),
        ):
            self.post('/api/token/', self.credentials)
        diagnostic = '\n'.join(captured.output)
        assert 'PASSWORD_LOGIN_FAILED stage=allauth_login' in diagnostic
        assert 'SMTPAuthenticationError' in diagnostic
        assert self.credentials['email'] not in diagnostic
        assert self.credentials['password'] not in diagnostic
        assert 'sensitive-provider-message' not in diagnostic

    def test_pending_session_and_correct_code_are_both_required(self):
        session_token, code = self.signup()
        response = self.post('/api/registro/confirmar-email/', {'key': code})
        assert response.status_code != HTTPStatus.OK
        wrong = '111111' if code != '111111' else '222222'
        response = self.post('/api/registro/confirmar-email/', {'key': wrong}, session_token)
        assert response.status_code == HTTPStatus.BAD_REQUEST
        assert 'access' not in response.json()
        assert not EmailAddress.objects.get(email=self.credentials['email']).verified

    def test_resend_throttle_and_delivery(self):
        session_token, _ = self.signup()
        response = self.post('/api/registro/reenviar-codigo/', {}, session_token)
        assert response.status_code == HTTPStatus.TOO_MANY_REQUESTS
        initial_count = len(mail.outbox)
        with patch('time.time', return_value=time.time() + 181):
            response = self.post('/api/registro/reenviar-codigo/', {}, session_token)
        assert response.status_code == HTTPStatus.OK, response.content
        assert len(mail.outbox) == initial_count + 1

    def test_google_session_exchange_requires_verified_user_and_csrf(self):
        user = User.objects.create_user(**self.credentials)
        self.client.force_login(user, backend='django.contrib.auth.backends.ModelBackend')
        assert self.post('/api/token/session/', {}).status_code == HTTPStatus.FORBIDDEN
        csrf = self.client.get('/api/auth/csrf/').json()['csrfToken']
        response = self.client.post('/api/token/session/', HTTP_X_CSRFTOKEN=csrf)
        assert response.status_code == HTTPStatus.FORBIDDEN
        EmailAddress.objects.create(user=user, email=user.email, verified=True, primary=True)
        response = self.client.post('/api/token/session/', HTTP_X_CSRFTOKEN=csrf)
        assert response.status_code == HTTPStatus.OK
        assert set(response.json()) == {'access', 'refresh'}

    def test_swagger_contains_original_token_routes_and_bearer(self):
        schema = SchemaGenerator().get_schema(public=True)
        for path in (
            '/api/token/',
            '/api/token/refresh/',
            '/api/token/verify/',
            '/api/registro/',
            '/api/registro/confirmar-email/',
            '/api/registro/reenviar-codigo/',
        ):
            assert 'post' in schema['paths'][path]
        assert schema['components']['securitySchemes']['jwtAuth']['scheme'] == 'bearer'

    def test_development_email_is_written_to_console(self):
        with self.settings(EMAIL_BACKEND='django.core.mail.backends.console.EmailBackend'):
            output = io.StringIO()
            with redirect_stdout(output):
                response = self.post('/api/registro/', self.credentials)
            assert response.status_code == HTTPStatus.CREATED, response.content
            code = re.search(r'(?<!\d)\d{6}(?!\d)', output.getvalue()).group()
            response = self.post('/api/registro/confirmar-email/', {'key': code}, response.json()['session_token'])
            assert response.status_code == HTTPStatus.OK
