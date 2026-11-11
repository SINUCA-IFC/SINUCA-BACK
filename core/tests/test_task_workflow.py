from django.urls import reverse
from rest_framework.test import APITestCase

from core.models import Category, Country, User


class TaskWorkflowTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.country = Country.objects.create(name='País A', political_name='Delegação A')
        cls.student = User.objects.create_user(email='workflow@example.test', country=cls.country)
        cls.category = Category.objects.create(name='Categoria nova')

    def test_saved_task_returns_categories_ready_for_the_board(self):
        self.client.force_authenticate(self.student)
        response = self.client.post(reverse('tarefas-list'), {
            'title': 'Estudo', 'status': 1, 'startDate': None, 'endDate': None,
            'category': [self.category.pk], 'user': [self.student.pk],
        }, format='json')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['category'], [{'id': self.category.pk, 'name': 'Categoria nova'}])
        response = self.client.patch(reverse('tarefas-detail', args=[response.data['id']]), {
            'title': 'Estudo revisado', 'status': 2,
        }, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['category'], [{'id': self.category.pk, 'name': 'Categoria nova'}])
        self.assertEqual(set(response.data['user'][0]), {'id', 'name', 'foto'})
