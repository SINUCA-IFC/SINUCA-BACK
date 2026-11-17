import logging

from django.db import transaction
from rest_framework.viewsets import ModelViewSet

from core.models import Post
from core.permissions import IsOrganizerOrReadOnly
from core.serializers import PostSerializer
from core.services.push import send_push_event

logger = logging.getLogger(__name__)


def notify_post_created(post, excluded_endpoint):
    payload = {
        'event': 'post_created',
        'title': 'Nova postagem no mural',
        'body': post.title,
        'data': {'post_id': post.pk, 'url': '/mural'},
    }
    try:
        send_push_event(payload, excluded_endpoint=excluded_endpoint)
    except Exception:
        logger.exception('Post %s was created, but its Web Push notification failed.', post.pk)


class PostViewSet(ModelViewSet):
    permission_classes = [IsOrganizerOrReadOnly]
    queryset = Post.objects.all().order_by('id')
    serializer_class = PostSerializer

    def perform_create(self, serializer):
        post = serializer.save()
        excluded_endpoint = self.request.headers.get('X-Push-Endpoint')
        transaction.on_commit(lambda: notify_post_created(post, excluded_endpoint))
