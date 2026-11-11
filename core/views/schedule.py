from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ModelViewSet

from core.models import Schedule
from core.permissions import HasDelegationForWrite, IsOrganizerOrReadOnly
from core.serializers import ScheduleSerializer


class ScheduleViewSet(ModelViewSet):
    permission_classes = [IsAuthenticated, HasDelegationForWrite, IsOrganizerOrReadOnly]

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Schedule.objects.none()
        usuario = self.request.user
        if usuario.is_superuser or usuario.is_organizer:
            return Schedule.objects.all().order_by('startDate', 'id')

        if not usuario.country:
            return Schedule.objects.none()

        return Schedule.objects.filter(
        country=usuario.country
        ).distinct().order_by('startDate')

    serializer_class = ScheduleSerializer
