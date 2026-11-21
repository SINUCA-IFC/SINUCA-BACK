# ruff: noqa: PLR2004 -- Os números são resultados esperados dos testes.
from datetime import timedelta
from io import StringIO
from unittest.mock import patch

from django.core.management import call_command
from django.utils import timezone
from rest_framework.test import APITestCase

from core.models import Category, Country, Task, User


class TaskPushTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.country = Country.objects.create(name='Brasil', political_name='Brasil')
        cls.category = Category.objects.create(name='Pesquisa')
        cls.author = User.objects.create_user(email='task-author@example.test', country=cls.country)
        cls.first = User.objects.create_user(email='task-first@example.test', country=cls.country)
        cls.second = User.objects.create_user(email='task-second@example.test', country=cls.country)

    def setUp(self):
        self.client.force_authenticate(self.author)

    def save_task(self, payload, task=None):
        with self.captureOnCommitCallbacks(execute=True):
            if task:
                return self.client.patch(f'/api/tarefas/{task}/', payload, format='json')
            payload = {**payload, 'category': [self.category.pk]}
            return self.client.post(
                '/api/tarefas/', payload, format='json', HTTP_X_PUSH_ENDPOINT='https://push.test/origin'
            )

    @patch('core.services.notifications.send_push_event', return_value=1)
    def test_assignment_notifies_only_new_assignees_on_create_and_update(self, send):
        result = self.save_task({'title': 'Pesquisa', 'status': 1, 'user': [self.first.pk]})
        assert result.status_code == 201
        assert send.call_args.kwargs['user_ids'] == [self.first.pk]
        assert send.call_args.kwargs['excluded_endpoint'] == 'https://push.test/origin'
        assert send.call_args.args[0]['event'] == 'task_assigned'
        send.reset_mock()
        assert self.save_task({'title': 'Revisada'}, result.data['id']).status_code == 200
        send.assert_not_called()
        self.save_task({'user': [self.first.pk, self.second.pk]}, result.data['id'])
        assert send.call_args.kwargs['user_ids'] == [self.second.pk]
        send.reset_mock()
        self.save_task({'user': [self.second.pk]}, result.data['id'])
        send.assert_not_called()

    @patch('core.services.notifications.send_push_event', side_effect=RuntimeError('offline'))
    def test_push_failure_preserves_task(self, send):
        result = self.save_task({'title': 'Preservada', 'status': 1, 'user': [self.first.pk]})
        assert result.status_code == 201
        assert Task.objects.filter(pk=result.data['id']).exists()

    def test_assignee_can_open_notified_task_created_by_admin_without_country(self):
        admin = User.objects.create_superuser('task-admin@example.test', 'synthetic-password')
        task = Task.objects.create(creator=admin, title='Administrativa', status=1)
        task.user.add(self.first)
        self.client.force_authenticate(self.first)
        response = self.client.get(f'/api/tarefas/{task.pk}/')
        assert response.status_code == 200
        self.client.force_authenticate(self.second)
        assert self.client.get(f'/api/tarefas/{task.pk}/').status_code == 404

    def task(self, **kwargs):
        task = Task.objects.create(
            creator=self.author, title='Prazo', status=1, endDate=timezone.localdate() - timedelta(days=1), **kwargs
        )
        task.user.set([self.first, self.second])
        return task

    def test_assignee_without_country_can_read_only_explicitly_assigned_tasks(self):
        assigned = Task.objects.create(creator=self.author, title='Atribuída', status=1)
        private = Task.objects.create(creator=self.author, title='Outra', status=1)
        for role in [User.Role.STUDENT, User.Role.ORGANIZER]:
            user = User.objects.create_user(email=f'no-country-{role}@example.test', role=role)
            assigned.user.add(user)
            self.client.force_authenticate(user)
            assert self.client.get(f'/api/tarefas/{assigned.pk}/').status_code == 200
            assert self.client.get(f'/api/tarefas/{private.pk}/').status_code == 404
            result = self.client.get('/api/tarefas/')
            assert [row['id'] for row in result.data['results']] == [assigned.pk]
            if role == User.Role.STUDENT:
                assert self.client.patch(f'/api/tarefas/{assigned.pk}/', {'status': 3}).status_code == 403

    def run_overdue(self):
        call_command('notify_overdue_tasks', stdout=StringIO())

    @patch('core.services.notifications.send_push_event', return_value=1)
    def test_overdue_is_once_per_assignee_and_deadline(self, send):
        task = self.task()
        self.run_overdue()
        self.run_overdue()
        assert send.call_count == 2
        assert {c.kwargs['user_ids'][0] for c in send.call_args_list} == {self.first.pk, self.second.pk}
        assert send.call_args.args[0]['event'] == 'task_overdue'
        task.status = Task.Status.DONE
        task.save()
        self.run_overdue()
        task.status = Task.Status.TO_DO
        task.save()
        self.run_overdue()
        assert send.call_count == 2
        task.endDate -= timedelta(days=1)
        task.save()
        self.run_overdue()
        assert send.call_count == 4

    @patch('core.services.notifications.send_push_event', return_value=1)
    def test_only_overdue_unfinished_tasks_with_active_assignees_are_eligible(self, send):
        task = self.task()
        for deadline, status in [
            (None, 1),
            (timezone.localdate(), 1),
            (timezone.localdate() + timedelta(days=1), 1),
            (timezone.localdate() - timedelta(days=1), 3),
        ]:
            task.endDate, task.status = deadline, status
            task.save()
            self.run_overdue()
        send.assert_not_called()
        task.status = 2
        task.save()
        self.first.is_active = False
        self.first.save()
        self.run_overdue()
        assert send.call_args.kwargs['user_ids'] == [self.second.pk]
        assert send.call_count == 1

    @patch('core.services.notifications.send_push_event')
    def test_failed_or_skipped_delivery_can_retry(self, send):
        self.task()
        send.return_value = 0
        self.run_overdue()
        send.side_effect = RuntimeError('offline')
        self.run_overdue()
        send.side_effect = None
        send.return_value = 1
        self.run_overdue()
        self.run_overdue()
        assert send.call_count == 6
