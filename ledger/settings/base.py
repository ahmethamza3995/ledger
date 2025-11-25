import os
from pathlib import Path
from dotenv import load_dotenv
import dj_database_url
from django.urls import reverse_lazy

BASE_DIR = Path(__file__).resolve().parent.parent.parent
ENV_PATH = BASE_DIR / '.env'
if ENV_PATH.exists():
    load_dotenv(ENV_PATH)

SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-me')
DEBUG = False
ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', '127.0.0.1,localhost').split(',')

INSTALLED_APPS = [
    'django.contrib.admin','django.contrib.auth','django.contrib.contenttypes',
    'django.contrib.sessions','django.contrib.messages','django.contrib.staticfiles',
    'rest_framework','django_filters',
    'transactions',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'ledger.urls'
TEMPLATES = [{
    'BACKEND':'django.template.backends.django.DjangoTemplates',
    'DIRS':[BASE_DIR / 'transactions' / 'templates'],
    'APP_DIRS':True,
    'OPTIONS':{'context_processors':[
        'django.template.context_processors.debug',
        'django.template.context_processors.request',
        'django.contrib.auth.context_processors.auth',
        'django.contrib.messages.context_processors.messages',
    ]},
}]
WSGI_APPLICATION = 'ledger.wsgi.application'
ASGI_APPLICATION = 'ledger.asgi.application'

# DB: DATABASE_URL ya da DB_* parçaları
DATABASES = {}
DATABASE_URL = os.getenv('DATABASE_URL')
if DATABASE_URL:
    DATABASES['default'] = dj_database_url.parse(DATABASE_URL, conn_max_age=600, ssl_require=False)
else:
    DATABASES['default'] = {
        'ENGINE':'django.db.backends.postgresql',
        'NAME':os.getenv('DB_NAME','ledger'),
        'USER':os.getenv('DB_USER','postgres'),
        'PASSWORD':os.getenv('DB_PASSWORD',''),
        'HOST':os.getenv('DB_HOST','localhost'),
        'PORT':os.getenv('DB_PORT','5432'),
    }

# E-posta ile giriş backend'i — ileride dosyasını ekleyeceğiz
AUTHENTICATION_BACKENDS = [
    'transactions.authentication.EmailBackend',
    'django.contrib.auth.backends.ModelBackend',
]

LANGUAGE_CODE = 'tr-tr'
TIME_ZONE = 'Europe/Istanbul'
USE_I18N = True
USE_TZ = True

# Oturum: 30 dk. Her istekte oturum yenileniyor
SESSION_COOKIE_AGE = 1800
SESSION_SAVE_EVERY_REQUEST = True

LOGIN_URL = '/auth/login/'
LOGIN_REDIRECT_URL = '/transactions/'

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'transactions' / 'static']

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.AutoField'

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': ['rest_framework.authentication.SessionAuthentication'],
    'DEFAULT_PERMISSION_CLASSES': ['rest_framework.permissions.IsAuthenticated'],
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 100,
}

CSRF_TRUSTED_ORIGINS = os.getenv('CSRF_TRUSTED_ORIGINS','').split(',') if os.getenv('CSRF_TRUSTED_ORIGINS') else []
