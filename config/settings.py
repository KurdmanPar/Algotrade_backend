# config/settings/base.py

import os
from pathlib import Path

# pip install django-environ
import environ


# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# env = environ.Env(
#     DEBUG=(bool, False)  # مقدار پیش‌فرض برای DEBUG
# )


env = environ.Env()
environ.Env.read_env()  # اگر پارامتر مسیر ندادید باید .env در کنار settings.py باشد


# خواندن فایل .env
# environ.Env.read_env(os.path.join(BASE_DIR, '.env'))
# environ.Env.read_env(os.path.join(BASE_DIR, '.env'))
# environ.Env.read_env(BASE_DIR / ".env")
# environ.Env.read_env(BASE_DIR / "config/.env")




# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/4.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
# SECRET_KEY = os.environ.get('SECRET_KEY', 'django-insecure-your-secret-key-here')

SECRET_KEY = env('SECRET_KEY')
# print(f"SECRET_KEY: {'SECRET_KEY'}")


# SECURITY WARNING: don't run with debug turned on in production!
# DEBUG = os.environ.get('DEBUG', 'True').lower() in ['true', '1', 'yes']
DEBUG = env('DEBUG')

ALLOWED_HOSTS = []


# Application definition
INSTALLED_APPS = [
    # Default Django apps
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Third-party apps
    'rest_framework',
    'rest_framework.authtoken',
    'rest_framework_simplejwt',
    'corsheaders',

    # Local apps (ترتیب مهم)
    'apps.core',
    'apps.accounts',
    'apps.instruments',
    'apps.exchanges',
    'apps.strategies',
    'apps.trading',
    'apps.bots',
    'apps.risk',
    'apps.logging_app',  # <--- باید قبل از signals باشد
    'apps.signals',  # <---
    'apps.agents',


]



MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
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

WSGI_APPLICATION = 'config.wsgi.application'


# Database
# https://docs.djangoproject.com/en/4.2/ref/settings/#databases

# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.postgresql',
#         'NAME': os.environ.get('DB_NAME', DB_NAME),
#         'USER': os.environ.get('DB_USER', DB_USER),
#         'PASSWORD': os.environ.get('DB_PASSWORD', DB_PASSWORD),
#         'HOST': os.environ.get('DB_HOST', DB_HOST),
#         # 'PORT': os.environ.get('DB_PORT', '5432'),
#         'PORT': os.environ.get('DB_PORT', DB_PORT),
#     }
# }

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': env('DB_NAME'),
        'USER': env('DB_USER'),
        'PASSWORD': env('DB_PASSWORD'),
        'HOST': env('DB_HOST'),
        # 'PORT': os.environ.get('DB_PORT', '5432'),
        'PORT': env('DB_PORT'),
    }
}


# Password validation
# https://docs.djangoproject.com/en/4.2/ref/settings/#auth-password-validators

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


# Internationalization
# https://docs.djangoproject.com/en/4.2/topics/i18n/

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/4.2/howto/static-files/

STATIC_URL = 'static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

# Default primary key field type
# https://docs.djangoproject.com/en/4.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# --- تنظیمات سفارشی پروژه ---

# 1. مدل کاربر سفارشی
AUTH_USER_MODEL = 'accounts.CustomUser'

# 2. تنظیمات Django REST Framework
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ]
}

# 3. تنظیمات JWT
from datetime import timedelta

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=60),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=1),
    'ROTATE_REFRESH_TOKENS': True,
}

# 4. تنظیمات CORS
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",  # آدرس فرانت‌اند شما در محیط توسعه
]
