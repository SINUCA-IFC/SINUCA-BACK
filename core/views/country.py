from rest_framework.viewsets import ModelViewSet

from core.models import Country
from core.serializers import CountrySerializer


class CountryViewSet(ModelViewSet):
    queryset = Country.objects.all()
    serializer_class = CountrySerializer
