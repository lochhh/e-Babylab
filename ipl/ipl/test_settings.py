"""Test settings for pytest."""
from ipl.settings import *

# Override database for testing
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
}

# Disable debug for tests
DEBUG = False

# Use a simpler password hasher for faster tests
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.MD5PasswordHasher',
]
