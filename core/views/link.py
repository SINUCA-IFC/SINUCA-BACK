from rest_framework.viewsets import ModelViewSet

from core.models import Link
from core.serializers import LinkSerializer


class LinkViewSet(ModelViewSet):

    def get_queryset(self):
        usuario = self.request.user
        if usuario.is_superuser:
            return Link.objects.all()

        if not usuario.country:
            return Link.objects.none()

        return Link.objects.filter(
        country=usuario.country
        ).distinct()

    serializer_class = LinkSerializer
