import os
from base64 import b64decode

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec
from django.conf import settings
from django.core import checks
from py_vapid import Vapid


@checks.register('webpush')
def check_web_push(app_configs, **kwargs):
    public = settings.VAPID_PUBLIC_KEY
    private = settings.VAPID_PRIVATE_KEY
    if not public or not private:
        return [
            checks.Warning(
                'Configuração Web Push incompleta: faltam chaves VAPID.',
                hint='Configure VAPID_PUBLIC_KEY e VAPID_PRIVATE_KEY do mesmo par e reinicie o backend.',
                id='core.W001',
            )
        ]
    try:
        vapid = Vapid.from_file(private) if os.path.isfile(private) else Vapid.from_string(private)
        if not isinstance(vapid.public_key, ec.EllipticCurvePublicKey) or not isinstance(
            vapid.public_key.curve, ec.SECP256R1
        ):
            raise ValueError('VAPID requires P-256.')
        expected = vapid.public_key.public_bytes(
            serialization.Encoding.X962,
            serialization.PublicFormat.UncompressedPoint,
        )
    except Exception:
        return [
            checks.Warning(
                'VAPID_PRIVATE_KEY não pôde ser carregada.',
                hint='Use a chave privada em base64url ou o caminho de um arquivo PEM existente no servidor.',
                id='core.W002',
            )
        ]
    try:
        actual = b64decode(public + '=' * (-len(public) % 4), altchars=b'-_', validate=True)
    except ValueError:
        actual = None
    if actual != expected:
        return [
            checks.Warning(
                'VAPID_PUBLIC_KEY é inválida ou não corresponde à VAPID_PRIVATE_KEY.',
                hint='Configure as duas chaves geradas juntas. O navegador precisará renovar a inscrição.',
                id='core.W003',
            )
        ]
    try:
        vapid.sign({'sub': settings.VAPID_SUBJECT, 'aud': 'https://push.example.test'})
    except Exception:
        return [
            checks.Warning(
                'VAPID_SUBJECT não é um contato válido para envio Web Push.',
                hint='Use mailto:seu-email@dominio.com ou uma URL HTTPS de contato.',
                id='core.W004',
            )
        ]
    return []
