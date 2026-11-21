from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from core.models import Country, Link, Schedule, User


class ResourcePermissionTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.country = Country.objects.create(name='País A', political_name='Delegação A')
        cls.other_country = Country.objects.create(name='País B', political_name='Delegação B')
        cls.student = User.objects.create_user(email='student@example.test', country=cls.country)
        cls.peer = User.objects.create_user(email='peer@example.test', country=cls.country)
        cls.foreign = User.objects.create_user(email='foreign@example.test', country=cls.other_country)
        cls.evaluator = User.objects.create_user(
            email='evaluator@example.test', role=User.Role.EVALUATOR, country=cls.country,
        )
        cls.staff = User.objects.create_user(email='staff@example.test', country=cls.country, is_staff=True)
        cls.organizer = User.objects.create_user(email='organizer@example.test', role=User.Role.ORGANIZER)
        cls.admin = User.objects.create_superuser(email='admin@example.test', password='Synthetic-password-2026!')
        cls.link = Link.objects.create(name='Documento compartilhado', url='https://example.test/document')
        cls.link.country.set([cls.country, cls.other_country])
        cls.schedule = Schedule.objects.create(
            title='Atividade compartilhada', description='Descrição', category=1,
            startDate='2026-11-03T10:00:00-03:00', endDate='2026-11-03T11:00:00-03:00',
        )
        cls.schedule.country.set([cls.country, cls.other_country])
        cls.schedule.docs.add(cls.link)

    def test_participants_cannot_change_or_delete_peers(self):
        for actor in [self.student, self.evaluator, self.staff]:
            self.client.force_authenticate(actor)
            for method in ['put', 'patch', 'delete']:
                with self.subTest(actor=actor.pk, method=method):
                    response = getattr(self.client, method)(
                        reverse('usuarios-detail', args=[self.peer.pk]),
                        {'email': 'hijacked@example.test', 'name': 'Alterado'}, format='json',
                    )
                    self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.peer.refresh_from_db()
        self.assertEqual(self.peer.email, 'peer@example.test')

    def test_student_can_edit_self_but_cannot_create_or_delete_accounts(self):
        self.client.force_authenticate(self.student)
        response = self.client.patch(
            reverse('usuarios-detail', args=[self.student.pk]), {'name': 'Meu nome'}, format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.student.refresh_from_db()
        self.assertEqual(self.student.name, 'Meu nome')
        response = self.client.post(
            reverse('usuarios-list'), {'email': 'extra@example.test'}, format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        response = self.client.delete(reverse('usuarios-detail', args=[self.student.pk]))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertFalse(User.objects.filter(email='extra@example.test').exists())
        self.assertTrue(User.objects.filter(pk=self.student.pk).exists())

    def test_participants_can_read_only_their_delegation(self):
        self.client.force_authenticate(self.student)
        response = self.client.get(reverse('usuarios-list'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn(self.peer.pk, [item['id'] for item in response.data['results']])
        self.assertNotIn(self.foreign.pk, [item['id'] for item in response.data['results']])
        self.assertEqual(
            self.client.get(reverse('usuarios-detail', args=[self.foreign.pk])).status_code,
            status.HTTP_404_NOT_FOUND,
        )
        for endpoint, obj in [('cronogramas', self.schedule), ('docs', self.link)]:
            self.assertEqual(
                self.client.get(reverse(f'{endpoint}-detail', args=[obj.pk])).status_code,
                status.HTTP_200_OK,
            )

    def test_only_organization_can_write_shared_resources(self):
        resources = [
            ('cronogramas', self.schedule, {
                'title': 'Alterado', 'description': 'Descrição', 'category': 1,
                'startDate': '2026-11-03T10:00:00-03:00', 'endDate': '2026-11-03T11:00:00-03:00',
                'country': [self.other_country.pk],
            }),
            ('docs', self.link, {'url': 'https://example.test/injected', 'country': [self.other_country.pk]}),
        ]
        for actor in [self.student, self.evaluator, self.staff]:
            self.client.force_authenticate(actor)
            for endpoint, obj, payload in resources:
                for method in ['post', 'put', 'patch', 'delete']:
                    with self.subTest(actor=actor.pk, endpoint=endpoint, method=method):
                        url = reverse(f'{endpoint}-list') if method == 'post' else reverse(
                            f'{endpoint}-detail', args=[obj.pk],
                        )
                        response = getattr(self.client, method)(url, payload, format='json')
                        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.schedule.refresh_from_db()
        self.link.refresh_from_db()
        self.assertEqual(self.schedule.title, 'Atividade compartilhada')
        self.assertEqual(self.link.url, 'https://example.test/document')
        self.assertEqual(set(self.schedule.country.values_list('id', flat=True)), {
            self.country.pk, self.other_country.pk,
        })

    def test_organizer_without_country_and_superuser_can_manage_resources(self):
        for actor in [self.organizer, self.admin]:
            self.client.force_authenticate(actor)
            with self.subTest(actor=actor.pk):
                response = self.client.patch(
                    reverse('usuarios-detail', args=[self.foreign.pk]), {'name': 'Nome corrigido'}, format='json',
                )
                self.assertEqual(response.status_code, status.HTTP_200_OK)
                response = self.client.patch(
                    reverse('cronogramas-detail', args=[self.schedule.pk]), {'title': 'Revisado'}, format='json',
                )
                self.assertEqual(response.status_code, status.HTTP_200_OK)
                response = self.client.post(
                    reverse('docs-list'),
                    {'url': 'https://example.test/new', 'country': [self.other_country.pk]}, format='json',
                )
                self.assertEqual(response.status_code, status.HTTP_201_CREATED)
                link = Link.objects.get(pk=response.data['id'])
                self.assertEqual(list(link.country.values_list('id', flat=True)), [self.other_country.pk])
                self.assertEqual(
                    self.client.delete(reverse('docs-detail', args=[link.pk])).status_code,
                    status.HTTP_204_NO_CONTENT,
                )

    def test_schedule_cannot_expose_document_to_another_delegation(self):
        foreign_link = Link.objects.create(url='https://example.test/foreign')
        foreign_link.country.add(self.other_country)
        self.client.force_authenticate(self.organizer)
        response = self.client.patch(
            reverse('cronogramas-detail', args=[self.schedule.pk]),
            {'docs': [foreign_link.pk]}, format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(list(self.schedule.docs.values_list('id', flat=True)), [self.link.pk])

    def test_link_cannot_drop_delegation_still_using_it(self):
        self.client.force_authenticate(self.organizer)
        response = self.client.patch(
            reverse('docs-detail', args=[self.link.pk]), {'country': [self.country.pk]}, format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.link.country.count(), 2)

    def test_organizer_cannot_change_or_delete_privileged_accounts(self):
        self.client.force_authenticate(self.organizer)
        another_organizer = User.objects.create_user(email='other-org@example.test', role=User.Role.ORGANIZER)
        for target in [self.admin, self.staff, another_organizer]:
            for method in ['patch', 'delete']:
                with self.subTest(target=target.pk, method=method):
                    response = getattr(self.client, method)(
                        reverse('usuarios-detail', args=[target.pk]), {'email': 'hijacked@example.test'}, format='json',
                    )
                    self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.admin.refresh_from_db()
        self.assertEqual(self.admin.email, 'admin@example.test')

    def test_shared_document_remains_usable_when_all_countries_have_access(self):
        self.client.force_authenticate(self.organizer)
        response = self.client.patch(
            reverse('cronogramas-detail', args=[self.schedule.pk]), {'docs': [self.link.pk]}, format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
