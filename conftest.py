"""Root pytest configuration for e-Babylab tests."""
import os
import pytest

# Set environment variables BEFORE Django settings are imported
os.environ.setdefault('SECRET_KEY', 'test-secret-key-for-testing')
os.environ.setdefault('GOOGLE_RECAPTCHA_SITE_KEY', 'test-site-key')
os.environ.setdefault('GOOGLE_RECAPTCHA_SECRET_KEY', 'test-secret-key')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ipl.settings')


@pytest.fixture(scope='session')
def django_db_setup(django_db_blocker):
    """Override database configuration for tests."""
    from django.conf import settings
    
    # Override database settings to use SQLite for tests
    settings.DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': ':memory:',
        }
    }
    
    with django_db_blocker.unblock():
        from django.core.management import call_command
        call_command('migrate', '--run-syncdb')
