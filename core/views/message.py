from rest_framework import mixins, viewsets

from core.models import Message
from core.permissions import IsStudentOrOrganizer
from core.serializers import MessageSerializer


class MessageViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = MessageSerializer
    permission_classes = [IsStudentOrOrganizer]

    def get_queryset(self):
        user = self.request.user
        qs = Message.objects.select_related('creator')

        if user.is_organizer:
            delegation = self.request.query_params.get('delegation')
            return qs.filter(delegation_id=delegation) if delegation else qs

        return qs.filter(delegation_id=user.country_id)

    def perform_create(self, serializer):
        user = self.request.user
        if user.is_organizer:
            serializer.save(creator=user)  # delegation vem do body
        else:
            serializer.save(creator=user, delegation_id=user.country_id)