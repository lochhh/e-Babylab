"""
Minimal Django settings for running tests without full dependencies.
"""
import os
import sys

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Use a dummy secret key for testing
SECRET_KEY = 'test-secret-key-for-testing-only'

DEBUG = True
ALLOWED_HOSTS = ['*']

# Minimal INSTALLED_APPS for testing
INSTALLED_APPS = [
    'django.contrib.contenttypes',
    'django.contrib.auth',
    'experiments.apps.ExperimentsConfig',
]

# Database - use SQLite for testing
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
}

# Minimal middleware
MIDDLEWARE = []

ROOT_URLCONF = 'ipl.urls'

# Templates (minimal)
TEMPLATES = []

# Media files
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
MEDIA_URL = '/media/'

# Static files
STATIC_URL = '/static/'

# Reports
REPORTS_ROOT = os.path.join(BASE_DIR, 'reports')
REPORTS_URL = '/reports/'

# Webcam
WEBCAM_ROOT = os.path.join(BASE_DIR, 'webcam')

# Disable migrations for faster testing
class DisableMigrations:
    def __contains__(self, item):
        return True

    def __getitem__(self, item):
        return None

MIGRATION_MODULES = DisableMigrations()

USE_TZ = True
