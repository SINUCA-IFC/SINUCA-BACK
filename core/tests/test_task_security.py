from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from core.models import Category, Country, Task, User
from uploader.models import Image


class TaskSecurityTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.country = Country.objects.create(name='País A', political_name='Delegação A')
        cls.other_country = Country.objects.create(name='País B', political_name='Delegação B')
        cls.category = Category.objects.create(name='Estudo')
        cls.photo = Image.objects.create(file='images/synthetic.png', description='Foto sintética')
        cls.student = User.objects.create_user(
            email='task-student@example.test', password='Synthetic-task-password-2026!',
            name='Aluno', country=cls.country, foto=cls.photo,
        )
        cls.peer = User.objects.create_user(
            email='task-peer@example.test', name='Colega', country=cls.country,
        )
        cls.outsider = User.objects.create_user(
            email='task-outsider@example.test', country=cls.other_country,
        )
        cls.unassigned = User.objects.create_user(email='task-unassigned@example.test')
        cls.admin = User.objects.create_superuser(
            email='task-admin@example.test', password='Synthetic-admin-password-2026!',
        )
        cls.organizer = User.objects.create_user(
            email='task-organizer@example.test', country=cls.country, role=User.Role.ORGANIZER,
        )
        cls.task = Task.objects.create(title='Tarefa original', status=1, creator=cls.student)
        cls.task.user.add(cls.peer)

    def setUp(self):
        self.authenticate(self.student)

    def authenticate(self, user):
        token = RefreshToken.for_user(user).access_token
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')

    def test_task_creator_returns_only_public_summary_fields(self):
        response = self.client.get(reverse('tarefas-detail', args=[self.task.pk]))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        creator = response.data['creator']
        self.assertEqual(set(creator), {'id', 'name', 'foto'})
        self.assertEqual(creator['id'], self.student.pk)
        self.assertEqual(creator['name'], 'Aluno')
        self.assertTrue(creator['foto']['url'].endswith('/media/images/synthetic.png'))

    def test_task_assignees_do_not_expose_authentication_fields_even_for_legacy_assignments(self):
        self.task.user.add(self.admin)

        response = self.client.get(reverse('tarefas-detail', args=[self.task.pk]))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        people = response.data['user']
        self.assertEqual({person['id'] for person in people}, {self.peer.pk, self.admin.pk})
        for person in people:
            with self.subTest(user=person['id']):
                self.assertEqual(set(person), {'id', 'name', 'foto'})

    def test_student_can_create_task_for_own_delegation(self):
        response = self.client.post(
            reverse('tarefas-list'),
            {
                'title': 'Nova tarefa', 'status': 1, 'category': [self.category.pk],
                'user': [self.student.pk, self.peer.pk],
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        task = Task.objects.get(pk=response.data['id'])
        self.assertEqual(task.creator_id, self.student.pk)
        self.assertEqual(set(task.user.values_list('pk', flat=True)), {self.student.pk, self.peer.pk})

    def test_creation_cannot_assign_foreign_unassigned_or_admin_accounts(self):
        for assignee in [self.outsider, self.unassigned, self.admin]:
            with self.subTest(user=assignee.pk):
                response = self.client.post(
                    reverse('tarefas-list'),
                    {
                        'title': 'Tentativa indevida', 'status': 1, 'category': [self.category.pk],
                        'user': [assignee.pk],
                    },
                    format='json',
                )
                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
                self.assertIn('user', response.data)
                self.assertEqual(Task.objects.count(), 1)

    def test_put_and_patch_allow_responsible_users_from_own_delegation(self):
        for method, assignee in [('put', self.student), ('patch', self.peer)]:
            with self.subTest(method=method):
                response = getattr(self.client, method)(
                    reverse('tarefas-detail', args=[self.task.pk]),
                    {
                        'title': 'Tarefa atualizada', 'status': 2, 'category': [self.category.pk],
                        'user': [assignee.pk],
                    },
                    format='json',
                )

                self.assertEqual(response.status_code, status.HTTP_200_OK)
                self.task.refresh_from_db()
                self.assertEqual(self.task.title, 'Tarefa atualizada')
                self.assertEqual(list(self.task.user.values_list('pk', flat=True)), [assignee.pk])

    def test_patch_rejects_cross_country_assignment_without_partial_changes(self):
        response = self.client.patch(
            reverse('tarefas-detail', args=[self.task.pk]),
            {'title': 'Alteração indevida', 'user': [self.peer.pk, self.outsider.pk]},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('user', response.data)
        self.task.refresh_from_db()
        self.assertEqual(self.task.title, 'Tarefa original')
        self.assertEqual(list(self.task.user.values_list('pk', flat=True)), [self.peer.pk])

    def test_put_rejects_cross_country_assignment(self):
        response = self.client.put(
            reverse('tarefas-detail', args=[self.task.pk]),
            {
                'title': 'Alteração indevida', 'status': 2, 'category': [self.category.pk],
                'user': [self.outsider.pk],
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('user', response.data)
        self.task.refresh_from_db()
        self.assertEqual(self.task.title, 'Tarefa original')
        self.assertEqual(self.task.status, 1)
        self.assertEqual(list(self.task.user.values_list('pk', flat=True)), [self.peer.pk])

    def test_user_without_country_cannot_assign_other_unassigned_users(self):
        self.authenticate(self.unassigned)
        response = self.client.post(
            reverse('tarefas-list'),
            {'title': 'Sem delegação', 'status': 1, 'category': [self.category.pk], 'user': [self.admin.pk]},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Task.objects.count(), 1)

    def test_organizer_without_global_privileges_cannot_assign_another_country(self):
        self.authenticate(self.organizer)
        response = self.client.post(
            reverse('tarefas-list'),
            {'title': 'Outra delegação', 'status': 1, 'category': [self.category.pk], 'user': [self.outsider.pk]},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Task.objects.count(), 1)

    def test_superuser_retains_global_assignment_without_exposing_credentials(self):
        self.authenticate(self.admin)
        response = self.client.post(
            reverse('tarefas-list'),
            {'title': 'Tarefa administrativa', 'status': 1, 'category': [self.category.pk], 'user': [self.outsider.pk]},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        task = Task.objects.get(pk=response.data['id'])
        self.assertEqual(list(task.user.values_list('pk', flat=True)), [self.outsider.pk])
        response = self.client.get(reverse('tarefas-detail', args=[task.pk]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(set(response.data['creator']), {'id', 'name', 'foto'})
        self.assertEqual(set(response.data['user'][0]), {'id', 'name', 'foto'})

    def test_superuser_can_update_assignments_across_delegations(self):
        self.authenticate(self.admin)
        for method, assignee in [('put', self.outsider), ('patch', self.unassigned)]:
            with self.subTest(method=method):
                response = getattr(self.client, method)(
                    reverse('tarefas-detail', args=[self.task.pk]),
                    {
                        'title': 'Tarefa administrativa', 'status': 1, 'category': [self.category.pk],
                        'user': [assignee.pk],
                    },
                    format='json',
                )

                self.assertEqual(response.status_code, status.HTTP_200_OK)
                self.assertEqual(list(self.task.user.values_list('pk', flat=True)), [assignee.pk])
