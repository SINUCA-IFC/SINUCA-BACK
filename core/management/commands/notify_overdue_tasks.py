from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from core.models import Task, TaskOverdueNotification
from core.services.notifications import deliver_push_event, task_payload


class Command(BaseCommand):
    help = 'Notifica responsáveis sobre tarefas vencidas ainda não concluídas (seguro para reexecutar).'

    def handle(self, *args, **options):
        today = timezone.localdate()
        task_ids = Task.objects.filter(endDate__lt=today).exclude(status=Task.Status.DONE).values_list('pk', flat=True)
        sent = 0
        for task_id in task_ids.iterator():
            # Serializa execuções simultâneas no PostgreSQL e revalida o prazo/status.
            with transaction.atomic():
                task = (
                    Task.objects
                    .select_for_update()
                    .filter(pk=task_id, endDate__lt=today)
                    .exclude(
                        status=Task.Status.DONE,
                    )
                    .first()
                )
                if task is None:
                    continue
                for user_id in task.user.filter(is_active=True).values_list('pk', flat=True):
                    receipt = {'task': task, 'user_id': user_id, 'deadline': task.endDate}
                    if TaskOverdueNotification.objects.filter(**receipt).exists():
                        continue
                    delivered = deliver_push_event(task_payload(task, 'task_overdue'), user_ids=[user_id])
                    if delivered:
                        TaskOverdueNotification.objects.create(**receipt)
                        sent += 1
        self.stdout.write(self.style.SUCCESS(f'{sent} aviso(s) de atraso enviado(s).'))
