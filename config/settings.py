# config/settings.py

import os
from pathlib import Path
from datetime import timedelta
import environ

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Initialize environment variables
# نام متغیر را به env_settings تغییر می‌دهیم تا با نام کلاس تداخل نداشته باشد
env_settings = environ.Env(
    DEBUG=(bool, False)  # Default value for DEBUG
)

# Reading .env file from project root
# این خط بسیار مهم است و مسیر فایل .env را به طور صریح مشخص می‌کند
environ.Env.read_env(os.path.join(BASE_DIR, '.env'))

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.0/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = env_settings('SECRET_KEY')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = env_settings('DEBUG')

# For production, set ALLOWED_HOSTS in .env file
ALLOWED_HOSTS = env_settings.list('ALLOWED_HOSTS', default=[])

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

    # Local apps (ترتیب برحسب وابستگی)
    'apps.core',          # BaseModel (هیچ چیز به این وابسته نیست)
    'apps.accounts',      # User, UserProfile (وابستگی کمی دارد)
    'apps.instruments',   # Instrument, Indicator (به accounts نه)
    'apps.exchanges',     # Exchange, ExchangeAccount (به accounts وابسته است)
    'apps.market_data',   # DataSource, MarketDataConfig (به instruments و exchanges)
    'apps.strategies',    # Strategy (به instruments و accounts)
    'apps.agents',        # Agent, AgentType (وابستگی کمی دارد، اما بقیه ممکن است به این نیاز داشته باشند)
    'apps.signals',       # Signal (به agents, strategies, instruments, trading)
    'apps.trading',       # Order, Trade, Position (به agents, signals, instruments, exchanges, accounts)
    'apps.bots',          # Bot (به trading, strategies, exchanges, accounts)
    'apps.risk',          # RiskProfile (به accounts, bots, agents, trading)
    'apps.connectors',    # APICredential, ExchangeConnectorConfig (به exchanges)
    'apps.logging_app',   # SystemLog, Alert (به agents, signals, trading, risk, accounts)
    'apps.backtesting',
    'apps.agent_runtime',
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
# https://docs.djangoproject.com/en/5.0/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': env_settings('DB_NAME'),
        'USER': env_settings('DB_USER'),
        'PASSWORD': env_settings('DB_PASSWORD'),
        'HOST': env_settings('DB_HOST', default='localhost'), # استفاده صحیح از default
        'PORT': env_settings('DB_PORT', default='5432'), # استفاده صحیح از default
    }
}


# Password validation
# https://docs.djangoproject.com/en/5.0/ref/settings/#auth-password-validators

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
# https://docs.djangoproject.com/en/5.0/topics/i18n/

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.0/howto/static-files/

STATIC_URL = 'static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

# Default primary key field type
# https://docs.djangoproject.com/en/5.0/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# --- تنظیمات سفارشی پروژه ---

# 1. مدل کاربر سفارشی
AUTH_USER_MODEL = 'accounts.CustomUser'



# 2. تنظیمات Django REST Framework
# REST Framework
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    # اضافه کردن throttling برای امنیت
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle'
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '100/hour',
        'user': '1000/hour'
    }
}

# 3. تنظیمات JWT
# JWT Settings
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=60),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": True,
    "ALGORITHM": "HS256",
    "SIGNING_KEY": SECRET_KEY, # استفاده از SECRET_KEY اصلی
    "VERIFYING_KEY": "",
    "AUDIENCE": None,
    "ISSUER": None,
    "JWK_URL": None,
    "LEEWAY": 0,

    "AUTH_HEADER_TYPES": ("Bearer",),
    "AUTH_HEADER_NAME": "HTTP_AUTHORIZATION",
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
    "USER_AUTHENTICATION_RULE": "rest_framework_simplejwt.authentication.default_user_authentication_rule",

    "AUTH_TOKEN_CLASSES": ("rest_framework_simplejwt.tokens.AccessToken",),
    "TOKEN_TYPE_CLAIM": "token_type",
    "TOKEN_USER_CLASS": "rest_framework_simplejwt.models.TokenUser",

    "JTI_CLAIM": "jti",

    "SLIDING_TOKEN_REFRESH_EXP_CLAIM": "refresh_exp",
    "SLIDING_TOKEN_LIFETIME": timedelta(minutes=5),
    "SLIDING_TOKEN_REFRESH_LIFETIME": timedelta(days=1),
}





# 4. تنظیمات CORS
CORS_ALLOWED_ORIGINS = env_settings.list('CORS_ALLOWED_ORIGINS', default=["http://localhost:3000"])
CORS_ALLOW_CREDENTIALS = True



# Celery Settings
CELERY_BROKER_URL = env_settings('CELERY_BROKER_URL', default='redis://localhost:6379/0')
CELERY_RESULT_BACKEND = env_settings('CELERY_RESULT_BACKEND', default='redis://localhost:6379/0')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'UTC'


# Cache: برای django-filter حتماً Redis cache را در settings.py تنظیم کنید:
# CACHES = {
#     'default': {
#         'BACKEND': 'django_redis.cache.RedisCache',
#         'LOCATION': 'redis://127.0.0.1:6379/1',
#         'OPTIONS': {
#             'CLIENT_CLASS': 'django_redis.client.DefaultClient',
#         }
#     }
# }


CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'unique-snowflake',
    }
}



##############################################
###  OLD :
##############################################

# # config/settings.py
#
# import os
# from pathlib import Path
# from datetime import timedelta
# # pip install django-environ
# import environ
#
#
# # Build paths inside the project like this: BASE_DIR / 'subdir'.
# BASE_DIR = Path(__file__).resolve().parent.parent.parent
#
# # env = environ.Env(
# #     DEBUG=(bool, False)  # مقدار پیش‌فرض برای DEBUG
# # )
#
#
# env = environ.Env()
# environ.Env.read_env()  # اگر پارامتر مسیر ندادید باید .env در کنار settings.py باشد
#
#
# # خواندن فایل .env
# # environ.Env.read_env(os.path.join(BASE_DIR, '.env'))
# # environ.Env.read_env(os.path.join(BASE_DIR, '.env'))
# # environ.Env.read_env(BASE_DIR / ".env")
# # environ.Env.read_env(BASE_DIR / "config/.env")
#
#
#
#
# # Quick-start development settings - unsuitable for production
# # See https://docs.djangoproject.com/en/4.2/howto/deployment/checklist/
#
# # SECURITY WARNING: keep the secret key used in production secret!
# # SECRET_KEY = os.environ.get('SECRET_KEY', 'django-insecure-your-secret-key-here')
#
# SECRET_KEY = env('SECRET_KEY')
# # print(f"SECRET_KEY: {'SECRET_KEY'}")
#
#
# # SECURITY WARNING: don't run with debug turned on in production!
# # DEBUG = os.environ.get('DEBUG', 'True').lower() in ['true', '1', 'yes']
# DEBUG = env('DEBUG')
#
# ALLOWED_HOSTS = []
#
#
# # Application definition
# INSTALLED_APPS = [
#     # Default Django apps
#     'django.contrib.admin',
#     'django.contrib.auth',
#     'django.contrib.contenttypes',
#     'django.contrib.sessions',
#     'django.contrib.messages',
#     'django.contrib.staticfiles',
#
#     # Third-party apps
#     'rest_framework',
#     'rest_framework.authtoken',
#     'rest_framework_simplejwt',
#     'corsheaders',
#
#     # Local apps (ترتیب برحسب وابستگی)
#     'apps.core',          # BaseModel (هیچ چیز به این وابسته نیست)
#     'apps.accounts',      # User, UserProfile (وابستگی کمی دارد)
#     'apps.instruments',   # Instrument, Indicator (به accounts نه)
#     'apps.exchanges',     # Exchange, ExchangeAccount (به accounts وابسته است)
#     'apps.market_data',   # DataSource, MarketDataConfig (به instruments و exchanges)
#     'apps.strategies',    # Strategy (به instruments و accounts)
#     'apps.agents',        # Agent, AgentType (وابستگی کمی دارد، اما بقیه ممکن است به این نیاز داشته باشند)
#     'apps.signals',       # Signal (به agents, strategies, instruments, trading)
#     'apps.trading',       # Order, Trade, Position (به agents, signals, instruments, exchanges, accounts)
#     'apps.bots',          # Bot (به trading, strategies, exchanges, accounts)
#     'apps.risk',          # RiskProfile (به accounts, bots, agents, trading)
#     'apps.connectors',    # APICredential, ExchangeConnectorConfig (به exchanges)
#     'apps.logging_app',   # SystemLog, Alert (به agents, signals, trading, risk, accounts)
#     'apps.backtesting',
#     'apps.agent_runtime',
# ]
#
#
#
# MIDDLEWARE = [
#     'corsheaders.middleware.CorsMiddleware',
#     'django.middleware.security.SecurityMiddleware',
#     'django.contrib.sessions.middleware.SessionMiddleware',
#     'django.middleware.common.CommonMiddleware',
#     'django.middleware.csrf.CsrfViewMiddleware',
#     'django.contrib.auth.middleware.AuthenticationMiddleware',
#     'django.contrib.messages.middleware.MessageMiddleware',
#     'django.middleware.clickjacking.XFrameOptionsMiddleware',
# ]
#
# ROOT_URLCONF = 'config.urls'
#
# TEMPLATES = [
#     {
#         'BACKEND': 'django.template.backends.django.DjangoTemplates',
#         'DIRS': [],
#         'APP_DIRS': True,
#         'OPTIONS': {
#             'context_processors': [
#                 'django.template.context_processors.debug',
#                 'django.template.context_processors.request',
#                 'django.contrib.auth.context_processors.auth',
#                 'django.contrib.messages.context_processors.messages',
#             ],
#         },
#     },
# ]
#
# WSGI_APPLICATION = 'config.wsgi.application'
#
#
# # Database
# # https://docs.djangoproject.com/en/4.2/ref/settings/#databases
#
# # DATABASES = {
# #     'default': {
# #         'ENGINE': 'django.db.backends.postgresql',
# #         'NAME': os.environ.get('DB_NAME', DB_NAME),
# #         'USER': os.environ.get('DB_USER', DB_USER),
# #         'PASSWORD': os.environ.get('DB_PASSWORD', DB_PASSWORD),
# #         'HOST': os.environ.get('DB_HOST', DB_HOST),
# #         # 'PORT': os.environ.get('DB_PORT', '5432'),
# #         'PORT': os.environ.get('DB_PORT', DB_PORT),
# #     }
# # }
#
# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.postgresql',
#         'NAME': env('DB_NAME'),
#         'USER': env('DB_USER'),
#         'PASSWORD': env('DB_PASSWORD'),
#         'HOST': env('DB_HOST'),
#         # 'PORT': os.environ.get('DB_PORT', '5432'),
#         'PORT': env('DB_PORT'),
#     }
# }
#
#
# # Password validation
# # https://docs.djangoproject.com/en/4.2/ref/settings/#auth-password-validators
#
# AUTH_PASSWORD_VALIDATORS = [
#     {
#         'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
#     },
#     {
#         'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
#     },
#     {
#         'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
#     },
#     {
#         'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
#     },
# ]
#
#
# # Internationalization
# # https://docs.djangoproject.com/en/4.2/topics/i18n/
#
# LANGUAGE_CODE = 'en-us'
# TIME_ZONE = 'UTC'
# USE_I18N = True
# USE_TZ = True
#
#
# # Static files (CSS, JavaScript, Images)
# # https://docs.djangoproject.com/en/4.2/howto/static-files/
#
# STATIC_URL = 'static/'
# STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
#
# # Default primary key field type
# # https://docs.djangoproject.com/en/4.2/ref/settings/#default-auto-field
#
# DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
#
# # --- تنظیمات سفارشی پروژه ---
#
# # 1. مدل کاربر سفارشی
# AUTH_USER_MODEL = 'accounts.CustomUser'
#
#
#
# # 2. تنظیمات Django REST Framework
# # REST Framework
# REST_FRAMEWORK = {
#     'DEFAULT_AUTHENTICATION_CLASSES': (
#         'rest_framework_simplejwt.authentication.JWTAuthentication',
#     ),
#     'DEFAULT_PERMISSION_CLASSES': [
#         'rest_framework.permissions.IsAuthenticated',
#     ],
#     # اضافه کردن throttling برای امنیت
#     'DEFAULT_THROTTLE_CLASSES': [
#         'rest_framework.throttling.AnonRateThrottle',
#         'rest_framework.throttling.UserRateThrottle'
#     ],
#     'DEFAULT_THROTTLE_RATES': {
#         'anon': '100/hour',
#         'user': '1000/hour'
#     }
# }
#
# # 3. تنظیمات JWT
# # JWT Settings
# SIMPLE_JWT = {
#     "ACCESS_TOKEN_LIFETIME": timedelta(minutes=60),
#     "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
#     "ROTATE_REFRESH_TOKENS": True,
#     "BLACKLIST_AFTER_ROTATION": True,
#     "UPDATE_LAST_LOGIN": True,
#     "ALGORITHM": "HS256",
#     "SIGNING_KEY": "SIGNING_KEY_SIMPLE_JWT",  # تغییر دهید و در متغیرهای محیطی قرار دهید
#     "VERIFYING_KEY": "",
#     "AUDIENCE": None,
#     "ISSUER": None,
#     "JWK_URL": None,
#     "LEEWAY": 0,
#
#     "AUTH_HEADER_TYPES": ("Bearer",),
#     "AUTH_HEADER_NAME": "HTTP_AUTHORIZATION",
#     "USER_ID_FIELD": "id",
#     "USER_ID_CLAIM": "user_id",
#     "USER_AUTHENTICATION_RULE": "rest_framework_simplejwt.authentication.default_user_authentication_rule",
#
#     "AUTH_TOKEN_CLASSES": ("rest_framework_simplejwt.tokens.AccessToken",),
#     "TOKEN_TYPE_CLAIM": "token_type",
#     "TOKEN_USER_CLASS": "rest_framework_simplejwt.models.TokenUser",
#
#     "JTI_CLAIM": "jti",
#
#     "SLIDING_TOKEN_REFRESH_EXP_CLAIM": "refresh_exp",
#     "SLIDING_TOKEN_LIFETIME": timedelta(minutes=5),
#     "SLIDING_TOKEN_REFRESH_LIFETIME": timedelta(days=1),
# }
#
#
#
#
#
# # 4. تنظیمات CORS
# CORS_ALLOWED_ORIGINS = [
#     "http://localhost:3000",  # آدرس فرانت‌اند شما در محیط توسعه
# ]
#
#
#
# # Celery Settings
# CELERY_BROKER_URL = 'redis://localhost:6379/0'
# CELERY_RESULT_BACKEND = 'redis://localhost:6379/0'
# CELERY_ACCEPT_CONTENT = ['json']
# CELERY_TASK_SERIALIZER = 'json'
# CELERY_RESULT_SERIALIZER = 'json'
# CELERY_TIMEZONE = 'UTC'
#
#
# # Cache: برای django-filter حتماً Redis cache را در settings.py تنظیم کنید:
# # CACHES = {
# #     'default': {
# #         'BACKEND': 'django_redis.cache.RedisCache',
# #         'LOCATION': 'redis://127.0.0.1:6379/1',
# #         'OPTIONS': {
# #             'CLIENT_CLASS': 'django_redis.client.DefaultClient',
# #         }
# #     }
# # }
#
#
# CACHES = {
#     'default': {
#         'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
#         'LOCATION': 'unique-snowflake',
#     }
# }