from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import (
    TokenRefreshView,
    TokenVerifyView,
)

from core.views import (
    CategoryViewSet,
    CountryViewSet,
    GangViewSet,
    LinkViewSet,
    MessageViewSet,
    PostViewSet,
    PushSubscriptionView,
    ScheduleViewSet,
    TaskViewSet,
    UserViewSet,
    VapidPublicKeyView,
)
from core.views.auth import connect_google, csrf_token, google_login, logout_session, prepare_google_connection
from core.views.auth_api import RegistrationView, ResendEmailView, SessionTokenView, TokenLoginView, VerifyEmailView
from uploader.router import router as uploader_router

router = DefaultRouter()

router.register(r'tarefas', TaskViewSet, basename='tarefas')
router.register(r'usuarios', UserViewSet, basename='usuarios')
router.register(r'postagens', PostViewSet, basename='postagens')
router.register(r'categorias', CategoryViewSet, basename='categorias')
router.register(r'turmas', GangViewSet, basename='turmas')
router.register(r'paises', CountryViewSet, basename='paises')
router.register(r'cronogramas', ScheduleViewSet, basename='cronogramas')
router.register(r'docs', LinkViewSet, basename='docs')
router.register(r'mensagens', MessageViewSet, basename='mensagens')

urlpatterns = [
    path('api/token/session/', SessionTokenView.as_view(), name='session_token'),
    path('api/registro/confirmar-email/', VerifyEmailView.as_view(), name='verify_registration_email'),
    path('api/registro/reenviar-codigo/', ResendEmailView.as_view(), name='resend_registration_code'),
    path('api/auth/csrf/', csrf_token, name='csrf_token'),
    path('api/auth/google/', google_login, name='google_start'),
    path('api/auth/google/vincular/', prepare_google_connection, name='google_link_prepare'),
    path('api/auth/google/conectar/', connect_google, name='google_connect'),
    path('api/auth/logout/', logout_session, name='logout_session'),
    path('accounts/', include('allauth.urls')),
    path('_allauth/', include('allauth.headless.urls')),
    path('admin/', admin.site.urls),
    # OpenAPI 3
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path(
        'api/doc/',
        SpectacularSwaggerView.as_view(url_name='schema'),
        name='swagger-ui',
    ),
    path(
        'api/redoc/',
        SpectacularRedocView.as_view(url_name='schema'),
        name='redoc',
    ),
    path('api/media/', include(uploader_router.urls)),  # nova linha
    # Autenticação JWT
    path('api/token/', TokenLoginView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/token/verify/', TokenVerifyView.as_view(), name='token_verify'),
    # Registro de usuários
    path('api/registro/', RegistrationView.as_view(), name='user_registration'),
    path('api/vapid-public-key/', VapidPublicKeyView.as_view(), name='vapid-public-key'),
    path('api/push-subscriptions/', PushSubscriptionView.as_view(), name='push-subscriptions'),
    # API
    path('api/', include(router.urls)),
]

urlpatterns += static(settings.MEDIA_ENDPOINT, document_root=settings.MEDIA_ROOT)
