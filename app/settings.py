import os
from datetime import timedelta
from pathlib import Path

import dj_database_url
from corsheaders.defaults import default_headers
from dotenv import load_dotenv
from django.core.exceptions import ImproperlyConfigured

# Carrega as variáveis de ambiente do arquivo .env
load_dotenv()

# Define o modo de execução da aplicação

# Constrói o caminho base do projeto, usado para definir caminhos relativos

# Segurança e configuração básica
MODE = os.getenv('MODE')
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / '.secrets' / 'google.env')
SECRET_KEY = os.getenv('SECRET_KEY', 'django-insecure')
DEBUG = os.getenv('DEBUG', 'False').strip().lower() in {'true', '1', 'yes', 'on'}
DEFAULT_EXCEPTION_REPORTER_FILTER = 'app.debug.SensitiveSettingsFilter'
ALLOWED_HOSTS = ['*']
FRONTEND_URL = os.getenv('FRONTEND_URL', 'https://sinuca-ifc-mocha.vercel.app').strip().rstrip('/')
# Cookies belong to the HTTPS API.
SESSION_COOKIE_SECURE = os.getenv(
    'AUTH_COOKIE_SECURE', str(FRONTEND_URL.startswith('https://'))
).strip().lower() in {'true', '1', 'yes', 'on'}
CSRF_COOKIE_SECURE = SESSION_COOKIE_SECURE
# Enable only when the frontend and API are on different sites (e.g. Vercel/IFC).
# Exact-origin CORS and CSRF validation remain required.
AUTH_CROSS_SITE_COOKIES = os.getenv('AUTH_CROSS_SITE_COOKIES', 'True').strip().lower() in {'true', '1', 'yes', 'on'}
if AUTH_CROSS_SITE_COOKIES and not SESSION_COOKIE_SECURE:
    raise ImproperlyConfigured('AUTH_CROSS_SITE_COOKIES requires AUTH_COOKIE_SECURE=True and an HTTPS backend.')
SESSION_COOKIE_SAMESITE = 'None' if AUTH_CROSS_SITE_COOKIES else 'Lax'
CSRF_COOKIE_SAMESITE = SESSION_COOKIE_SAMESITE
# Enable only behind a proxy that overwrites this header.
if os.getenv('TRUST_PROXY_HTTPS', 'False').lower() == 'true':
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
# Explicit browser origins supported by the frontend; no wildcard credentials.
FRONTEND_ALLOWED_ORIGINS = list(dict.fromkeys([
    FRONTEND_URL,
    *[origin.strip().rstrip('/') for origin in os.getenv(
        'FRONTEND_ALLOWED_ORIGINS',
        '',
    ).split(',') if origin.strip()],
]))
CSRF_TRUSTED_ORIGINS = FRONTEND_ALLOWED_ORIGINS
CORS_ALLOW_ALL_ORIGINS = False
CORS_ALLOWED_ORIGINS = FRONTEND_ALLOWED_ORIGINS
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_HEADERS = (*default_headers, 'x-session-token', 'x-push-endpoint')

# Aplicações instaladas
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'cloudinary_storage',
    'cloudinary',
    'corsheaders',
    'django_extensions',
    'django_filters',
    'drf_spectacular',
    'rest_framework',
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'allauth.socialaccount.providers.google',
    'allauth.headless',
    'uploader',
    'core',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'allauth.account.middleware.AccountMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'app.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'app.wsgi.application'

# Banco de dados
DATABASES = {
    'default': dj_database_url.config(
        default='sqlite:///db.sqlite3',
        conn_max_age=600,
        conn_health_checks=True,
    )
}

# Validação de senhas
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Configurações do Django-allauth
AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
    'allauth.account.auth_backends.AuthenticationBackend',
]

ACCOUNT_USER_MODEL_USERNAME_FIELD = None
ACCOUNT_USER_MODEL_EMAIL_FIELD = 'email'
ACCOUNT_LOGIN_METHODS = {'email'}
ACCOUNT_SIGNUP_FIELDS = ['email*', 'password1*', 'password2*']
ACCOUNT_EMAIL_VERIFICATION = 'mandatory'
ACCOUNT_EMAIL_VERIFICATION_BY_CODE_ENABLED = True
ACCOUNT_EMAIL_VERIFICATION_BY_CODE_FORMAT = {
    'length': 6,
    'numeric': True,
    'dashed': False,
}
ACCOUNT_EMAIL_VERIFICATION_BY_CODE_TIMEOUT = 600
ACCOUNT_EMAIL_VERIFICATION_BY_CODE_MAX_ATTEMPTS = 3
ACCOUNT_EMAIL_VERIFICATION_SUPPORTS_RESEND = True
ACCOUNT_RATE_LIMITS = {'signup': '30/m/ip'}
ACCOUNT_SIGNUP_FORM_CLASS = 'core.forms.SignupProfileForm'

SOCIALACCOUNT_AUTO_SIGNUP = True
# The adapter only matches active accounts with a locally verified email.
SOCIALACCOUNT_EMAIL_AUTHENTICATION_AUTO_CONNECT = True
SOCIALACCOUNT_ADAPTER = 'core.adapters.SocialAccountAdapter'
HEADLESS_ONLY = True
HEADLESS_CLIENTS = ('browser', 'app')
LOGIN_REDIRECT_URL = f'{FRONTEND_URL}/auth/callback'
ACCOUNT_LOGOUT_REDIRECT_URL = f'{FRONTEND_URL}/login'
SOCIALACCOUNT_PROVIDERS = {
    'google': {
        'APP': {
            'client_id': os.getenv('GOOGLE_CLIENT_ID', ''),
            'secret': os.getenv('GOOGLE_CLIENT_SECRET', ''),
            'key': '',
        },
        'SCOPE': ['profile', 'email'],
        'AUTH_PARAMS': {'access_type': 'online'},
    },
}
HEADLESS_FRONTEND_URLS = {
    'account_confirm_email': f'{FRONTEND_URL}/verificar-email',
    'account_reset_password': f'{FRONTEND_URL}/recuperar-senha',
    'account_reset_password_from_key': f'{FRONTEND_URL}/redefinir-senha/{{key}}',
    'account_signup': f'{FRONTEND_URL}/cadastro',
    'socialaccount_login_error': f'{FRONTEND_URL}/auth/callback',
}

EMAIL_BACKEND = os.getenv(
    'EMAIL_BACKEND',
    'django.core.mail.backends.smtp.EmailBackend',
)
EMAIL_HOST = os.getenv('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(os.getenv('EMAIL_PORT', '587'))
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER', 'sinuca.ifc.no.reply@gmail.com')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD', '')
EMAIL_USE_TLS = os.getenv('EMAIL_USE_TLS', 'True').lower() == 'true'
EMAIL_USE_SSL = os.getenv('EMAIL_USE_SSL', 'False').lower() == 'true'
EMAIL_TIMEOUT = 15
DEFAULT_FROM_EMAIL = os.getenv('DEFAULT_FROM_EMAIL', 'SINUCA <sinuca.ifc.no.reply@gmail.com>')

# Configurações de internacionalização
LANGUAGE_CODE = 'pt-br'
TIME_ZONE = 'America/Sao_Paulo'
USE_I18N = True
USE_TZ = True

# Configurações de arquivos estáticos
STATIC_URL = 'static/'

# Configurações de arquivos de mídia (App Uploader)
MEDIA_ENDPOINT = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media/')
FILE_UPLOAD_PERMISSIONS = 0o640
UPLOADER_MAX_IMAGE_BYTES = 5 * 1024 * 1024
UPLOADER_MAX_DOCUMENT_BYTES = 10 * 1024 * 1024
UPLOADER_MAX_IMAGE_DIMENSION = 4096
UPLOADER_MAX_FILES_PER_USER = 50
UPLOADER_MAX_BYTES_PER_USER = 100 * 1024 * 1024


# Configurações específicas para desenvolvimento, migração e produção
MEDIA_URL = '/media/'
if MODE != 'DEVELOPMENT':
    CLOUDINARY_URL = os.getenv('CLOUDINARY_URL')
    STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
    STORAGES = {
        'default': {
            'BACKEND': 'cloudinary_storage.storage.MediaCloudinaryStorage',
        },
        'staticfiles': {
            'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage',
        },
    }

# STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"


# Tipo padrão de campo para chaves primárias
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Configurações do DRF e drf-spectacular (OpenAPI/Swagger)
SPECTACULAR_SETTINGS = {
    'TITLE': 'SINUCA API',
    'DESCRIPTION': 'API para o projeto do SINUCA.',
    'VERSION': '1.0.0',
}

# Modelo de usuário personalizado
AUTH_USER_MODEL = 'core.User'

# Configurações do Django REST Framework
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ),
    'DEFAULT_PAGINATION_CLASS': 'app.pagination.CustomPagination',
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'PAGE_SIZE': 10,
}

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=180),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=1),
    'AUTH_HEADER_TYPES': ('Bearer',),
}

# Web Push (VAPID). The private key must only exist in the backend environment.
VAPID_PUBLIC_KEY = os.getenv('VAPID_PUBLIC_KEY', '')
VAPID_PRIVATE_KEY = os.getenv('VAPID_PRIVATE_KEY', '')
VAPID_SUBJECT = os.getenv('VAPID_SUBJECT', 'mailto:admin@example.com')

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {'push_console': {'class': 'logging.StreamHandler'}},
    'loggers': {
        'django.security.csrf': {
            'handlers': ['push_console'],
            'level': 'WARNING',
            'propagate': False,
        },
        'core.services.push': {
            'handlers': ['push_console'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}
