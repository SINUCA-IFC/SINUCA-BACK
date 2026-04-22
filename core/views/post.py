from rest_framework.viewsets import ModelViewSet

from core.models import Post
from core.serializers import PostSerializer


class PostViewSet(ModelViewSet):
    queryset = Post.objects.all()
    serializer_class = PostSerializer
