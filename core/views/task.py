from django.db.models import Q
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ModelViewSet

from core.models import Task
from core.permissions import HasDelegationForWrite
from core.serializers import TaskDetailSerializer, TaskListSerializer, TaskSerializer
from core.services.notifications import schedule_push_event, task_payload


class TaskViewSet(ModelViewSet):
    serializer_class = TaskSerializer
    permission_classes = [IsAuthenticated, HasDelegationForWrite]

    def perform_create(self, serializer):
        task = serializer.save(creator=self.request.user)
        self.notify_assignees(task, set())

    def perform_update(self, serializer):
        previous = set(serializer.instance.user.values_list('id', flat=True))
        task = serializer.save()
        self.notify_assignees(task, previous)

    def notify_assignees(self, task, previous):
        added = sorted(set(task.user.values_list('id', flat=True)) - previous)
        if added:
            schedule_push_event(
                task_payload(task, 'task_assigned'),
                user_ids=added,
                excluded_endpoint=self.request.headers.get('X-Push-Endpoint'),
            )

    def get_queryset(self):
        usuario = self.request.user
        if usuario.is_superuser:
            return Task.objects.all().order_by('id')

        scope = Q(user=usuario)
        if usuario.country_id:
            scope |= Q(creator__country_id=usuario.country_id)
        return Task.objects.filter(scope).distinct().order_by('id')

    def get_serializer_class(self):
        if self.action == 'list':
            return TaskListSerializer
        elif self.action == 'retrieve':
            return TaskDetailSerializer
        return TaskSerializer
