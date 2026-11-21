from rest_framework.test import APITestCase

from core.models import Country, Message, User


class MessageReadTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.country = Country.objects.create(name='Brasil', political_name='República do Brasil')
        cls.other_country = Country.objects.create(name='Colômbia', political_name='República da Colômbia')
        cls.student = User.objects.create_user(email='read-student@example.test', country=cls.country)
        cls.peer = User.objects.create_user(email='read-peer@example.test', country=cls.country)
        cls.organizer = User.objects.create_user(email='read-organizer@example.test', role=User.Role.ORGANIZER)
        cls.other_organizer = User.objects.create_user(email='read-organizer2@example.test', role=User.Role.ORGANIZER)
        cls.pending = User.objects.create_user(email='read-pending@example.test')
        cls.evaluator = User.objects.create_user(email='read-evaluator@example.test', role=User.Role.EVALUATOR)
        cls.received = Message.objects.create(country=cls.country, creator=cls.student, text='Uma dúvida')
        cls.answer = Message.objects.create(country=cls.country, creator=cls.organizer, text='Uma resposta')
        cls.foreign = Message.objects.create(country=cls.other_country, creator=cls.other_organizer, text='Outro país')

    def conversations(self):
        response = self.client.get('/api/mensagens/conversas/')
        self.assertEqual(response.status_code, 200)
        return {item['id']: item for item in response.data['results']}

    def mark_read(self, country, message):
        return self.client.post('/api/mensagens/lidas/', {
            'country': country.pk, 'last_message_id': message.pk,
        }, format='json')

    def test_unread_counts_exclude_own_messages_and_get_does_not_mark_read(self):
        self.client.force_authenticate(self.organizer)
        for _ in range(2):
            conversations = self.conversations()
            self.assertEqual(conversations[self.country.pk]['unread_count'], 1)
            self.assertEqual(conversations[self.other_country.pk]['unread_count'], 1)
            self.assertIsNotNone(conversations[self.country.pk]['last_message_at'])
        self.client.force_authenticate(self.student)
        self.assertEqual(list(self.conversations()), [self.country.pk])
        self.assertEqual(self.conversations()[self.country.pk]['unread_count'], 1)

    def test_read_is_saved_per_user_and_persists_across_requests(self):
        self.client.force_authenticate(self.organizer)
        self.assertEqual(self.mark_read(self.country, self.answer).status_code, 200)
        self.assertEqual(self.conversations()[self.country.pk]['unread_count'], 0)
        self.client.force_authenticate(self.other_organizer)
        self.assertEqual(self.conversations()[self.country.pk]['unread_count'], 2)
        self.client.force_authenticate(self.organizer)
        self.assertEqual(self.conversations()[self.country.pk]['unread_count'], 0)

    def test_receipt_does_not_read_message_arriving_after_loaded_history(self):
        self.client.force_authenticate(self.organizer)
        new = Message.objects.create(country=self.country, creator=self.peer, text='Chegou depois da consulta')
        self.assertEqual(self.mark_read(self.country, self.answer).status_code, 200)
        self.assertEqual(self.conversations()[self.country.pk]['unread_count'], 1)
        self.assertEqual(self.mark_read(self.country, new).status_code, 200)
        self.assertEqual(self.conversations()[self.country.pk]['unread_count'], 0)

    def test_old_or_repeated_receipt_does_not_move_read_position_backwards(self):
        self.client.force_authenticate(self.organizer)
        latest = Message.objects.create(country=self.country, creator=self.peer, text='Mensagem recente')
        for message in [latest, self.received, latest, self.answer]:
            self.assertEqual(self.mark_read(self.country, message).status_code, 200)
            self.assertEqual(self.conversations()[self.country.pk]['unread_count'], 0)

    def test_manual_unread_restores_latest_received_message_only_for_requester(self):
        self.client.force_authenticate(self.organizer)
        self.mark_read(self.country, self.answer)
        response = self.client.post('/api/mensagens/nao-lidas/', {'country': self.country.pk}, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.conversations()[self.country.pk]['unread_count'], 1)
        self.client.force_authenticate(self.other_organizer)
        self.assertEqual(self.conversations()[self.country.pk]['unread_count'], 2)
        self.client.force_authenticate(self.student)
        self.mark_read(self.country, self.answer)
        self.assertEqual(self.client.post('/api/mensagens/nao-lidas/', {
            'country': self.country.pk,
        }, format='json').status_code, 200)
        self.assertEqual(self.conversations()[self.country.pk]['unread_count'], 1)

    def test_manual_unread_requires_a_received_message(self):
        self.client.force_authenticate(self.other_organizer)
        response = self.client.post('/api/mensagens/nao-lidas/', {
            'country': self.other_country.pk,
        }, format='json')
        self.assertEqual(response.status_code, 400)

    def test_manual_unread_does_not_erase_other_unread_messages(self):
        self.client.force_authenticate(self.organizer)
        Message.objects.create(country=self.country, creator=self.peer, text='Outra mensagem não lida')
        self.assertEqual(self.conversations()[self.country.pk]['unread_count'], 2)
        response = self.client.post('/api/mensagens/nao-lidas/', {'country': self.country.pk}, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.conversations()[self.country.pk]['unread_count'], 2)

    def test_students_cannot_change_read_state_of_another_delegation(self):
        self.client.force_authenticate(self.student)
        self.assertEqual(self.mark_read(self.other_country, self.foreign).status_code, 404)
        self.assertEqual(self.client.post('/api/mensagens/nao-lidas/', {
            'country': self.other_country.pk,
        }, format='json').status_code, 404)
        self.assertEqual(list(self.conversations()), [self.country.pk])

    def test_invalid_receipts_cannot_read_arbitrary_messages(self):
        self.client.force_authenticate(self.organizer)
        for payload in [
            {}, {'country': self.country.pk},
            {'country': self.country.pk, 'last_message_id': 0},
            {'country': self.country.pk, 'last_message_id': -1},
            {'country': self.country.pk, 'last_message_id': 'invalid'},
            {'country': 999999, 'last_message_id': self.answer.pk},
        ]:
            with self.subTest(payload=payload):
                self.assertEqual(self.client.post('/api/mensagens/lidas/', payload, format='json').status_code, 400)
        self.assertEqual(self.mark_read(self.country, self.foreign).status_code, 404)
        self.assertEqual(self.conversations()[self.country.pk]['unread_count'], 1)

    def test_new_actions_require_the_same_chat_permissions(self):
        for user, expected in [(None, 401), (self.pending, 403), (self.evaluator, 403)]:
            self.client.force_authenticate(user)
            with self.subTest(user=user):
                self.assertEqual(self.client.get('/api/mensagens/conversas/').status_code, expected)
                self.assertEqual(self.mark_read(self.country, self.answer).status_code, expected)
                self.assertEqual(self.client.post('/api/mensagens/nao-lidas/', {
                    'country': self.country.pk,
                }, format='json').status_code, expected)

    def test_unread_conversations_come_first_then_latest_activity_not_unread_quantity(self):
        self.client.force_authenticate(self.organizer)
        # Brasil: duas não lidas antigas. Colômbia: uma não lida mais recente.
        Message.objects.create(country=self.country, creator=self.peer, text='Mais uma dúvida')
        Message.objects.filter(country=self.country).update(created_at='2026-11-10T10:00:00Z')
        Message.objects.filter(country=self.other_country).update(created_at='2026-11-11T10:00:00Z')
        read_country = Country.objects.create(name='Conversa lida', political_name='País de teste')
        read_message = Message.objects.create(country=read_country, creator=self.peer, text='Conversa mais recente')
        self.mark_read(read_country, read_message)
        empty_country = Country.objects.create(name='Sem conversa', political_name='País de teste')
        response = self.client.get('/api/mensagens/conversas/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual([item['id'] for item in response.data['results']], [
            self.other_country.pk, self.country.pk, read_country.pk, empty_country.pk,
        ])
        self.assertIsNone(response.data['results'][-1]['last_message_at'])

    def test_conversations_are_sorted_before_pagination(self):
        self.client.force_authenticate(self.organizer)
        for number in range(11):
            Country.objects.create(name=f'País {number}', political_name='País de teste')
        response = self.client.get('/api/mensagens/conversas/?page=1')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['total_pages'], 2)
        first_ids = [item['id'] for item in response.data['results']]
        second = self.client.get('/api/mensagens/conversas/?page=2')
        ids = first_ids + [item['id'] for item in second.data['results']]
        self.assertEqual(len(ids), 13)
        self.assertEqual(len(set(ids)), 13)
        self.assertIn(self.country.pk, first_ids[:2])
        self.assertIn(self.other_country.pk, first_ids[:2])

    def test_sending_own_message_does_not_implicitly_read_received_messages(self):
        self.client.force_authenticate(self.organizer)
        response = self.client.post('/api/mensagens/', {
            'country': self.country.pk, 'text': 'Resposta rápida',
        }, format='json')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(self.conversations()[self.country.pk]['unread_count'], 1)
