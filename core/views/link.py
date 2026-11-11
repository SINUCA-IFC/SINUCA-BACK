from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ModelViewSet

from core.models import Link
from core.permissions import HasDelegationForWrite, IsOrganizerOrReadOnly
from core.serializers import LinkSerializer


class LinkViewSet(ModelViewSet):
    permission_classes = [IsAuthenticated, HasDelegationForWrite, IsOrganizerOrReadOnly]

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Link.objects.none()
        usuario = self.request.user
        if usuario.is_superuser or usuario.is_organizer:
            return Link.objects.all().order_by('id')

        if not usuario.country:
            return Link.objects.none()

        return Link.objects.filter(
        country=usuario.country
        ).distinct()

    serializer_class = LinkSerializer
