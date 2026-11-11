import warnings

from django.core.paginator import UnorderedObjectListWarning
from rest_framework.test import APITestCase

from core.models import Category, Country, Gang, Link, Post, Schedule, Task, User


class PaginationTests(APITestCase):
    def test_lists_are_ordered_and_cover_all_pages_without_duplicates(self):
        country = Country.objects.create(name='País', political_name='Delegação')
        actor = User.objects.create_user(email='pagination@example.test', country=country)
        self.client.force_authenticate(actor)
        for i in range(12):
            Category.objects.create(name=f'Categoria {i}')
            Country.objects.create(name=f'País {i}', political_name=f'Delegação {i}')
            Gang.objects.create(name=f'Turma {i}', courses='INFO')
            Post.objects.create(title=f'Aviso {i}', content='Texto')
            User.objects.create_user(email=f'pagination-{i}@example.test', country=country)
            Task.objects.create(title=f'Tarefa {i}', status=1, creator=actor)
            link = Link.objects.create(url=f'https://example.test/{i}')
            link.country.add(country)
            schedule = Schedule.objects.create(
                title=f'Atividade {i}', category=1, description='Descrição',
                startDate='2026-11-11T10:00:00-03:00', endDate='2026-11-11T11:00:00-03:00',
            )
            schedule.country.add(country)
        for endpoint, count in [
            ('categorias', 12), ('paises', 13), ('turmas', 12), ('postagens', 12),
            ('usuarios', 13), ('tarefas', 12), ('docs', 12), ('cronogramas', 12),
        ]:
            with self.subTest(endpoint=endpoint), warnings.catch_warnings():
                warnings.simplefilter('error', UnorderedObjectListWarning)
                first = self.client.get(f'/api/{endpoint}/?page=1')
                second = self.client.get(f'/api/{endpoint}/?page=2')
                self.assertEqual(first.status_code, 200)
                self.assertEqual(second.status_code, 200)
                ids = [item['id'] for item in first.data['results'] + second.data['results']]
                self.assertEqual(len(ids), count)
                self.assertEqual(len(set(ids)), count)
                self.assertEqual(ids, sorted(ids))
