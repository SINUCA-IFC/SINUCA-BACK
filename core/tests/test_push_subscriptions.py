import importlib.util
import json
from unittest.mock import patch

from django.test import override_settings
from rest_framework.test import APITestCase

from core.models import PushSubscription, User


class PushSubscriptionApiTests(APITestCase):
    subscription = {
        'endpoint': 'https://push.example.test/subscriptions/browser-a',
        'keys': {
            'p256dh': 'browser-public-key',
            'auth': 'browser-auth-secret',
        },
    }

    @classmethod
    def setUpTestData(cls):
        cls.first_user = User.objects.create_user(email='push-first@example.test')
        cls.second_user = User.objects.create_user(email='push-second@example.test')

    @override_settings(VAPID_PUBLIC_KEY='public-vapid-key')
    def test_public_vapid_endpoint_exposes_only_public_key_without_authentication(self):
        response = self.client.get('/api/vapid-public-key/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, {'publicKey': 'public-vapid-key'})

    def test_subscription_registration_and_removal_require_authentication(self):
        post_response = self.client.post('/api/push-subscriptions/', self.subscription, format='json')
        delete_response = self.client.delete(
            '/api/push-subscriptions/',
            {'endpoint': self.subscription['endpoint']},
            format='json',
        )

        self.assertEqual(post_response.status_code, 401)
        self.assertEqual(delete_response.status_code, 401)

    def test_malformed_subscription_is_rejected_without_partial_registration(self):
        self.client.force_authenticate(self.first_user)

        missing_auth = self.client.post(
            '/api/push-subscriptions/',
            {
                'endpoint': self.subscription['endpoint'],
                'keys': {'p256dh': 'browser-public-key'},
            },
            format='json',
        )
        empty_endpoint = self.client.post(
            '/api/push-subscriptions/',
            {
                'endpoint': '',
                'keys': self.subscription['keys'],
            },
            format='json',
        )

        self.assertEqual(missing_auth.status_code, 400)
        self.assertEqual(empty_endpoint.status_code, 400)
        self.assertEqual(
            self.client.delete(
                '/api/push-subscriptions/',
                {'endpoint': self.subscription['endpoint']},
                format='json',
            ).status_code,
            404,
        )

    def test_registering_existing_endpoint_transfers_it_to_current_account(self):
        self.client.force_authenticate(self.first_user)
        created = self.client.post('/api/push-subscriptions/', self.subscription, format='json')

        self.client.force_authenticate(self.second_user)
        updated_payload = {
            **self.subscription,
            'keys': {'p256dh': 'new-public-key', 'auth': 'new-auth-secret'},
        }
        transferred = self.client.post('/api/push-subscriptions/', updated_payload, format='json')

        self.client.force_authenticate(self.first_user)
        former_owner_delete = self.client.delete(
            '/api/push-subscriptions/',
            {'endpoint': self.subscription['endpoint']},
            format='json',
        )
        self.client.force_authenticate(self.second_user)
        current_owner_delete = self.client.delete(
            '/api/push-subscriptions/',
            {'endpoint': self.subscription['endpoint']},
            format='json',
        )

        self.assertEqual(created.status_code, 201)
        self.assertEqual(transferred.status_code, 200)
        self.assertEqual(former_owner_delete.status_code, 404)
        self.assertEqual(current_owner_delete.status_code, 204)


class PushDeliveryServiceContractTests(APITestCase):
    def test_push_delivery_service_is_available(self):
        try:
            service_spec = importlib.util.find_spec('core.services.push')
        except ModuleNotFoundError:
            service_spec = None

        self.assertIsNotNone(service_spec)


class PushDeliveryServiceTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.active_user = User.objects.create_user(email='push-active@example.test')
        cls.other_active_user = User.objects.create_user(email='push-other@example.test')
        cls.inactive_user = User.objects.create_user(email='push-inactive@example.test', is_active=False)
        cls.origin = PushSubscription.objects.create(
            user=cls.active_user,
            endpoint='https://push.example.test/origin',
            p256dh='origin-key',
            auth='origin-auth',
        )
        cls.recipient = PushSubscription.objects.create(
            user=cls.other_active_user,
            endpoint='https://push.example.test/recipient',
            p256dh='recipient-key',
            auth='recipient-auth',
        )
        PushSubscription.objects.create(
            user=cls.inactive_user,
            endpoint='https://push.example.test/inactive-user',
            p256dh='inactive-key',
            auth='inactive-auth',
        )
        PushSubscription.objects.create(
            user=cls.other_active_user,
            endpoint='https://push.example.test/inactive-subscription',
            p256dh='disabled-key',
            auth='disabled-auth',
            active=False,
        )

    @override_settings(
        VAPID_PUBLIC_KEY='public-vapid-key',
        VAPID_PRIVATE_KEY='private-vapid-key',
        VAPID_SUBJECT='mailto:push@example.test',
    )
    def test_delivery_targets_active_users_and_excludes_origin_endpoint(self):
        from core.services.push import send_push_event

        payload = {
            'event': 'post_created',
            'title': 'Nova postagem',
            'body': 'Comunicado',
            'data': {'post_id': 10, 'url': '/mural'},
        }
        with patch('core.services.push.webpush', create=True) as mocked_webpush:
            delivered = send_push_event(payload, excluded_endpoint=self.origin.endpoint)

        self.assertEqual(delivered, 1)
        self.assertEqual(mocked_webpush.call_count, 1)
        call = mocked_webpush.call_args.kwargs
        self.assertEqual(call['subscription_info'], {
            'endpoint': self.recipient.endpoint,
            'keys': {'p256dh': 'recipient-key', 'auth': 'recipient-auth'},
        })
        self.assertEqual(json.loads(call['data']), payload)
        self.assertEqual(call['vapid_private_key'], 'private-vapid-key')
        self.assertEqual(call['vapid_claims'], {'sub': 'mailto:push@example.test'})

    @override_settings(VAPID_PRIVATE_KEY='', VAPID_SUBJECT='mailto:push@example.test')
    def test_missing_private_key_skips_delivery_without_error(self):
        from core.services.push import send_push_event

        with patch('core.services.push.webpush', create=True) as mocked_webpush:
            delivered = send_push_event({'event': 'post_created'})

        self.assertEqual(delivered, 0)
        mocked_webpush.assert_not_called()

    @override_settings(VAPID_PRIVATE_KEY='private-vapid-key', VAPID_SUBJECT='mailto:push@example.test')
    def test_gone_endpoint_is_deactivated(self):
        from core.services.push import send_push_event

        class GoneResponse:
            status_code = 410

        class GonePushError(Exception):
            response = GoneResponse()

        with (
            patch('core.services.push.WebPushException', GonePushError, create=True),
            patch('core.services.push.webpush', side_effect=GonePushError, create=True),
        ):
            delivered = send_push_event(
                {'event': 'post_created'},
                excluded_endpoint=self.origin.endpoint,
            )

        self.recipient.refresh_from_db()
        self.assertEqual(delivered, 0)
        self.assertFalse(self.recipient.active)

    @override_settings(VAPID_PRIVATE_KEY='private-vapid-key', VAPID_SUBJECT='mailto:push@example.test')
    def test_missing_endpoint_is_deactivated(self):
        from core.services.push import send_push_event

        class MissingResponse:
            status_code = 404

        class MissingPushError(Exception):
            response = MissingResponse()

        with (
            patch('core.services.push.WebPushException', MissingPushError),
            patch('core.services.push.webpush', side_effect=MissingPushError),
        ):
            delivered = send_push_event(
                {'event': 'post_created'},
                excluded_endpoint=self.origin.endpoint,
            )

        self.recipient.refresh_from_db()
        self.assertEqual(delivered, 0)
        self.assertFalse(self.recipient.active)

    @override_settings(VAPID_PRIVATE_KEY='private-vapid-key', VAPID_SUBJECT='mailto:push@example.test')
    def test_non_expiration_push_error_does_not_disable_subscription(self):
        from core.services.push import send_push_event

        class ErrorResponse:
            status_code = 500

        class TemporaryPushError(Exception):
            response = ErrorResponse()

        with (
            patch('core.services.push.WebPushException', TemporaryPushError, create=True),
            patch('core.services.push.webpush', side_effect=TemporaryPushError, create=True),
        ):
            delivered = send_push_event(
                {'event': 'post_created'},
                excluded_endpoint=self.origin.endpoint,
            )

        self.recipient.refresh_from_db()
        self.assertEqual(delivered, 0)
        self.assertTrue(self.recipient.active)
