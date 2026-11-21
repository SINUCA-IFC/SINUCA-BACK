# ruff: noqa: PLR2004 -- Resultados esperados dos testes.
from datetime import timedelta
from io import StringIO
from unittest.mock import patch

from django.core.management import call_command
from django.test import override_settings
from django.utils import timezone
from requests.exceptions import Timeout
from rest_framework.test import APITestCase

from core.models import PushSubscription, Task, TaskOverdueNotification, User
from core.services.push import send_push_event


@override_settings(VAPID_PRIVATE_KEY='private-key', VAPID_SUBJECT='mailto:push@example.test')
class PushDeliveryResilienceTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(email='delivery-resilience@example.test')
        for number in range(3):
            PushSubscription.objects.create(
                user=cls.user, endpoint=f'https://push.test/{number}', p256dh='key', auth='auth'
            )

    def test_one_failed_endpoint_does_not_lose_successes_or_skip_other_endpoints(self):
        for error in [Timeout('offline'), ValueError('invalid browser key')]:
            with (
                self.subTest(error=error),
                patch('core.services.push.webpush', side_effect=[None, error, None]) as send,
            ):
                delivered = send_push_event({'event': 'post_created'})
                assert delivered == 2
                assert send.call_count == 3

    def test_push_is_retained_for_a_day_for_temporarily_offline_devices(self):
        with patch('core.services.push.webpush') as send:
            send_push_event({'event': 'task_overdue'})
        assert send.call_args.kwargs['ttl'] == 86400

    def test_logs_distinguish_provider_acceptance_from_failed_delivery_without_private_data(self):
        with (
            patch('core.services.push.webpush', side_effect=[None, Timeout('private-error'), None]),
            self.assertLogs('core.services.push', level='INFO') as logs,
        ):
            delivered = send_push_event({'event': 'message_created', 'body': 'private-message'})
        assert delivered == 2
        output = '\n'.join(logs.output)
        assert 'event=message_created attempted=3 accepted=2 failed=1' in output
        assert 'private-message' not in output
        assert 'private-error' not in output
        assert 'https://push.test/' not in output
        assert 'private-key' not in output

    def test_logs_when_no_subscriptions_match_the_event_recipients(self):
        with self.assertLogs('core.services.push', level='INFO') as logs:
            delivered = send_push_event({'event': 'message_created'}, user_ids=[])
        assert delivered == 0
        assert 'event=message_created attempted=0 accepted=0 failed=0' in '\n'.join(logs.output)

    def test_partial_success_records_overdue_receipt_and_does_not_repeat_next_run(self):
        task = Task.objects.create(
            creator=self.user, title='Prazo', status=1, endDate=timezone.localdate() - timedelta(days=1)
        )
        task.user.add(self.user)
        with patch('core.services.push.webpush', side_effect=[None, Timeout('offline'), None]) as send:
            call_command('notify_overdue_tasks', stdout=StringIO())
            call_command('notify_overdue_tasks', stdout=StringIO())
        assert send.call_count == 3
        assert TaskOverdueNotification.objects.filter(task=task, user=self.user).count() == 1
