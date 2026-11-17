# ruff: noqa: PLR2004 -- Os números são resultados esperados dos testes.
from unittest.mock import patch

from rest_framework.test import APITestCase

from core.models import Country, Message, User


class ChatPushTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.country = Country.objects.create(name='Brasil', political_name='Brasil')
        cls.other = Country.objects.create(name='Chile', political_name='Chile')
        cls.student = User.objects.create_user(email='chat-student@example.test', country=cls.country)
        cls.peer = User.objects.create_user(email='chat-peer@example.test', country=cls.country)
        cls.foreign = User.objects.create_user(email='chat-foreign@example.test', country=cls.other)
        cls.organizer = User.objects.create_user(email='chat-org@example.test', role='organizer')
        cls.other_org = User.objects.create_user(email='chat-org2@example.test', role='organizer')
        cls.inactive = User.objects.create_user(email='chat-inactive@example.test', role='organizer', is_active=False)

    def send(self, actor):
        self.client.force_authenticate(actor)
        with self.captureOnCommitCallbacks(execute=True):
            return self.client.post(
                '/api/mensagens/',
                {'country': self.country.pk, 'text': 'Segredo'},
                format='json',
                HTTP_X_PUSH_ENDPOINT='https://push.test/origin',
            )

    @patch('core.services.notifications.send_push_event', return_value=1)
    def test_student_notifies_only_active_organizers(self, send):
        response = self.send(self.student)
        assert response.status_code == 201
        assert set(send.call_args.kwargs['user_ids']) == {self.organizer.pk, self.other_org.pk}
        payload = send.call_args.args[0]
        assert payload['event'] == 'message_created'
        assert payload['data']['url'] == f'/chat/{self.country.pk}'
        assert 'Segredo' not in payload['body']

    @patch('core.services.notifications.send_push_event', return_value=1)
    def test_organizer_notifies_only_students_in_destination_country(self, send):
        assert self.send(self.organizer).status_code == 201
        assert set(send.call_args.kwargs['user_ids']) == {self.student.pk, self.peer.pk}
        assert send.call_args.args[0]['data']['url'] == '/chat'

    @patch('core.services.notifications.send_push_event', side_effect=RuntimeError('offline'))
    def test_push_failure_does_not_lose_message(self, send):
        response = self.send(self.student)
        assert response.status_code == 201
        assert Message.objects.filter(pk=response.data['id']).exists()

    def test_cross_origin_requests_allow_push_endpoint_header(self):
        response = self.client.options(
            '/api/mensagens/',
            HTTP_ORIGIN='https://sinuca.test',
            HTTP_ACCESS_CONTROL_REQUEST_METHOD='POST',
            HTTP_ACCESS_CONTROL_REQUEST_HEADERS='authorization,x-push-endpoint',
        )
        assert 'x-push-endpoint' in response.headers['Access-Control-Allow-Headers']
