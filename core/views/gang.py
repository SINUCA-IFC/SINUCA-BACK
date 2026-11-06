from rest_framework.viewsets import ModelViewSet

from core.models import Gang
from core.permissions import IsOrganizerOrReadOnly
from core.serializers import GangSerializer


class GangViewSet(ModelViewSet):
    permission_classes = [IsOrganizerOrReadOnly]
    queryset = Gang.objects.all()
    serializer_class = GangSerializer
