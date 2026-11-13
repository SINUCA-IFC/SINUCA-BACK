import json
from unittest.mock import patch

from django.test import override_settings
from rest_framework.test import APITestCase

from core.models import Post, PushSubscription, User


@override_settings(
    VAPID_PRIVATE_KEY='private-vapid-key',
    VAPID_SUBJECT='mailto:push@example.test',
)
class PostPushNotificationTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.organizer = User.objects.create_user(
            email='post-organizer@example.test',
            role=User.Role.ORGANIZER,
        )
        cls.first_recipient = User.objects.create_user(email='post-first@example.test')
        cls.second_recipient = User.objects.create_user(email='post-second@example.test')
        cls.origin = PushSubscription.objects.create(
            user=cls.organizer,
            endpoint='https://push.example.test/post-origin',
            p256dh='origin-key',
            auth='origin-auth',
        )
        cls.first_subscription = PushSubscription.objects.create(
            user=cls.first_recipient,
            endpoint='https://push.example.test/post-first',
            p256dh='first-key',
            auth='first-auth',
        )
        cls.second_subscription = PushSubscription.objects.create(
            user=cls.second_recipient,
            endpoint='https://push.example.test/post-second',
            p256dh='second-key',
            auth='second-auth',
        )

    def setUp(self):
        self.client.force_authenticate(self.organizer)

    def test_post_creation_notifies_subscribed_users_except_origin_browser(self):
        with (
            patch('core.services.push.webpush') as mocked_webpush,
            self.captureOnCommitCallbacks(execute=True),
        ):
            response = self.client.post(
                '/api/postagens/',
                {'title': 'Mudança de horário', 'content': 'Confira o novo cronograma.'},
                format='json',
                HTTP_X_PUSH_ENDPOINT=self.origin.endpoint,
            )

        self.assertEqual(response.status_code, 201)
        self.assertTrue(Post.objects.filter(pk=response.data['id']).exists())
        endpoints = {
            call.kwargs['subscription_info']['endpoint']
            for call in mocked_webpush.call_args_list
        }
        self.assertEqual(endpoints, {
            self.first_subscription.endpoint,
            self.second_subscription.endpoint,
        })
        payloads = [json.loads(call.kwargs['data']) for call in mocked_webpush.call_args_list]
        self.assertEqual(payloads, [{
            'event': 'post_created',
            'title': 'Nova postagem no mural',
            'body': 'Mudança de horário',
            'data': {'post_id': response.data['id'], 'url': '/mural'},
        }] * 2)

    def test_push_failure_does_not_reject_or_undo_post_creation(self):
        with (
            patch(
                'core.views.post.send_push_event',
                side_effect=RuntimeError('Push Service unavailable'),
                create=True,
            ) as mocked_send,
            self.captureOnCommitCallbacks(execute=True),
        ):
            response = self.client.post(
                '/api/postagens/',
                {'title': 'Postagem preservada', 'content': 'O push pode falhar.'},
                format='json',
            )

        self.assertEqual(response.status_code, 201)
        self.assertTrue(Post.objects.filter(pk=response.data['id']).exists())
        mocked_send.assert_called_once()
