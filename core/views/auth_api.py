import json
from copy import copy
from io import BytesIO

from allauth.account.models import EmailAddress
from allauth.headless.account import views as account_views
from allauth.headless.constants import Client
from django.db import transaction
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.authentication import SessionAuthentication
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from core.google_link import consume_connection_result
from core.models import User
from core.serializers.auth import (
    LoginSerializer,
    PendingVerificationSerializer,
    RegistrationResponseSerializer,
    RegistrationSerializer,
    TokenPairSerializer,
    VerificationSerializer,
)
from uploader.limits import RegistrationRateThrottle

SESSION_HEADER = OpenApiParameter(
    'X-Session-Token',
    str,
    OpenApiParameter.HEADER,
    description='session_token recebido no cadastro ou no login pendente.',
    required=True,
)


def token_pair(user):
    if (
        not user.is_active
        or not EmailAddress.objects.filter(user=user, email__iexact=user.email, verified=True).exists()
    ):
        raise PermissionDenied('Confirme seu e-mail antes de obter tokens.')
    refresh = RefreshToken.for_user(user)
    return {'access': str(refresh.access_token), 'refresh': str(refresh)}


class AllauthAPIView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def invoke(self, request, view, *, signup_data=None, photo=None):
        # O allauth lê o JSON original e gerencia o código, os limites e a sessão pendente.
        raw_request = request._request
        if signup_data is not None:
            # Allauth accepts JSON; preserve multipart upload validation from dev.
            raw_request = copy(raw_request)
            raw_request.META = raw_request.META.copy()
            raw_request._body = json.dumps(signup_data).encode()
            raw_request._stream = BytesIO(raw_request._body)
            raw_request.META['CONTENT_TYPE'] = 'application/json'
            raw_request.META['CONTENT_LENGTH'] = str(len(raw_request._body))
            raw_request.registration_photo = photo
        response = view.as_api_view(client=Client.APP)(raw_request)
        if not response.get('Content-Type', '').startswith('application/json'):
            return None, response
        return json.loads(response.content), response

    def authentication_response(self, payload, response):
        if payload is None:
            return response
        if payload.get('meta', {}).get('is_authenticated'):
            user = User.objects.get(pk=payload['data']['user']['id'])
            return Response(token_pair(user))
        flows = payload.get('data', {}).get('flows', [])
        if any(flow['id'] == 'verify_email' and flow.get('is_pending') for flow in flows):
            return Response(
                {
                    'detail': 'Confirme seu e-mail com o código enviado.',
                    'email_verification_required': True,
                    'session_token': payload.get('meta', {}).get('session_token'),
                },
                status=status.HTTP_401_UNAUTHORIZED,
            )
        return Response(payload, status=response.status_code)


class RegistrationView(AllauthAPIView):
    throttle_classes = [RegistrationRateThrottle]

    @extend_schema(
        request=RegistrationSerializer, responses={201: RegistrationResponseSerializer}, tags=['Autenticação']
    )
    @transaction.atomic
    def post(self, request):
        # Preserva o corpo para o allauth antes de o parser do DRF consumir o stream.
        request._request.body
        serializer = RegistrationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = dict(serializer.validated_data)
        photo = data.pop('foto', None)
        if data.get('gang') is not None:
            data['gang'] = data['gang'].pk
        payload, response = self.invoke(request, account_views.SignupView, signup_data=data, photo=photo)
        result = self.authentication_response(payload, response)
        if isinstance(result, Response) and result.data.get('email_verification_required'):
            user = User.objects.get(email__iexact=serializer.validated_data['email'])
            result.data.update(RegistrationSerializer(user).data)
            result.status_code = status.HTTP_201_CREATED
        return result


class TokenLoginView(AllauthAPIView):
    @extend_schema(
        request=LoginSerializer,
        responses={200: TokenPairSerializer, 401: PendingVerificationSerializer},
        tags=['Autenticação'],
    )
    def post(self, request):
        return self.authentication_response(*self.invoke(request, account_views.LoginView))


class VerifyEmailView(AllauthAPIView):
    @extend_schema(
        request=VerificationSerializer,
        responses={200: TokenPairSerializer},
        parameters=[SESSION_HEADER],
        tags=['Autenticação'],
    )
    def post(self, request):
        return self.authentication_response(*self.invoke(request, account_views.VerifyEmailView))


class ResendEmailView(AllauthAPIView):
    @extend_schema(
        request=None, responses={200: PendingVerificationSerializer}, parameters=[SESSION_HEADER], tags=['Autenticação']
    )
    def post(self, request):
        payload, response = self.invoke(request, account_views.ResendEmailVerificationCodeView)
        if payload is None:
            return response
        return Response(payload, status=response.status_code)


class SessionTokenView(APIView):
    """Troca a sessão obtida via Google/allauth pelo JWT usado no site."""

    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(request=None, responses={200: TokenPairSerializer}, tags=['Autenticação'])
    def post(self, request):
        if request.data.get('purpose') == 'google_connect':
            if not consume_connection_result(request._request):
                return Response(
                    {'detail': 'A vinculação não foi concluída. Confirme sua senha e tente novamente.'}, status=409
                )
            return Response({**token_pair(request.user), 'google_connected': True})
        return Response(token_pair(request.user))
