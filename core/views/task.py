from rest_framework.viewsets import ModelViewSet

from core.models import Task
from core.serializers import TaskDetailSerializer, TaskListSerializer, TaskSerializer


class TaskViewSet(ModelViewSet):
    queryset = Task.objects.all()
    serializer_class = TaskSerializer

    def get_serializer_class(self):
        if self.action == 'list':
            return TaskListSerializer
        elif self.action == 'retrieve':
            return TaskDetailSerializer
        return TaskSerializer
