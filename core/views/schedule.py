from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ModelViewSet

from core.models import Schedule
from core.permissions import HasDelegationForWrite
from core.serializers import ScheduleSerializer


class ScheduleViewSet(ModelViewSet):
    permission_classes = [IsAuthenticated, HasDelegationForWrite]

    def get_queryset(self):
        usuario = self.request.user
        if usuario.is_superuser:
            return Schedule.objects.all()

        if not usuario.country:
            return Schedule.objects.none()

        return Schedule.objects.filter(
        country=usuario.country
        ).distinct().order_by('startDate')

    serializer_class = ScheduleSerializer
