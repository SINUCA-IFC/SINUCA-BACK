import os
import subprocess
import sys
from pathlib import Path

from django.test import SimpleTestCase, override_settings

FRONTEND = 'https://sinuca-front-pedro-gabriel-goncalves-projects.vercel.app'


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
            'AUTH_CROSS_SITE_COOKIES': 'True',
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
        rejected = subprocess.run(
            [sys.executable, '-c', 'from app import settings'], env=env,
            cwd=Path(__file__).resolve().parent.parent,
            capture_output=True, text=True, timeout=20,
        )
        self.assertNotEqual(rejected.returncode, 0)
        self.assertIn('requires an HTTPS FRONTEND_URL', rejected.stderr)
