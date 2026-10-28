import io
import os
import runpy
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from django.test import Client, SimpleTestCase, override_settings
from django.urls import path, reverse
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from core.models import Country, Link, Schedule, Task, User


def intentional_error(request):
    raise RuntimeError('Internal diagnostic marker for security regression test')


urlpatterns = [path('intentional-error/', intentional_error)]


class DebugSecurityTests(SimpleTestCase):
    settings_path = Path(__file__).resolve().parents[2] / 'app' / 'settings.py'
    cloudinary_url = 'cloudinary://audit-key:audit-cloud-secret@audit-cloud'
    database_password = 'audit-database-secret'

    def load_settings(self, debug=None):
        environment = {
            'MODE': 'PRODUCTION',
            'SECRET_KEY': 'isolated-settings-test-secret',
            'CLOUDINARY_URL': self.cloudinary_url,
            'DATABASE_URL': f'postgres://audit:{self.database_password}@127.0.0.1/audit',
        }
        if debug is not None:
            environment['DEBUG'] = debug
        output = io.StringIO()
        with patch.dict(os.environ, environment, clear=True), patch('dotenv.load_dotenv'), redirect_stdout(output):
            values = runpy.run_path(str(self.settings_path))
        return values, output.getvalue()

    def test_debug_defaults_to_boolean_false(self):
        values, _ = self.load_settings()

        self.assertIs(values['DEBUG'], False)

    def test_false_and_unrecognized_debug_values_disable_debug(self):
        for value in ['False', 'false', 'FALSE', '0', 'no', 'off', '', 'release', 'invalid', '  FALSE  ']:
            with self.subTest(value=value):
                values, _ = self.load_settings(value)
                self.assertIs(values['DEBUG'], False)

    def test_explicit_true_values_enable_debug(self):
        for value in ['True', 'true', 'TRUE', '1', 'yes', 'on', '  TRUE  ']:
            with self.subTest(value=value):
                values, _ = self.load_settings(value)
                self.assertIs(values['DEBUG'], True)

    def test_loading_settings_does_not_print_secrets(self):
        _, output = self.load_settings('False')

        self.assertEqual(output, '')

    @override_settings(ROOT_URLCONF=__name__, DEBUG_PROPAGATE_EXCEPTIONS=False)
    def test_false_debug_returns_generic_server_error(self):
        values, _ = self.load_settings('False')
        with override_settings(DEBUG=values['DEBUG'], CLOUDINARY_URL=self.cloudinary_url):
            response = Client(raise_request_exception=False).get('/intentional-error/', HTTP_ACCEPT='text/html')

        body = response.content.decode()
        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertFalse('Traceback' in body, 'The public response must not include a traceback.')
        self.assertFalse(
            'Internal diagnostic marker' in body, 'The public response must not include exception details.',
        )
        self.assertFalse('audit-cloud-secret' in body, 'The public response must not include Cloudinary credentials.')

    @override_settings(ROOT_URLCONF=__name__, DEBUG=True, DEBUG_PROPAGATE_EXCEPTIONS=False)
    def test_development_traceback_redacts_cloudinary_credentials(self):
        with override_settings(CLOUDINARY_URL=self.cloudinary_url):
            response = Client(raise_request_exception=False).get('/intentional-error/', HTTP_ACCEPT='text/html')

        body = response.content.decode()
        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertTrue('Traceback' in body, 'The development diagnostic page must still be available.')
        self.assertFalse('audit-cloud-secret' in body, 'Development diagnostics must redact Cloudinary credentials.')


class ScopedEndpointAuthenticationTests(APITestCase):
    endpoints = ['tarefas', 'cronogramas', 'docs']

    @classmethod
    def setUpTestData(cls):
        cls.country = Country.objects.create(name='País A', political_name='Delegação A')
        cls.other_country = Country.objects.create(name='País B', political_name='Delegação B')
        cls.student = User.objects.create_user(email='scope-a@example.test', country=cls.country)
        cls.other_student = User.objects.create_user(email='scope-b@example.test', country=cls.other_country)
        cls.unassigned = User.objects.create_user(email='unassigned@example.test')
        cls.visible_ids = {}
        for country, user in [(cls.country, cls.student), (cls.other_country, cls.other_student)]:
            task = Task.objects.create(title='Tarefa de teste', creator=user, status=1)
            link = Link.objects.create(name='Documento de teste', url='https://example.test/document')
            link.country.add(country)
            schedule = Schedule.objects.create(
                title='Evento de teste',
                category=1,
                startDate='2026-10-28T10:00:00-03:00',
                endDate='2026-10-28T11:00:00-03:00',
                description='Evento para testar isolamento de delegações',
            )
            schedule.country.add(country)
            if country == cls.country:
                cls.visible_ids = {'tarefas': task.pk, 'cronogramas': schedule.pk, 'docs': link.pk}

    def authenticate(self, user):
        token = RefreshToken.for_user(user).access_token
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')

    def test_anonymous_list_and_detail_require_login(self):
        for endpoint in self.endpoints:
            for url in [reverse(f'{endpoint}-list'), reverse(f'{endpoint}-detail', args=[self.visible_ids[endpoint]])]:
                with self.subTest(url=url):
                    response = self.client.get(url)
                    self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_anonymous_creation_requires_login(self):
        payloads = {
            'tarefas': {'title': 'Tentativa anônima', 'status': 1},
            'cronogramas': {
                'title': 'Tentativa anônima',
                'category': 1,
                'startDate': '2026-10-28T12:00:00-03:00',
                'endDate': '2026-10-28T13:00:00-03:00',
                'description': 'Tentativa de criação sem autenticação',
                'country': [self.country.pk],
            },
            'docs': {'name': 'Tentativa anônima', 'url': 'https://example.test/anonymous'},
        }
        for endpoint, payload in payloads.items():
            with self.subTest(endpoint=endpoint):
                response = self.client.post(reverse(f'{endpoint}-list'), payload, format='json')
                self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(Task.objects.count(), 2)
        self.assertEqual(Schedule.objects.count(), 2)
        self.assertEqual(Link.objects.count(), 2)

    def test_authenticated_lists_preserve_country_filter(self):
        self.authenticate(self.student)
        for endpoint in self.endpoints:
            with self.subTest(endpoint=endpoint):
                response = self.client.get(reverse(f'{endpoint}-list'))
                self.assertEqual(response.status_code, status.HTTP_200_OK)
                self.assertEqual([obj['id'] for obj in response.data['results']], [self.visible_ids[endpoint]])

    def test_authenticated_user_without_country_gets_empty_lists(self):
        self.authenticate(self.unassigned)
        for endpoint in self.endpoints:
            with self.subTest(endpoint=endpoint):
                response = self.client.get(reverse(f'{endpoint}-list'))
                self.assertEqual(response.status_code, status.HTTP_200_OK)
                self.assertEqual(response.data['results'], [])
