"""
Root conftest.py for pytest configuration.
"""
import os
import sys


def pytest_configure(config):
    """Configure test settings before running tests."""
    # Set environment variable to use test settings
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ipl.settings')
    os.environ['DJANGO_USE_TEST_DB'] = 'true'
    
    # Import Django and configure
    import django
    from django.conf import settings
    
    # Override database settings for testing
    if not hasattr(settings, 'DATABASES'):
        django.setup()
    
    # Override the databases setting
    settings.DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': ':memory:',
        }
    }
    
    # Ensure media directories don't fail
    settings.MEDIA_ROOT = '/tmp/test_media'
    settings.REPORTS_ROOT = '/tmp/test_reports'
    settings.WEBCAM_ROOT = '/tmp/test_webcam'
    
    # Create directories if needed
    for dir_path in [settings.MEDIA_ROOT, settings.REPORTS_ROOT, settings.WEBCAM_ROOT]:
        os.makedirs(dir_path, exist_ok=True)
