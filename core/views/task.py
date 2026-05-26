from rest_framework.viewsets import ModelViewSet

from core.models import Task
from core.serializers import TaskDetailSerializer, TaskListSerializer, TaskSerializer


class TaskViewSet(ModelViewSet):
    serializer_class = TaskSerializer

    def get_queryset(self):
        usuario = self.request.user

        if usuario.is_superuser:
            return Task.objects.all()

        grupos = list(usuario.groups.values_list('name', flat=True))

        pais = next((g for g in grupos if g not in {'Alunos', 'Organizadores', 'Avaliadores'}), None)

        if not pais:
            return Task.objects.none()

        return Task.objects.filter(
            creator__groups__name=pais
        ).distinct()

    def get_serializer_class(self):
        if self.action == 'list':
            return TaskListSerializer
        elif self.action == 'retrieve':
            return TaskDetailSerializer
        return TaskSerializer
