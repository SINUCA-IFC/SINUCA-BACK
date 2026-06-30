from rest_framework.viewsets import ModelViewSet

from core.models import Link
from core.serializers import LinkSerializer


class LinkViewSet(ModelViewSet):
    queryset = Link.objects.all()
    serializer_class = LinkSerializer
