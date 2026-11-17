from django.conf import settings
from django.db import models

from .category import Category
from .user import User


class Task(models.Model):
    class Status(models.IntegerChoices):
        TO_DO = 1, 'A fazer',
        IN_PROGRESS = 2, 'Em andamento',
        DONE = 3, 'Concluído'

    creator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='created_tasks'
    )

    title = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)
    category = models.ManyToManyField(Category, related_name="tasks")
    endDate = models.DateField(null=True, blank=True)
    postDate = models.DateField(auto_now_add=True)
    startDate = models.DateField(null=True, blank=True)
    status = models.IntegerField(choices=Status.choices)
    user = models.ManyToManyField(User, related_name='tasks')
    notification = models.BooleanField(default=False)

    def __str__(self):
        return self.title

    class Meta:
        verbose_name = "Tarefa"
        verbose_name_plural = "Tarefas"


class TaskOverdueNotification(models.Model):
    """Um aviso de atraso por responsável e prazo, independente de leitura."""
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='overdue_notifications')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    deadline = models.DateField()
    sent_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(
            fields=['task', 'user', 'deadline'], name='unique_task_user_overdue_deadline',
        )]
