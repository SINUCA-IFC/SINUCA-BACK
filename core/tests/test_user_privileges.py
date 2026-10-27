from django.contrib.auth.models import Group
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from core.models import Country, User


class UserPrivilegeTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.country = Country.objects.create(name='País A', political_name='Delegação A')
        cls.other_country = Country.objects.create(name='País B', political_name='Delegação B')
        cls.student = User.objects.create_user(
            email='student@example.test',
            password='Profile-test-password-2026!',
            name='Aluno',
            country=cls.country,
        )
        cls.peer = User.objects.create_user(
            email='peer@example.test', name='Colega', country=cls.country,
        )
        cls.other_student = User.objects.create_user(
            email='other@example.test', name='Outro aluno', country=cls.other_country,
        )
        cls.group = Group.objects.create(name='Grupo restrito')

    def setUp(self):
        response = self.client.post(
            reverse('token_obtain_pair'),
            {'email': self.student.email, 'password': 'Profile-test-password-2026!'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['access']}")

    def protected_payload(self):
        return {
            'is_staff': True,
            'is_superuser': True,
            'is_active': False,
            'role': User.Role.ORGANIZER,
            'groups': [self.group.pk],
            'country': self.other_country.pk,
            'last_login': '2020-01-01T00:00:00Z',
        }

    def assert_student_privileges_unchanged(self, user):
        user.refresh_from_db()
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertTrue(user.is_active)
        self.assertEqual(user.role, User.Role.STUDENT)
        self.assertEqual(user.country_id, self.country.pk)
        self.assertFalse(user.groups.exists())
        self.assertIsNone(user.last_login)

    def test_patch_cannot_promote_self_or_unlock_other_delegations(self):
        response = self.client.patch(
            reverse('usuarios-detail', args=[self.student.pk]),
            self.protected_payload(),
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assert_student_privileges_unchanged(self.student)
        response = self.client.get(reverse('usuarios-detail', args=[self.other_student.pk]))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_put_cannot_promote_self(self):
        response = self.client.put(
            reverse('usuarios-detail', args=[self.student.pk]),
            {**self.protected_payload(), 'email': self.student.email, 'name': self.student.name},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assert_student_privileges_unchanged(self.student)

    def test_cannot_grant_privileges_or_deactivate_peer(self):
        response = self.client.patch(
            reverse('usuarios-detail', args=[self.peer.pk]),
            self.protected_payload(),
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assert_student_privileges_unchanged(self.peer)

    def test_user_creation_cannot_inject_privileges(self):
        response = self.client.post(
            reverse('usuarios-list'),
            {**self.protected_payload(), 'email': 'created@example.test', 'name': 'Nova conta'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        user = User.objects.get(pk=response.data['id'])
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertTrue(user.is_active)
        self.assertEqual(user.role, User.Role.STUDENT)
        self.assertIsNone(user.country_id)
        self.assertIsNone(user.last_login)
        self.assertFalse(user.groups.exists())

    def test_regular_profile_fields_remain_editable(self):
        response = self.client.patch(
            reverse('usuarios-detail', args=[self.student.pk]),
            {'name': 'Nome atualizado', 'email': 'updated@example.test'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.student.refresh_from_db()
        self.assertEqual(self.student.name, 'Nome atualizado')
        self.assertEqual(self.student.email, 'updated@example.test')
        self.assert_student_privileges_unchanged(self.student)

    def test_profile_still_returns_administrative_fields_for_reading(self):
        response = self.client.get(reverse('usuarios-me'))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIs(response.data['is_staff'], False)
        self.assertIs(response.data['is_superuser'], False)
        self.assertIs(response.data['is_active'], True)
        self.assertEqual(response.data['role'], User.Role.STUDENT)
        self.assertEqual(response.data['country']['id'], self.country.pk)

    def test_anonymous_user_cannot_update_profile(self):
        self.client.credentials()
        response = self.client.patch(
            reverse('usuarios-detail', args=[self.student.pk]),
            self.protected_payload(),
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assert_student_privileges_unchanged(self.student)

    def test_public_registration_cannot_inject_privileges(self):
        self.client.credentials()
        response = self.client.post(
            reverse('user_registration'),
            {
                **self.protected_payload(),
                'email': 'registered@example.test',
                'password': 'Registration-test-password-2026!',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        user = User.objects.get(pk=response.data['id'])
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertTrue(user.is_active)
        self.assertEqual(user.role, User.Role.STUDENT)
        self.assertFalse(user.groups.exists())
