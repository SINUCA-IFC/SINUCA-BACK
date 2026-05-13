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

        tipo_grupo = None
        pais = None

        for grupo in grupos:

            if grupo in {'Alunos', 'Organizadores'}:
                tipo_grupo = grupo

            else:
                pais = grupo

        if not tipo_grupo or not pais:
            return Task.objects.none()

        return Task.objects.filter(
            user__groups__name=tipo_grupo
        ).filter(
            user__groups__name=pais
        ).distinct()

    def get_serializer_class(self):
        if self.action == 'list':
            return TaskListSerializer
        elif self.action == 'retrieve':
            return TaskDetailSerializer
        return TaskSerializer
