from rest_framework.viewsets import ModelViewSet

from core.models import Schedule
from core.serializers import ScheduleSerializer


class ScheduleViewSet(ModelViewSet):
    queryset = Schedule.objects.order_by('endDate')
    serializer_class = ScheduleSerializer
