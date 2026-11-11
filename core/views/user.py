from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.generics import CreateAPIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from core.models import User
from core.permissions import HasDelegationForWrite, IsOrganizer, IsSelfOrOrganizer
from core.serializers import UserRegistrationSerializer, UserSerializer
from core.serializers.user import PendingUserSerializer, UserApprovalSerializer


class UserViewSet(ModelViewSet):
    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return User.objects.none()
        usuario = self.request.user
        if self.action in ['pendentes', 'aprovar'] and (usuario.is_superuser or usuario.is_organizer):
            return User.objects.filter(
                role=User.Role.STUDENT, country__isnull=True, is_superuser=False, is_active=True,
            ).order_by('id')

        if usuario.is_superuser or usuario.is_organizer:
            return User.objects.all().order_by('id')

        if not usuario.country:
            return User.objects.none()

        return User.objects.filter(
            country=usuario.country
        ).distinct()

    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated, HasDelegationForWrite, IsSelfOrOrganizer]

    @extend_schema(summary='Alunos aguardando aprovação', responses=PendingUserSerializer(many=True))
    @action(detail=False, methods=['get'], permission_classes=[IsOrganizer])
    def pendentes(self, request):
        queryset = self.get_queryset()
        page = self.paginate_queryset(queryset)
        if page is not None:
            return self.get_paginated_response(PendingUserSerializer(page, many=True).data)
        return Response(PendingUserSerializer(queryset, many=True).data)

    @extend_schema(summary='Aprovar aluno e atribuir delegação', request=UserApprovalSerializer, responses=UserSerializer)
    @action(detail=True, methods=['post'], permission_classes=[IsOrganizer])
    def aprovar(self, request, pk=None):
        student = self.get_object()
        serializer = UserApprovalSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        updated = User.objects.filter(
            pk=student.pk, country__isnull=True, role=User.Role.STUDENT, is_superuser=False, is_active=True,
        ).update(
            country=serializer.validated_data['country'],
        )
        if not updated:
            raise ValidationError({'country': 'Este aluno já recebeu uma delegação.'})
        student.refresh_from_db()
        return Response(UserSerializer(student).data)

    @extend_schema(
        summary="Dados do usuário autenticado",
        description="Retorna os dados do usuário autenticado.",
        responses={200: UserSerializer, 401: None},
    )
    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def me(self, request):
        """ Retorna os dados do usuário autenticado."""
        user = request.user
        serializer = UserSerializer(user)
        return Response(serializer.data, status=status.HTTP_200_OK)


class UserRegistrationView(CreateAPIView):
    """Endpoint para registro de novos usuários."""

    queryset = User.objects.all()
    serializer_class = UserRegistrationSerializer
    permission_classes = [AllowAny]
