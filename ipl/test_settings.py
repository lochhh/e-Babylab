"""
Test settings for pytest.

This file inherits from the main settings file and overrides database configuration
to use SQLite for testing.
"""
from ipl.settings import *

# Override database for testing
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
}

# Override media directories for testing
import os
import tempfile

TEST_TMP_DIR = tempfile.mkdtemp(prefix='e-babylab-test-')
MEDIA_ROOT = os.path.join(TEST_TMP_DIR, 'media')
REPORTS_ROOT = os.path.join(TEST_TMP_DIR, 'reports')
WEBCAM_ROOT = os.path.join(TEST_TMP_DIR, 'webcam')

# Create directories
for dir_path in [MEDIA_ROOT, REPORTS_ROOT, WEBCAM_ROOT]:
    os.makedirs(dir_path, exist_ok=True)

# Disable debug for tests
DEBUG = False
