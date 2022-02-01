"""This file and its contents are licensed under the Apache License 2.0. Please see the included NOTICE for copyright information and LICENSE for a copy of the license.
"""
from pathlib import Path
import os
from dotenv import load_dotenv
from core.settings.base import *

# Load the .env in this directory
ENV_PATH = Path(__file__).parent.resolve() / '.env'
load_env_success = load_dotenv(ENV_PATH, override=True)
print('core.settings.label_studio.py load_env_success:', load_env_success)
print(BASE_DATA_DIR)
# Load defaults from the .env in this directory
DEFAULT_SCALES_LSTUDIO_API_URL = os.getenv('DEFAULT_SCALES_LSTUDIO_API_URL')
DEFAULT_SCALES_LSTUDIO_CONNECTOR_API_URL = os.getenv('DEFAULT_SCALES_LSTUDIO_CONNECTOR_API_URL')

# Grab the following env variables, if specifid in docker-compose will come from there, else defaults
SCALES_LSTUDIO_API_URL = os.getenv('SCALES_LSTUDIO_API_URL', DEFAULT_SCALES_LSTUDIO_API_URL)
SCALES_LSTUDIO_CONNECTOR_API_URL = os.getenv('SCALES_LSTUDIO_CONNECTOR_API_URL', DEFAULT_SCALES_LSTUDIO_API_URL)

DJANGO_DB = get_env('DJANGO_DB', DJANGO_DB_SQLITE)
DATABASES = {'default': DATABASES_ALL[DJANGO_DB]}
print(DATABASES)

MIDDLEWARE.append('organizations.middleware.DummyGetSessionMiddleware')
MIDDLEWARE.append('core.middleware.UpdateLastActivityMiddleware')

ADD_DEFAULT_ML_BACKENDS = False

LOGGING['root']['level'] = get_env('LOG_LEVEL', 'DEBUG')

DEBUG = get_bool_env('DEBUG', False)

DEBUG_PROPAGATE_EXCEPTIONS = get_bool_env('DEBUG_PROPAGATE_EXCEPTIONS', False)

SESSION_COOKIE_SECURE = False

SESSION_ENGINE = "django.contrib.sessions.backends.signed_cookies"

RQ_QUEUES = {}

SENTRY_DSN = get_env(
    'SENTRY_DSN',
    'https://3447a24704fc427fb1d7b057d6da3be6@o227124.ingest.sentry.io/5820521'
)
SENTRY_ENVIRONMENT = get_env('SENTRY_ENVIRONMENT', 'opensource')

FRONTEND_SENTRY_DSN = get_env(
    'FRONTEND_SENTRY_DSN',
    'https://5f51920ff82a4675a495870244869c6b@o227124.ingest.sentry.io/5838868')
FRONTEND_SENTRY_ENVIRONMENT = get_env('FRONTEND_SENTRY_ENVIRONMENT', 'opensource')

from label_studio import __version__
from label_studio.core.utils import sentry
sentry.init_sentry(release_name='label-studio', release_version=__version__)

# we should do it after sentry init
from label_studio.core.utils.common import collect_versions
versions = collect_versions()
