from unittest.mock import patch

from django.http import HttpResponseRedirect
from django.test import Client, SimpleTestCase, override_settings

ORIGINS = ['https://sinuca-ifc-mocha.vercel.app', 'http://localhost:5173']


@override_settings(
    FRONTEND_ALLOWED_ORIGINS=ORIGINS,
    CORS_ALLOWED_ORIGINS=ORIGINS,
    CSRF_TRUSTED_ORIGINS=ORIGINS,
    CORS_ALLOW_ALL_ORIGINS=False,
    CORS_ALLOW_CREDENTIALS=True,
)
class FrontendOriginsTests(SimpleTestCase):
    def test_both_origins_can_get_csrf_and_return_to_their_google_callback(self):
        for origin in ORIGINS:
            with self.subTest(origin=origin):
                client = Client(enforce_csrf_checks=True)
                response = client.get('/api/auth/csrf/', HTTP_ORIGIN=origin, secure=True)
                self.assertEqual(response['Access-Control-Allow-Origin'], origin)
                self.assertEqual(response['Access-Control-Allow-Credentials'], 'true')
                with patch('core.views.auth.get_adapter') as adapter:
                    provider = adapter.return_value.get_provider.return_value
                    provider.redirect.return_value = HttpResponseRedirect('https://accounts.google.com/')
                    response = client.post(
                        '/api/auth/google/',
                        {'csrfmiddlewaretoken': response.json()['csrfToken']},
                        HTTP_ORIGIN=origin,
                        secure=True,
                    )
                    self.assertEqual(response.status_code, 302)
                    self.assertEqual(provider.redirect.call_args.kwargs['next_url'], origin + '/auth/callback')

    def test_unknown_origin_has_no_cors_and_cannot_start_google(self):
        client = Client(enforce_csrf_checks=True)
        response = client.get('/api/auth/csrf/', HTTP_ORIGIN='https://untrusted.example', secure=True)
        self.assertNotIn('Access-Control-Allow-Origin', response)
        with patch('core.views.auth.get_adapter') as adapter:
            response = client.post(
                '/api/auth/google/',
                {'csrfmiddlewaretoken': response.json()['csrfToken']},
                HTTP_ORIGIN='https://untrusted.example',
                secure=True,
            )
            self.assertEqual(response.status_code, 403)
            adapter.assert_not_called()