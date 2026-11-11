from django.db.models import (
    BigIntegerField, BooleanField, Case, Count, F, Max, OuterRef, Q, Subquery, Value, When,
)
from django.db.models.functions import Coalesce
from django.shortcuts import get_object_or_404
from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.response import Response

from core.models import Country, Message, MessageRead
from core.permissions import IsStudentOrOrganizer
from core.serializers import MessageSerializer
from core.serializers.message import MessageConversationSerializer, MessageCountrySerializer, MessageReadSerializer


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
        queryset = Message.objects.select_related('creator').order_by('-created_at', '-id')

        if user.is_organizer:
            country = self.request.query_params.get('country')
            if country is not None:
                try:
                    country = int(country)
                    if country <= 0:
                        raise ValueError
                except (TypeError, ValueError):
                    raise ValidationError({'country': 'Informe uma delegação válida.'})
            return queryset.filter(country_id=country) if country else queryset

        return queryset.filter(country_id=user.country_id)

    def perform_create(self, serializer):
        user = self.request.user
        if user.is_organizer:
            serializer.save(creator=user)
        else:
            serializer.save(creator=user, country_id=user.country_id)

    @action(detail=False, methods=['get'], serializer_class=MessageConversationSerializer)
    def conversas(self, request):
        user = request.user
        countries = Country.objects.select_related('flag')
        if not user.is_organizer:
            countries = countries.filter(pk=user.country_id)

        # Cada país recebe a posição de leitura do usuário que fez a consulta.
        last_read = MessageRead.objects.filter(
            user=user, country_id=OuterRef('pk'),
        ).values('last_read_message_id')[:1]
        countries = countries.annotate(
            last_read_id=Coalesce(Subquery(last_read), Value(0), output_field=BigIntegerField()),
        ).annotate(
            unread_count=Count('messages', filter=Q(messages__id__gt=F('last_read_id')) & ~Q(messages__creator=user)),
            last_message_at=Max('messages__created_at'),
        ).annotate(
            has_unread=Case(
                When(unread_count__gt=0, then=Value(True)),
                default=Value(False), output_field=BooleanField(),
            ),
        ).order_by('-has_unread', F('last_message_at').desc(nulls_last=True), 'name', 'id')

        page = self.paginate_queryset(countries)
        data = self.get_serializer(page, many=True).data
        return self.get_paginated_response(data)

    def get_receipt_country(self, serializer):
        country = serializer.validated_data['country']
        if not self.request.user.is_organizer and country.pk != self.request.user.country_id:
            raise NotFound()
        return country

    @action(detail=False, methods=['post'], serializer_class=MessageReadSerializer)
    def lidas(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        country = self.get_receipt_country(serializer)
        message = get_object_or_404(Message, pk=serializer.validated_data['last_message_id'], country=country)
        receipt, _ = MessageRead.objects.get_or_create(user=request.user, country=country)
        # Uma confirmação atrasada não pode desfazer uma leitura mais recente.
        MessageRead.objects.filter(
            pk=receipt.pk, last_read_message_id__lt=message.pk,
        ).update(last_read_message_id=message.pk)
        return Response({'country': country.pk})

    @action(detail=False, methods=['post'], url_path='nao-lidas', serializer_class=MessageCountrySerializer)
    def nao_lidas(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        country = self.get_receipt_country(serializer)
        last_received = Message.objects.filter(
            country=country,
        ).exclude(creator=request.user).order_by('-id').first()
        if last_received is None:
            raise ValidationError({'country': 'Esta conversa ainda não tem mensagens recebidas.'})
        receipt, _ = MessageRead.objects.get_or_create(user=request.user, country=country)
        # Se já existem não lidas, preservar todas em vez de reduzir a contagem.
        MessageRead.objects.filter(
            pk=receipt.pk, last_read_message_id__gte=last_received.pk,
        ).update(last_read_message_id=last_received.pk - 1)
        return Response({'country': country.pk})
