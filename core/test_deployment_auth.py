import os
import subprocess
import sys
from pathlib import Path

from django.test import SimpleTestCase, override_settings

FRONTEND = 'https://sinuca-ifc-mocha.vercel.app'


@override_settings(
    CORS_ALLOWED_ORIGINS=[FRONTEND],
    CORS_ALLOW_ALL_ORIGINS=False,
    CORS_ALLOW_CREDENTIALS=True,
    CSRF_TRUSTED_ORIGINS=[FRONTEND],
    SESSION_COOKIE_SECURE=True,
    CSRF_COOKIE_SECURE=True,
    SESSION_COOKIE_SAMESITE='None',
    CSRF_COOKIE_SAMESITE='None',
)
class ProductionBrowserAuthTests(SimpleTestCase):
    def test_default_deployment_configuration(self):
        env = {**os.environ, 'PYTHON_DOTENV_DISABLED': '1'}
        for key in (
            'FRONTEND_URL', 'FRONTEND_ALLOWED_ORIGINS', 'AUTH_COOKIE_SECURE',
            'AUTH_CROSS_SITE_COOKIES', 'EMAIL_BACKEND', 'EMAIL_HOST',
            'EMAIL_HOST_USER', 'DEFAULT_FROM_EMAIL', 'EMAIL_PORT',
            'EMAIL_USE_TLS', 'EMAIL_USE_SSL',
        ):
            env.pop(key, None)
        code = (
            'from app import settings as s; '
            f'assert s.FRONTEND_URL == {FRONTEND!r}; '
            'assert s.CORS_ALLOWED_ORIGINS == s.CSRF_TRUSTED_ORIGINS == [s.FRONTEND_URL]; '
            'assert s.LOGIN_REDIRECT_URL == s.FRONTEND_URL + "/auth/callback"; '
            'assert s.CSRF_COOKIE_SECURE and s.SESSION_COOKIE_SECURE; '
            'assert s.CSRF_COOKIE_SAMESITE == s.SESSION_COOKIE_SAMESITE == "None"; '
            'assert s.EMAIL_BACKEND == "django.core.mail.backends.smtp.EmailBackend"; '
            'assert s.EMAIL_HOST == "smtp.gmail.com" and s.EMAIL_PORT == 587; '
            'assert s.EMAIL_USE_TLS and not s.EMAIL_USE_SSL; '
            'assert s.EMAIL_HOST_USER == "sinuca.ifc.no.reply@gmail.com"; '
            'assert s.DEFAULT_FROM_EMAIL == "SINUCA <sinuca.ifc.no.reply@gmail.com>"'
        )
        result = subprocess.run(
            [sys.executable, '-c', code], env=env,
            cwd=Path(__file__).resolve().parent.parent,
            capture_output=True, text=True, timeout=20,
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_csrf_response_allows_only_the_deployed_frontend(self):
        response = self.client.get('/api/auth/csrf/', HTTP_ORIGIN=FRONTEND, secure=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Access-Control-Allow-Origin'], FRONTEND)
        self.assertEqual(response['Access-Control-Allow-Credentials'], 'true')
        self.assertEqual(response.cookies['csrftoken']['samesite'], 'None')
        self.assertTrue(response.cookies['csrftoken']['secure'])
        for origin in ('http://localhost:5173', 'https://untrusted.example'):
            rejected = self.client.get('/api/auth/csrf/', HTTP_ORIGIN=origin, secure=True)
            self.assertNotIn('Access-Control-Allow-Origin', rejected)

    def test_authenticated_api_preflight(self):
        response = self.client.options(
            '/api/postagens/',
            HTTP_ORIGIN=FRONTEND,
            HTTP_ACCESS_CONTROL_REQUEST_METHOD='GET',
            HTTP_ACCESS_CONTROL_REQUEST_HEADERS='authorization,x-push-endpoint',
            secure=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Access-Control-Allow-Origin'], FRONTEND)
        self.assertIn('authorization', response['Access-Control-Allow-Headers'])
        self.assertIn('x-push-endpoint', response['Access-Control-Allow-Headers'])

    def test_cross_site_cookie_environment_configuration(self):
        env = {
            **os.environ,
            'PYTHON_DOTENV_DISABLED': '1',
            'MODE': 'DEVELOPMENT',
            'DATABASE_URL': 'sqlite:///:memory:',
            'FRONTEND_URL': FRONTEND,
            'FRONTEND_ALLOWED_ORIGINS': '',
            'AUTH_CROSS_SITE_COOKIES': 'True',
            'AUTH_COOKIE_SECURE': 'True',
        }
        code = (
            'from app import settings as s; '
            'assert s.CORS_ALLOWED_ORIGINS == [s.FRONTEND_URL]; '
            'assert s.CSRF_TRUSTED_ORIGINS == [s.FRONTEND_URL]; '
            'assert s.CORS_ALLOW_CREDENTIALS; '
            'assert not s.CORS_ALLOW_ALL_ORIGINS; '
            'assert s.SESSION_COOKIE_SECURE and s.CSRF_COOKIE_SECURE; '
            'assert s.SESSION_COOKIE_SAMESITE == s.CSRF_COOKIE_SAMESITE == "None"'
        )
        result = subprocess.run(
            [sys.executable, '-c', code], env=env,
            cwd=Path(__file__).resolve().parent.parent,
            capture_output=True, text=True, timeout=20,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        env['FRONTEND_URL'] = 'http://localhost:5173'
        local_frontend = subprocess.run(
            [sys.executable, '-c', code], env=env,
            cwd=Path(__file__).resolve().parent.parent,
            capture_output=True, text=True, timeout=20,
        )
        self.assertEqual(local_frontend.returncode, 0, local_frontend.stderr)
        env['AUTH_COOKIE_SECURE'] = 'False'
        rejected = subprocess.run(
            [sys.executable, '-c', 'from app import settings'], env=env,
            cwd=Path(__file__).resolve().parent.parent,
            capture_output=True, text=True, timeout=20,
        )
        self.assertNotEqual(rejected.returncode, 0)
        self.assertIn('requires AUTH_COOKIE_SECURE=True', rejected.stderr)
