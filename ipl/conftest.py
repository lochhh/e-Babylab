"""Pytest configuration for test database setup."""
import pytest
import os


@pytest.fixture(scope='session')
def django_db_setup():
    """Override database configuration for tests."""
    from django.conf import settings
    
    # Override database settings to use SQLite for tests
    settings.DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': ':memory:',
        }
    }
