import re
import time
from http import HTTPStatus
from unittest.mock import patch
from urllib.parse import parse_qs, urlparse

from allauth.account.models import EmailAddress
from django.core import mail
from django.core.cache import cache
from django.test import Client, TestCase, override_settings

from core.models import Country, User


@override_settings(
    EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
    STORAGES={
        'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
        'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'},
    },
)
class LocalAuthenticationTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = Client(enforce_csrf_checks=True)
        self.password = 'Local-Test-Password-739!'

    def post(self, path, data):
        token = self.client.get('/api/auth/csrf/').json()['csrfToken']
        return self.client.post(path, data, content_type='application/json', HTTP_X_CSRFTOKEN=token)

    def signup(self):
        response = self.post(
            '/_allauth/browser/v1/auth/signup',
            {
                'email': 'local@example.com',
                'password': self.password,
            },
        )
        assert response.status_code == HTTPStatus.UNAUTHORIZED
        assert not response.json()['meta']['is_authenticated']
        assert any(flow['id'] == 'verify_email' for flow in response.json()['data']['flows'])
        return re.search(r'(?<!\d)\d{6}(?!\d)', mail.outbox[-1].body).group()

    def test_signup_verification_session_and_logout(self):
        code = self.signup()
        assert self.client.get('/api/usuarios/me/').status_code == HTTPStatus.UNAUTHORIZED
        response = self.post('/_allauth/browser/v1/auth/email/verify', {'key': code})
        assert response.status_code == HTTPStatus.OK
        assert EmailAddress.objects.get(email='local@example.com').verified
        assert self.client.get('/api/usuarios/me/').json()['email'] == 'local@example.com'
        self.post('/api/auth/logout/', {})
        assert self.client.get('/api/usuarios/me/').status_code == HTTPStatus.UNAUTHORIZED
        response = self.post(
            '/_allauth/browser/v1/auth/login',
            {
                'email': 'local@example.com',
                'password': self.password,
            },
        )
        assert response.status_code == HTTPStatus.OK

    def test_wrong_code_does_not_authenticate(self):
        code = self.signup()
        wrong = '111111' if code != '111111' else '222222'
        response = self.post('/_allauth/browser/v1/auth/email/verify', {'key': wrong})
        assert response.status_code == HTTPStatus.BAD_REQUEST
        assert not EmailAddress.objects.get(email='local@example.com').verified
        assert self.client.get('/api/usuarios/me/').status_code == HTTPStatus.UNAUTHORIZED

    def test_attempt_limit_invalidates_pending_verification(self):
        code = self.signup()
        wrong = '111111' if code != '111111' else '222222'
        for _ in range(3):
            self.post('/_allauth/browser/v1/auth/email/verify', {'key': wrong})
        response = self.post('/_allauth/browser/v1/auth/email/verify', {'key': code})
        assert response.status_code != HTTPStatus.OK
        assert not EmailAddress.objects.get(email='local@example.com').verified

    def test_expired_code_is_rejected(self):
        code = self.signup()
        with self.settings(ACCOUNT_EMAIL_VERIFICATION_BY_CODE_TIMEOUT=-1):
            response = self.post('/_allauth/browser/v1/auth/email/verify', {'key': code})
        assert response.status_code != HTTPStatus.OK
        assert not EmailAddress.objects.get(email='local@example.com').verified

    def test_resend_code(self):
        self.signup()
        initial_email_count = len(mail.outbox)
        response = self.post('/_allauth/browser/v1/auth/email/verify/resend', {})
        assert response.status_code == HTTPStatus.TOO_MANY_REQUESTS
        with patch('time.time', return_value=time.time() + 181):
            response = self.post('/_allauth/browser/v1/auth/email/verify/resend', {})
        assert response.status_code in {HTTPStatus.OK, HTTPStatus.UNAUTHORIZED}
        assert len(mail.outbox) == initial_email_count + 1
        code = re.search(r'(?<!\d)\d{6}(?!\d)', mail.outbox[-1].body).group()
        assert self.post('/_allauth/browser/v1/auth/email/verify', {'key': code}).status_code == HTTPStatus.OK

    def test_csrf_is_required(self):
        response = self.client.post(
            '/_allauth/browser/v1/auth/signup',
            {
                'email': 'local@example.com',
                'password': self.password,
            },
            content_type='application/json',
        )
        assert response.status_code == HTTPStatus.FORBIDDEN

    def test_original_routes_restored(self):
        for path in ('/api/registro/', '/api/token/', '/api/token/refresh/', '/api/token/verify/'):
            assert self.client.get(path).status_code == HTTPStatus.METHOD_NOT_ALLOWED

    def test_demo_pages_removed_and_google_redirect(self):
        for path in ('/', '/accounts/login/', '/accounts/signup/'):
            assert self.client.get(path).status_code == HTTPStatus.NOT_FOUND
        token = self.client.get('/api/auth/csrf/').json()['csrfToken']
        response = self.client.post('/api/auth/google/', HTTP_X_CSRFTOKEN=token, HTTP_HOST='localhost:8000')
        assert response.status_code == HTTPStatus.FOUND
        target = urlparse(response.url)
        assert target.hostname == 'accounts.google.com'
        assert parse_qs(target.query)['redirect_uri'] == ['http://localhost:8000/accounts/google/login/callback/']

    def test_profile_creation_and_email_changes_cannot_bypass_allauth(self):
        code = self.signup()
        self.post('/_allauth/browser/v1/auth/email/verify', {'key': code})
        assert self.post('/api/usuarios/', {'email': 'bypass@example.com'}).status_code == HTTPStatus.METHOD_NOT_ALLOWED
        user = User.objects.get(email='local@example.com')
        token = self.client.get('/api/auth/csrf/').json()['csrfToken']
        response = self.client.patch(
            f'/api/usuarios/{user.pk}/',
            {
                'email': 'bypass@example.com',
                'name': 'Meu nome',
                'is_staff': True,
                'role': 'organizer',
            },
            content_type='application/json',
            HTTP_X_CSRFTOKEN=token,
        )
        assert response.status_code == HTTPStatus.OK
        user.refresh_from_db()
        assert user.email == 'local@example.com'
        assert user.name == 'Meu nome'
        assert not user.is_staff
        assert user.role == 'student'

    def test_cannot_modify_another_user(self):
        country = Country.objects.create(name='Brasil', political_name='Brasil')
        user = User.objects.create_user('one@example.com', self.password, country=country)
        other = User.objects.create_user('two@example.com', self.password, country=country)
        self.client.force_login(user, backend='django.contrib.auth.backends.ModelBackend')
        token = self.client.get('/api/auth/csrf/').json()['csrfToken']
        response = self.client.patch(
            f'/api/usuarios/{other.pk}/', {'name': 'Alterado'}, content_type='application/json', HTTP_X_CSRFTOKEN=token
        )
        assert response.status_code == HTTPStatus.FORBIDDEN
        response = self.client.delete(f'/api/usuarios/{other.pk}/', HTTP_X_CSRFTOKEN=token)
        assert response.status_code == HTTPStatus.FORBIDDEN
