"""
Django settings for minv project.

For more information on this file, see
https://docs.djangoproject.com/en/1.7/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.7/ref/settings/
"""

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
import os

from minv.config import GlobalReader


BASE_DIR = os.path.dirname(os.path.dirname(__file__))

MINV_CONFIG_DIR = '/etc/minv'
MINV_DATA_DIR = '/srv/minv'
MINV_LOCK_DIR = '/tmp/minv/lock'
MINV_TASK_MODULES = [
    'minv.tasks.harvest',
    'minv.inventory.collection.export',
]


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.7/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = '{{ secret_key }}'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False

TEMPLATE_DEBUG = DEBUG

ALLOWED_HOSTS = ["*"]


# Application definition

INSTALLED_APPS = (
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.gis',
    'minv',
    'minv.inventory',
    'minv.tasks',
)

MIDDLEWARE_CLASSES = (
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
)

TEMPLATE_CONTEXT_PROCESSORS = (
    'django.contrib.auth.context_processors.auth',
    'django.core.context_processors.request',
    'django.contrib.messages.context_processors.messages',
)

ROOT_URLCONF = '{{ project_name }}.urls'

WSGI_APPLICATION = '{{ project_name }}.wsgi.application'


# Database
# https://docs.djangoproject.com/en/1.7/ref/settings/#databases

reader = GlobalReader(os.path.join(MINV_CONFIG_DIR, 'minv.conf'))
DATABASES = {
    'default': {
        'ENGINE': 'django.contrib.gis.db.backends.postgis',
        'HOST': reader.host,
        'PORT': reader.port,
        'NAME': reader.database,
        'USER': reader.user,
        'PASSWORD': reader.password
    }
}

# Internationalization
# https://docs.djangoproject.com/en/1.7/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

DATETIME_FORMAT = '%Y-%m-%d %H:%M:%S'

SHORT_DATETIME_FORMAT = '%Y-%m-%d %H:%M:%S'

DATETIME_FORMAT = 'c'

SHORT_DATETIME_FORMAT = 'c'


USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.7/howto/static-files/

STATIC_URL = '/minv_static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'static')


LOGIN_URL = '/login'


LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'simple': {
            'format': '%(levelname)s: %(message)s'
        },
        'verbose': {
            'format': '[%(asctime)s][%(module)s] %(levelname)s: %(message)s'
        }
    },
    'handlers': {
        'file': {
            'level': reader.log_level,
            'formatter': 'verbose',
            'class': 'logging.handlers.WatchedFileHandler',
            'filename': '/var/log/minv/minv.log',
        },
        'django_file': {
            'level': reader.log_level,
            'class': 'logging.handlers.WatchedFileHandler',
            'filename': '/var/log/minv/django.log',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['django_file'],
            'level': reader.log_level,
            'propagate': True,
        },
        'minv': {
            'handlers': ['file'],
            'level': reader.log_level,
            'propagate': True,
        },
    },
}
