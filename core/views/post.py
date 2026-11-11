from rest_framework.viewsets import ModelViewSet

from core.models import Post
from core.permissions import IsOrganizerOrReadOnly
from core.serializers import PostSerializer


class PostViewSet(ModelViewSet):
    permission_classes = [IsOrganizerOrReadOnly]
    queryset = Post.objects.all().order_by('id')
    serializer_class = PostSerializer
