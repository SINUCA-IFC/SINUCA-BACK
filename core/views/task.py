from rest_framework.viewsets import ModelViewSet

from core.serializers import TaskSerializer, TaskDetailSerializer, TaskListSerializer
from core.models import Task

class TaskViewSet(ModelViewSet):
    queryset = Task.objects.all()
    serializer_class = TaskSerializer
    
    def get_serializer_class(self):
        if self.action == 'list':
            return TaskListSerializer
        elif self.action == 'retrieve':
            return TaskDetailSerializer
        return TaskSerializer