# ruff: noqa: PLR2004 -- Tamanhos criptográficos e resultados esperados dos testes.
from base64 import urlsafe_b64encode
from pathlib import Path
from tempfile import TemporaryDirectory

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec
from django.core.checks import run_checks
from django.test import SimpleTestCase, override_settings
from py_vapid import Vapid


def encode(value):
    return urlsafe_b64encode(value).rstrip(b'=').decode()


class PushConfigurationTests(SimpleTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.vapid = Vapid()
        cls.vapid.generate_keys()
        cls.public = encode(
            cls.vapid.public_key.public_bytes(
                serialization.Encoding.X962,
                serialization.PublicFormat.UncompressedPoint,
            )
        )
        cls.private = encode(cls.vapid.private_key.private_numbers().private_value.to_bytes(32, 'big'))

    def check(self, **overrides):
        config = {
            'VAPID_PUBLIC_KEY': self.public,
            'VAPID_PRIVATE_KEY': self.private,
            'VAPID_SUBJECT': 'mailto:push@example.test',
            **overrides,
        }
        with override_settings(**config):
            return run_checks(tags=['webpush'])

    def test_matching_pair_is_valid(self):
        assert self.check() == []

    def test_disabled_push_is_reported(self):
        messages = self.check(VAPID_PUBLIC_KEY='', VAPID_PRIVATE_KEY='')
        assert [message.id for message in messages] == ['core.W001']

    def test_missing_half_of_pair_is_reported_without_disclosing_keys(self):
        for missing in ['VAPID_PUBLIC_KEY', 'VAPID_PRIVATE_KEY']:
            with self.subTest(missing=missing):
                messages = self.check(**{missing: ''})
                assert [message.id for message in messages] == ['core.W001']
                assert self.private not in str(messages)

    def test_invalid_private_key_is_reported(self):
        messages = self.check(VAPID_PRIVATE_KEY='invalid-private-value')
        assert [message.id for message in messages] == ['core.W002']
        assert 'invalid-private-value' not in str(messages)

    def test_private_key_using_a_different_curve_is_reported(self):
        private = ec.generate_private_key(ec.SECP384R1()).private_bytes(
            serialization.Encoding.DER,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
        messages = self.check(VAPID_PRIVATE_KEY=encode(private))
        assert [message.id for message in messages] == ['core.W002']

    def test_mismatched_public_key_is_reported(self):
        other = Vapid()
        other.generate_keys()
        public = encode(
            other.public_key.public_bytes(
                serialization.Encoding.X962,
                serialization.PublicFormat.UncompressedPoint,
            )
        )
        messages = self.check(VAPID_PUBLIC_KEY=public)
        assert [message.id for message in messages] == ['core.W003']

    def test_invalid_public_key_is_reported(self):
        messages = self.check(VAPID_PUBLIC_KEY='not-a-public-key')
        assert [message.id for message in messages] == ['core.W003']

    def test_contact_without_mailto_or_https_is_reported(self):
        messages = self.check(VAPID_SUBJECT='push@example.test')
        assert [message.id for message in messages] == ['core.W004']

    def test_der_and_pem_file_private_keys_are_supported(self):
        der = self.vapid.private_key.private_bytes(
            serialization.Encoding.DER,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
        assert self.check(VAPID_PRIVATE_KEY=encode(der)) == []
        with TemporaryDirectory() as directory:
            path = Path(directory) / 'private.pem'
            path.write_bytes(self.vapid.private_pem())
            assert self.check(VAPID_PRIVATE_KEY=str(path)) == []
