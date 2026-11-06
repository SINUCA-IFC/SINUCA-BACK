from rest_framework.viewsets import ModelViewSet

from core.models import Country
from core.permissions import IsOrganizerOrReadOnly
from core.serializers import CountrySerializer


class CountryViewSet(ModelViewSet):
    permission_classes = [IsOrganizerOrReadOnly]
    queryset = Country.objects.all()
    serializer_class = CountrySerializer
