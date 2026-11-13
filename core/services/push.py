import json
import logging

from django.conf import settings
from pywebpush import WebPushException, webpush

from core.models import PushSubscription

logger = logging.getLogger(__name__)


def send_push_event(payload, *, excluded_endpoint=None, user_ids=None):
    if not settings.VAPID_PRIVATE_KEY:
        logger.warning('Web Push skipped because VAPID_PRIVATE_KEY is not configured.')
        return 0

    subscriptions = PushSubscription.objects.filter(active=True, user__is_active=True)
    if excluded_endpoint:
        subscriptions = subscriptions.exclude(endpoint=excluded_endpoint)
    if user_ids is not None:
        subscriptions = subscriptions.filter(user_id__in=user_ids)

    delivered = 0
    for subscription in subscriptions.iterator():
        try:
            webpush(
                subscription_info={
                    'endpoint': subscription.endpoint,
                    'keys': {
                        'p256dh': subscription.p256dh,
                        'auth': subscription.auth,
                    },
                },
                data=json.dumps(payload),
                vapid_private_key=settings.VAPID_PRIVATE_KEY,
                vapid_claims={'sub': settings.VAPID_SUBJECT},
            )
            delivered += 1
        except WebPushException as error:
            response_status = getattr(getattr(error, 'response', None), 'status_code', None)
            if response_status in {404, 410}:
                PushSubscription.objects.filter(pk=subscription.pk).update(active=False)
            logger.warning(
                'Web Push delivery failed for subscription %s with status %s.',
                subscription.pk,
                response_status,
            )
    return delivered
