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
        queryset = Message.objects.select_related('creator')

        if user.is_organizer:
            country = self.request.query_params.get('country')
            return queryset.filter(country_id=country) if country else queryset

        return queryset.filter(country_id=user.country_id)

    def perform_create(self, serializer):
        user = self.request.user
        if user.is_organizer:
            serializer.save(creator=user)
        else:
            serializer.save(creator=user, country_id=user.country_id)