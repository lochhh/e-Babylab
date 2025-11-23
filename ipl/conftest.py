"""
Pytest configuration for the entire project.

Sets environment variables for testing.
"""

import os


def pytest_configure():
    """Configure environment for testing."""
    os.environ['DJANGO_TEST_DATABASE'] = 'sqlite'
