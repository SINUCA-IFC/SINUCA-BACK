from rest_framework.viewsets import ModelViewSet

from core.models import Gang
from core.serializers import GangSerializer


class GangViewSet(ModelViewSet):
    queryset = Gang.objects.all()
    serializer_class = GangSerializer
