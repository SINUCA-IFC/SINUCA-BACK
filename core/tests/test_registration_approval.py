from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from core.models import Category, Country, Gang, Link, Message, Schedule, Task, User


class RegistrationApprovalTests(APITestCase):
    password = 'Synthetic-registration-password-2026!'

    @classmethod
    def setUpTestData(cls):
        cls.country = Country.objects.create(name='País A', political_name='Delegação A')
        cls.other_country = Country.objects.create(name='País B', political_name='Delegação B')
        cls.category = Category.objects.create(name='Estudo')
        cls.gang = Gang.objects.create(name='1INFO', courses='INFO')
        cls.student = User.objects.create_user(
            email='approved@example.test', country=cls.country, name='Aluno aprovado',
        )
        cls.other_student = User.objects.create_user(email='foreign@example.test', country=cls.other_country)
        cls.pending = User.objects.create_user(
            email='pending@example.test', password=cls.password, name='Aluno pendente',
            gang=cls.gang, matriculation='1234567890',
        )
        cls.organizer = User.objects.create_user(email='organizer@example.test', role=User.Role.ORGANIZER)
        cls.evaluator = User.objects.create_user(email='evaluator@example.test', role=User.Role.EVALUATOR)
        cls.staff = User.objects.create_user(email='staff@example.test', is_staff=True)
        cls.admin = User.objects.create_superuser(email='admin@example.test', password=cls.password)
        cls.task = Task.objects.create(title='Tarefa privada', status=1, creator=cls.student)
        cls.foreign_task = Task.objects.create(title='Outra tarefa', status=1, creator=cls.other_student)
        cls.link = Link.objects.create(name='Documento privado', url='https://example.test/private')
        cls.link.country.add(cls.country)
        cls.schedule = Schedule.objects.create(
            title='Cronograma privado', category=1, description='Descrição',
            startDate='2026-11-03T10:00:00-03:00', endDate='2026-11-03T11:00:00-03:00',
        )
        cls.schedule.country.add(cls.country)
        cls.message = Message.objects.create(country=cls.country, creator=cls.student, text='Mensagem privada')

    def authenticate(self, user):
        token = RefreshToken.for_user(user).access_token
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')

    def approval_url(self, user=None):
        return f'/api/usuarios/{(user or self.pending).pk}/aprovar/'

    def test_public_registration_always_creates_pending_student(self):
        for country in [self.country.pk, 999999, None]:
            with self.subTest(country=country):
                response = self.client.post(
                    reverse('user_registration'),
                    {
                        'email': f'registered-{country}@example.test', 'name': 'Aluno novo',
                        'password': self.password, 'country': country, 'role': User.Role.ORGANIZER,
                        'is_superuser': True, 'approval_pending': False,
                    },
                    format='json',
                )
                self.assertEqual(response.status_code, status.HTTP_201_CREATED)
                user = User.objects.get(pk=response.data['id'])
                self.assertIsNone(user.country_id)
                self.assertEqual(user.role, User.Role.STUDENT)
                self.assertFalse(user.is_superuser)
                self.assertTrue(user.is_active)
                self.assertIs(response.data.get('approval_pending'), True)

    def test_pending_student_can_log_in_and_read_own_status(self):
        response = self.client.post(
            reverse('token_obtain_pair'),
            {'email': self.pending.email, 'password': self.password}, format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['access']}")

        response = self.client.get(reverse('usuarios-me'))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNone(response.data['country'])
        self.assertIs(response.data.get('approval_pending'), True)

    def test_pending_student_cannot_read_delegation_data(self):
        self.authenticate(self.pending)
        for endpoint in ['tarefas', 'cronogramas', 'docs', 'usuarios']:
            with self.subTest(endpoint=endpoint):
                response = self.client.get(reverse(f'{endpoint}-list'))
                self.assertEqual(response.status_code, status.HTTP_200_OK)
                self.assertEqual(response.data['results'], [])
        for endpoint, obj in [('tarefas', self.task), ('cronogramas', self.schedule), ('docs', self.link)]:
            with self.subTest(endpoint=endpoint):
                response = self.client.get(reverse(f'{endpoint}-detail', args=[obj.pk]))
                self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(self.client.get(reverse('mensagens-list')).status_code, status.HTTP_403_FORBIDDEN)

    def test_pending_student_cannot_create_or_modify_private_resources(self):
        self.authenticate(self.pending)
        resources = [
            ('tarefas', self.task, {'title': 'Tentativa', 'status': 1, 'category': [self.category.pk], 'user': []}),
            ('cronogramas', self.schedule, {
                'title': 'Tentativa', 'category': 1, 'description': 'Tentativa',
                'startDate': '2026-11-03T12:00:00-03:00', 'endDate': '2026-11-03T13:00:00-03:00',
                'country': [self.country.pk],
            }),
            ('docs', self.link, {'name': 'Tentativa', 'url': 'https://example.test/injected'}),
            ('usuarios', self.student, {'name': 'Tentativa', 'email': 'injected@example.test'}),
        ]
        for endpoint, obj, payload in resources:
            for method in ['post', 'put', 'patch', 'delete']:
                with self.subTest(endpoint=endpoint, method=method):
                    url = reverse(f'{endpoint}-list') if method == 'post' else reverse(
                        f'{endpoint}-detail', args=[obj.pk],
                    )
                    response = getattr(self.client, method)(url, payload, format='json')
                    self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(Task.objects.count(), 2)
        self.assertEqual(Link.objects.count(), 1)
        self.assertEqual(Schedule.objects.count(), 1)
        self.assertFalse(User.objects.filter(email='injected@example.test').exists())
        self.task.refresh_from_db()
        self.assertEqual(self.task.title, 'Tarefa privada')

    def test_only_organizers_and_superusers_can_list_pending_students(self):
        self.assertEqual(self.client.get('/api/usuarios/pendentes/').status_code, status.HTTP_401_UNAUTHORIZED)
        for user in [self.pending, self.student, self.evaluator, self.staff]:
            with self.subTest(user=user.pk):
                self.authenticate(user)
                self.assertEqual(self.client.get('/api/usuarios/pendentes/').status_code, status.HTTP_403_FORBIDDEN)
        for user in [self.organizer, self.admin]:
            with self.subTest(user=user.pk):
                self.authenticate(user)
                response = self.client.get('/api/usuarios/pendentes/')
                self.assertEqual(response.status_code, status.HTTP_200_OK)
                ids = {item['id'] for item in response.data['results']}
                self.assertIn(self.pending.pk, ids)
                self.assertNotIn(self.organizer.pk, ids)
                self.assertNotIn(self.evaluator.pk, ids)
                self.assertNotIn(self.admin.pk, ids)
                self.assertNotIn(self.student.pk, ids)

    def test_student_cannot_approve_self_or_another_student(self):
        self.authenticate(self.pending)
        response = self.client.post(self.approval_url(), {'country': self.country.pk}, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.authenticate(self.student)
        response = self.client.post(self.approval_url(), {'country': self.country.pk}, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.pending.refresh_from_db()
        self.assertIsNone(self.pending.country_id)

    def test_organization_can_identify_pending_student_by_school_data(self):
        self.authenticate(self.organizer)
        response = self.client.get('/api/usuarios/pendentes/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        pending = next(item for item in response.data['results'] if item['id'] == self.pending.pk)
        self.assertEqual(pending.get('matriculation'), '1234567890')
        self.assertEqual(pending['gang']['id'], self.gang.pk)
        self.assertNotIn('password', pending)

    def test_disabled_student_is_not_approved_or_listed(self):
        self.pending.is_active = False
        self.pending.save(update_fields=['is_active'])
        self.authenticate(self.organizer)

        response = self.client.get('/api/usuarios/pendentes/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotIn(self.pending.pk, [item['id'] for item in response.data['results']])
        response = self.client.post(self.approval_url(), {'country': self.country.pk}, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.pending.refresh_from_db()
        self.assertFalse(self.pending.is_active)
        self.assertIsNone(self.pending.country_id)

    def test_anonymous_evaluator_and_staff_cannot_approve(self):
        response = self.client.post(self.approval_url(), {'country': self.country.pk}, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        for user in [self.evaluator, self.staff]:
            with self.subTest(user=user.pk):
                self.authenticate(user)
                response = self.client.post(self.approval_url(), {'country': self.country.pk}, format='json')
                self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.pending.refresh_from_db()
        self.assertIsNone(self.pending.country_id)

    def test_organizer_approval_requires_valid_country(self):
        self.authenticate(self.organizer)
        for payload in [{}, {'country': None}, {'country': 999999}]:
            with self.subTest(payload=payload):
                response = self.client.post(self.approval_url(), payload, format='json')
                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
                self.assertIn('country', response.data)
                self.pending.refresh_from_db()
                self.assertIsNone(self.pending.country_id)

    def test_organizer_approves_without_granting_extra_privileges(self):
        self.authenticate(self.organizer)
        response = self.client.post(
            self.approval_url(),
            {'country': self.country.pk, 'role': User.Role.ORGANIZER, 'is_superuser': True}, format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIs(response.data['approval_pending'], False)
        self.assertEqual(response.data['country']['id'], self.country.pk)
        self.pending.refresh_from_db()
        self.assertEqual(self.pending.country_id, self.country.pk)
        self.assertEqual(self.pending.role, User.Role.STUDENT)
        self.assertFalse(self.pending.is_superuser)

    def test_superuser_can_approve_pending_student(self):
        self.authenticate(self.admin)
        response = self.client.post(self.approval_url(), {'country': self.country.pk}, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.pending.refresh_from_db()
        self.assertEqual(self.pending.country_id, self.country.pk)

    def test_approval_cannot_reassign_existing_delegation_or_modify_other_roles(self):
        self.authenticate(self.organizer)
        for target in [self.student, self.organizer, self.evaluator, self.admin]:
            with self.subTest(user=target.pk):
                previous_country = target.country_id
                response = self.client.post(self.approval_url(target), {'country': self.other_country.pk}, format='json')
                self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
                target.refresh_from_db()
                self.assertEqual(target.country_id, previous_country)

    def test_approval_takes_effect_for_already_issued_token(self):
        pending_token = str(RefreshToken.for_user(self.pending).access_token)
        self.authenticate(self.organizer)
        response = self.client.post(self.approval_url(), {'country': self.country.pk}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {pending_token}')

        response = self.client.get(reverse('usuarios-me'))
        self.assertIs(response.data['approval_pending'], False)
        self.assertEqual(response.data['country']['id'], self.country.pk)
        response = self.client.get(reverse('tarefas-list'))
        self.assertEqual([item['id'] for item in response.data['results']], [self.task.pk])
        self.assertEqual(
            self.client.get(reverse('tarefas-detail', args=[self.foreign_task.pk])).status_code,
            status.HTTP_404_NOT_FOUND,
        )
        response = self.client.get(reverse('mensagens-list'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual([item['id'] for item in response.data['results']], [self.message.pk])
