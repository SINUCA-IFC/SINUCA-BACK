from rest_framework.viewsets import ModelViewSet

from core.models import Task
from core.serializers import TaskDetailSerializer, TaskListSerializer, TaskSerializer


class TaskViewSet(ModelViewSet):
    serializer_class = TaskSerializer

    def get_queryset(self):
        usuario = self.request.user
        if usuario.is_superuser:
            return Task.objects.all()

        if not usuario.country:
            return Task.objects.none()

        return Task.objects.filter(
        creator__country=usuario.country
        ).distinct()

    def get_serializer_class(self):
        if self.action == 'list':
            return TaskListSerializer
        elif self.action == 'retrieve':
            return TaskDetailSerializer
        return TaskSerializer
