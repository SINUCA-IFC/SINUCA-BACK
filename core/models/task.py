from django.db import models
from .user import User
from .category import Category

class Task(models.Model):
    class Status(models.IntegerChoices):
        TO_DO = 1, 'A fazer',
        IN_PROGRESS = 2, 'Em andamento',
        DONE = 3, 'Concluído'

    title = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)
    category = models.ManyToManyField(Category, related_name="tasks")
    endDate = models.DateField(null=True, blank=True)
    postDate = models.DateField(auto_now_add=True)
    startDate = models.DateField(null=True, blank=True)    status = models.IntegerField(max_length=1, choices=Status.choices)
    user = models.ManyToManyField(User, related_name='tasks')
    notification = models.BooleanField(default=False)

    def __str__(self):
        return self.title
    
    class Meta:
        verbose_name = "Tarefa"
        verbose_name_plural = "Tarefas"