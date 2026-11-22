"""Isolated test configuration: no .env, external database, mail or cloud storage."""

import os
import tempfile

os.environ['PYTHON_DOTENV_DISABLED'] = '1'
os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
os.environ['MODE'] = 'DEVELOPMENT'
os.environ['FRONTEND_URL'] = 'http://localhost:5173'
os.environ['AUTH_CROSS_SITE_COOKIES'] = 'False'
os.environ['AUTH_COOKIE_SECURE'] = 'False'
os.environ['GOOGLE_CLIENT_ID'] = 'test-google-client'
os.environ['GOOGLE_CLIENT_SECRET'] = 'test-google-secret'

from .settings import *  # noqa: E402,F403

SECRET_KEY = 'isolated-test-secret-not-for-production-739'
DATABASES = {'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': ':memory:'}}
EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'
PASSWORD_HASHERS = ['django.contrib.auth.hashers.MD5PasswordHasher']
STORAGES = {
    'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
    'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'},
}
MEDIA_ROOT = tempfile.mkdtemp(prefix='sinuca-test-media-')
VAPID_PUBLIC_KEY = ''
VAPID_PRIVATE_KEY = ''
VAPID_SUBJECT = 'mailto:test@example.test'
