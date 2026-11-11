from rest_framework.test import APITestCase

from core.models import Country, Message, User


class MessageTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.country = Country.objects.create(name='Brasil', political_name='Delegação do Brasil')
        cls.other_country = Country.objects.create(name='Colômbia', political_name='Delegação da Colômbia')
        cls.student = User.objects.create_user(email='chat@example.test', name='Aluno', country=cls.country)
        cls.peer = User.objects.create_user(email='chat-peer@example.test', country=cls.country)
        cls.outsider = User.objects.create_user(email='chat-other@example.test', country=cls.other_country)
        cls.pending = User.objects.create_user(email='chat-pending@example.test')
        cls.evaluator = User.objects.create_user(email='chat-evaluator@example.test', role=User.Role.EVALUATOR)
        cls.organizer = User.objects.create_user(email='chat-organizer@example.test', role=User.Role.ORGANIZER)
        cls.message = Message.objects.create(country=cls.country, creator=cls.student, text='Olá, organização!')
        cls.foreign_message = Message.objects.create(
            country=cls.other_country, creator=cls.outsider, text='Mensagem de outra delegação',
        )

    def test_student_can_read_only_own_delegation_even_with_foreign_filter(self):
        self.client.force_authenticate(self.student)
        response = self.client.get(f'/api/mensagens/?country={self.other_country.pk}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual([item['id'] for item in response.data['results']], [self.message.pk])
        self.assertEqual(self.client.get(f'/api/mensagens/{self.foreign_message.pk}/').status_code, 404)

    def test_student_message_cannot_spoof_author_or_destination(self):
        self.client.force_authenticate(self.student)
        response = self.client.post('/api/mensagens/', {
            'country': self.other_country.pk, 'creator': self.organizer.pk, 'text': 'Pergunta',
        }, format='json')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['country'], self.country.pk)
        self.assertEqual(response.data['creator'], self.student.pk)
        self.assertTrue(response.data['is_mine'])
        self.assertFalse(response.data['from_organization'])

    def test_organizer_can_send_and_filter_messages_by_delegation(self):
        self.client.force_authenticate(self.organizer)
        missing = self.client.post('/api/mensagens/', {'text': 'Sem destino'}, format='json')
        self.assertEqual(missing.status_code, 400)
        response = self.client.post('/api/mensagens/', {
            'text': 'Resposta da organização', 'country': self.country.pk,
        }, format='json')
        self.assertEqual(response.status_code, 201)
        self.assertTrue(response.data['from_organization'])
        self.client.force_authenticate(self.student)
        conversation = self.client.get('/api/mensagens/').data['results']
        answer = next(message for message in conversation if message['id'] == response.data['id'])
        self.assertFalse(answer['is_mine'])
        self.assertEqual(answer['creator_name'], self.organizer.name)
        self.client.force_authenticate(self.organizer)
        filtered = self.client.get(f'/api/mensagens/?country={self.other_country.pk}')
        self.assertEqual([item['id'] for item in filtered.data['results']], [self.foreign_message.pk])

    def test_invalid_organizer_filter_returns_validation_error(self):
        self.client.force_authenticate(self.organizer)
        for value in ['invalid', '0', '-1', '1.5']:
            with self.subTest(country=value):
                self.assertEqual(self.client.get(f'/api/mensagens/?country={value}').status_code, 400)

    def test_visitors_pending_students_and_evaluators_cannot_read_or_send(self):
        for user, expected in [(None, 401), (self.pending, 403), (self.evaluator, 403)]:
            self.client.force_authenticate(user)
            with self.subTest(user=user):
                self.assertEqual(self.client.get('/api/mensagens/').status_code, expected)
                self.assertEqual(self.client.post('/api/mensagens/', {
                    'text': 'Tentativa', 'country': self.country.pk,
                }, format='json').status_code, expected)
        self.assertEqual(Message.objects.count(), 2)

    def test_empty_and_oversized_messages_are_rejected(self):
        self.client.force_authenticate(self.student)
        for text in ['', '   ', 'x' * 2001]:
            with self.subTest(length=len(text)):
                self.assertEqual(self.client.post('/api/mensagens/', {'text': text}, format='json').status_code, 400)
        self.assertEqual(Message.objects.count(), 2)

    def test_message_at_size_limit_is_accepted(self):
        self.client.force_authenticate(self.student)
        response = self.client.post('/api/mensagens/', {'text': 'á' * 2000}, format='json')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(len(response.data['text']), 2000)

    def test_conversation_pagination_has_stable_order_and_keeps_all_messages(self):
        self.client.force_authenticate(self.student)
        for index in range(11):
            Message.objects.create(country=self.country, creator=self.peer, text=f'Mensagem {index}')
        Message.objects.filter(country=self.country).update(created_at='2026-11-11T10:00:00-03:00')
        first = self.client.get('/api/mensagens/?page=1')
        second = self.client.get('/api/mensagens/?page=2')
        ids = [message['id'] for message in first.data['results'] + second.data['results']]
        self.assertEqual(len(ids), 12)
        self.assertEqual(len(set(ids)), 12)
        self.assertEqual(ids, sorted(ids, reverse=True))
