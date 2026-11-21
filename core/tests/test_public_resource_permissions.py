from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from core.models import Category, Country, Gang, Post, User


class PublicResourcePermissionTests(APITestCase):
    resources = [
        ('postagens', Post, {'title': 'Aviso original', 'content': 'Texto original'},
         {'title': 'Aviso atualizado', 'content': 'Texto atualizado'}, 'title'),
        ('categorias', Category, {'name': 'Categoria original'}, {'name': 'Categoria atualizada'}, 'name'),
        ('turmas', Gang, {'name': '1INFO', 'courses': 'INFO'}, {'name': '2AGRO', 'courses': 'AGRO'}, 'name'),
        ('paises', Country, {'name': 'País A', 'political_name': 'Delegação A'},
         {'name': 'País B', 'political_name': 'Delegação B'}, 'name'),
    ]

    @classmethod
    def setUpTestData(cls):
        cls.student = User.objects.create_user(email='permissions-student@example.test')
        cls.evaluator = User.objects.create_user(
            email='permissions-evaluator@example.test', role=User.Role.EVALUATOR,
        )
        cls.staff = User.objects.create_user(email='permissions-staff@example.test', is_staff=True)
        cls.organizer = User.objects.create_user(
            email='permissions-organizer@example.test', role=User.Role.ORGANIZER,
        )
        cls.admin = User.objects.create_superuser(
            email='permissions-admin@example.test', password='Synthetic-admin-password-2026!',
        )

    def authenticate(self, user):
        token = RefreshToken.for_user(user).access_token
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')

    def assert_writes_denied(self, expected_status):
        for endpoint, model, original, updated, field in self.resources:
            for method in ['post', 'put', 'patch', 'delete']:
                with self.subTest(endpoint=endpoint, method=method):
                    obj = model.objects.create(**original)
                    count = model.objects.count()
                    url = reverse(f'{endpoint}-list') if method == 'post' else reverse(
                        f'{endpoint}-detail', args=[obj.pk],
                    )
                    response = getattr(self.client, method)(url, updated, format='json')

                    self.assertEqual(response.status_code, expected_status)
                    self.assertEqual(model.objects.count(), count)
                    obj.refresh_from_db()
                    self.assertEqual(getattr(obj, field), original[field])

    def assert_management_allowed(self):
        for endpoint, model, original, updated, field in self.resources:
            with self.subTest(endpoint=endpoint):
                response = self.client.post(reverse(f'{endpoint}-list'), original, format='json')
                self.assertEqual(response.status_code, status.HTTP_201_CREATED)
                obj = model.objects.get(pk=response.data['id'])
                self.assertEqual(getattr(obj, field), original[field])
                url = reverse(f'{endpoint}-detail', args=[obj.pk])

                response = self.client.put(url, updated, format='json')
                self.assertEqual(response.status_code, status.HTTP_200_OK)
                obj.refresh_from_db()
                self.assertEqual(getattr(obj, field), updated[field])

                response = self.client.patch(url, {field: original[field]}, format='json')
                self.assertEqual(response.status_code, status.HTTP_200_OK)
                obj.refresh_from_db()
                self.assertEqual(getattr(obj, field), original[field])

                response = self.client.delete(url)
                self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
                self.assertFalse(model.objects.filter(pk=obj.pk).exists())

    def test_anonymous_reading_remains_available(self):
        for endpoint, model, original, _, field in self.resources:
            obj = model.objects.create(**original)
            list_url = reverse(f'{endpoint}-list')
            detail_url = reverse(f'{endpoint}-detail', args=[obj.pk])
            with self.subTest(endpoint=endpoint):
                response = self.client.get(list_url)
                self.assertEqual(response.status_code, status.HTTP_200_OK)
                self.assertIn(obj.pk, [item['id'] for item in response.data['results']])
                response = self.client.get(detail_url)
                self.assertEqual(response.status_code, status.HTTP_200_OK)
                self.assertEqual(response.data[field], original[field])
                self.assertEqual(self.client.head(detail_url).status_code, status.HTTP_200_OK)
                self.assertEqual(self.client.options(list_url).status_code, status.HTTP_200_OK)

    def test_anonymous_writes_require_authentication(self):
        self.assert_writes_denied(status.HTTP_401_UNAUTHORIZED)

    def test_students_evaluators_and_staff_cannot_manage_event_resources(self):
        for user in [self.student, self.evaluator, self.staff]:
            with self.subTest(role=user.email):
                self.authenticate(user)
                self.assert_writes_denied(status.HTTP_403_FORBIDDEN)

    def test_organizer_can_manage_event_resources_without_a_country(self):
        self.authenticate(self.organizer)
        self.assert_management_allowed()

    def test_superuser_can_manage_event_resources_without_organizer_role(self):
        self.authenticate(self.admin)
        self.assert_management_allowed()
