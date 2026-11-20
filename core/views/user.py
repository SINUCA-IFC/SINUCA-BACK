from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from core.models import User
from core.serializers import UserSerializer


class UserViewSet(ModelViewSet):
    http_method_names = ['get', 'put', 'patch', 'delete', 'head', 'options']

    def get_object(self):
        instance = super().get_object()
        if self.request.method not in {'GET', 'HEAD', 'OPTIONS'}:
            if instance.pk != self.request.user.pk and not self.request.user.is_superuser:
                raise PermissionDenied('Você só pode alterar seu próprio perfil.')
        return instance

    def get_queryset(self):
        usuario = self.request.user
        if usuario.is_superuser:
            return User.objects.all()

        if not usuario.country:
            return User.objects.filter(pk=usuario.pk)

        return User.objects.filter(country=usuario.country).distinct()

    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary='Dados do usuário autenticado',
        description='Retorna os dados do usuário autenticado.',
        responses={200: UserSerializer, 401: None, 403: None},
    )
    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def me(self, request):
        """Retorna os dados do usuário autenticado."""
        user = request.user
        serializer = UserSerializer(user)
        return Response(serializer.data, status=status.HTTP_200_OK)
