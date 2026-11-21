# ruff: noqa: PLR2004 -- Tamanhos criptográficos e resultados esperados dos testes.
import json
import secrets
from base64 import urlsafe_b64encode
from unittest.mock import patch

import http_ece
import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec
from django.test import override_settings
from py_vapid import Vapid
from requests import Response
from rest_framework.test import APITestCase

from core.models import Country, User


def encode(value):
    return urlsafe_b64encode(value).rstrip(b'=').decode()


class ChatPushEncryptionTests(APITestCase):
    """Executa pywebpush de verdade; somente a conexão HTTP externa é substituída."""

    @classmethod
    def setUpTestData(cls):
        country = Country.objects.create(name='Brasil', political_name='Brasil')
        cls.student = User.objects.create_user(email='crypto-student@example.test', country=country)
        cls.organizer = User.objects.create_user(email='crypto-organizer@example.test', role='organizer')

    def send_message(self, sender, recipient, private_format):
        vapid = Vapid()
        vapid.generate_keys()
        public = encode(
            vapid.public_key.public_bytes(
                serialization.Encoding.X962,
                serialization.PublicFormat.UncompressedPoint,
            )
        )
        private = encode(vapid.private_key.private_numbers().private_value.to_bytes(32, 'big'))
        if private_format == 'der':
            private = encode(
                vapid.private_key.private_bytes(
                    serialization.Encoding.DER,
                    serialization.PrivateFormat.PKCS8,
                    serialization.NoEncryption(),
                )
            )
        browser_key = ec.generate_private_key(ec.SECP256R1())
        browser_public = browser_key.public_key().public_bytes(
            serialization.Encoding.X962,
            serialization.PublicFormat.UncompressedPoint,
        )
        auth = secrets.token_bytes(16)
        self.client.force_authenticate(recipient)
        registered = self.client.post(
            '/api/push-subscriptions/',
            {
                'endpoint': 'https://updates.push.example.test/browser',
                'keys': {'p256dh': encode(browser_public), 'auth': encode(auth)},
            },
            format='json',
        )
        assert registered.status_code == 201

        received = []

        def accept_push(endpoint, data, headers, timeout):
            assert endpoint == 'https://updates.push.example.test/browser'
            authorization = dict(part.split('=', 1) for part in headers['authorization'][6:].split(','))
            assert authorization['k'] == public
            claims = jwt.decode(
                authorization['t'],
                vapid.public_key,
                algorithms=['ES256'],
                audience='https://updates.push.example.test',
            )
            assert claims['sub'] == 'mailto:push@example.test'
            payload = http_ece.decrypt(data, private_key=browser_key, auth_secret=auth, version='aes128gcm')
            received.append(json.loads(payload))
            response = Response()
            response.status_code = 201
            return response

        self.client.force_authenticate(sender)
        with (
            override_settings(
                VAPID_PUBLIC_KEY=public, VAPID_PRIVATE_KEY=private, VAPID_SUBJECT='mailto:push@example.test'
            ),
            patch('pywebpush.requests.post', side_effect=accept_push),
            self.captureOnCommitCallbacks(execute=True),
        ):
            response = self.client.post(
                '/api/mensagens/',
                {
                    'country': self.student.country_id,
                    'text': 'Mensagem privada',
                },
                format='json',
                HTTP_X_PUSH_ENDPOINT='https://push.example.test/sender',
            )

        assert response.status_code == 201
        assert len(received) == 1
        assert received[0]['event'] == 'message_created'
        assert received[0]['data']['message_id'] == response.data['id']
        assert 'Mensagem privada' not in received[0]['body']

    def test_organizer_message_can_be_authenticated_and_decrypted_by_delegate(self):
        self.send_message(self.organizer, self.student, 'raw')

    def test_delegate_message_can_be_authenticated_and_decrypted_by_organizer(self):
        self.send_message(self.student, self.organizer, 'der')
