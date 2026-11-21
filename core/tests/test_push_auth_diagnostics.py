# ruff: noqa: PLR2004 -- Códigos HTTP e tamanhos de chaves dos cenários de teste.
from base64 import urlsafe_b64encode
from unittest.mock import patch

from cryptography.hazmat.primitives import serialization
from django.test import override_settings
from py_vapid import Vapid
from pywebpush import WebPushException
from requests import Response
from rest_framework.test import APITestCase

from core.models import PushSubscription, User
from core.services.push import send_push_event


class PushAuthDiagnosticsTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        user = User.objects.create_user(email='push-auth@example.test')
        cls.subscription = PushSubscription.objects.create(
            user=user,
            endpoint='https://push.example.test/private-endpoint',
            p256dh='key',
            auth='auth',
        )

    def config(self):
        vapid = Vapid()
        vapid.generate_keys()
        public = vapid.public_key.public_bytes(
            serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint
        )
        private = vapid.private_key.private_numbers().private_value.to_bytes(32, 'big')
        return {
            'VAPID_PUBLIC_KEY': urlsafe_b64encode(public).rstrip(b'=').decode(),
            'VAPID_PRIVATE_KEY': urlsafe_b64encode(private).rstrip(b'=').decode(),
            'VAPID_SUBJECT': 'mailto:push@example.test',
        }

    def reject(self, status):
        response = Response()
        response.status_code = status
        return WebPushException('provider-body-with-sensitive-data', response=response)

    def test_auth_rejection_explains_key_mismatch_in_application_logs_without_secrets(self):
        config = self.config()
        config['VAPID_PUBLIC_KEY'] = self.config()['VAPID_PUBLIC_KEY']
        for status in (401, 403):
            with (
                self.subTest(status=status),
                override_settings(**config),
                patch('core.services.push.webpush', side_effect=self.reject(status)),
                self.assertLogs('core.services.push', level='WARNING') as logs,
            ):
                assert send_push_event({'event': 'message_created'}) == 0
            output = '\n'.join(logs.output)
            assert 'core.W003' in output
            assert config['VAPID_PRIVATE_KEY'] not in output
            assert 'provider-body-with-sensitive-data' not in output
            assert self.subscription.endpoint not in output

    def test_auth_rejection_with_consistent_keys_reports_that_configuration_passed(self):
        with (
            override_settings(**self.config()),
            patch('core.services.push.webpush', side_effect=self.reject(401)),
            self.assertLogs('core.services.push', level='WARNING') as logs,
        ):
            assert send_push_event({'event': 'message_created'}) == 0
        assert 'VAPID configuration is valid' in '\n'.join(logs.output)
        self.subscription.refresh_from_db()
        assert self.subscription.active
