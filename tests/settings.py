"""Minimal Django settings for the djangordf test suite."""
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

SECRET_KEY = "test-secret-key-not-for-production"

DEBUG = False

INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.auth",
    "djangordf",
    "tests",
]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

USE_TZ = True

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

DJANGORDF_BACKEND = {
    "class": "djangordf.backends.memory.InMemoryBackend",
}
DJANGORDF_DEFAULT_NAMESPACE = "http://example.org/d/"
DJANGORDF_DEFAULT_GRAPH = "http://example.org/g"

ROOT_URLCONF = "tests.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "APP_DIRS": True,
        "DIRS": [],
        "OPTIONS": {
            "context_processors": [],
        },
    }
]

MIDDLEWARE = [
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
]
