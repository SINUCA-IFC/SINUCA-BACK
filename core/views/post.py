from rest_framework.viewsets import ModelViewSet

from core.models import Post
from core.permissions import IsOrganizerOrReadOnly
from core.serializers import PostSerializer
from core.services.notifications import post_payload, schedule_push_event


class PostViewSet(ModelViewSet):
    permission_classes = [IsOrganizerOrReadOnly]
    queryset = Post.objects.all().order_by('-created_at', '-id')
    serializer_class = PostSerializer

    def perform_create(self, serializer):
        post = serializer.save()
        excluded_endpoint = self.request.headers.get('X-Push-Endpoint')
        schedule_push_event(post_payload(post), excluded_endpoint=excluded_endpoint)
