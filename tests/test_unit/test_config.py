"""Unit tests for config/dashboard.py, config/settings.py, config/urls.py, config/wsgi.py."""

import importlib
import os
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# config/wsgi.py
# ---------------------------------------------------------------------------


class TestWsgi:
    def test_application_is_callable(self):
        """The WSGI application exported by wsgi.py is callable."""
        from config import wsgi

        assert callable(wsgi.application)

    def test_django_settings_module_env_var_is_set(self):
        """wsgi.py ensures DJANGO_SETTINGS_MODULE defaults to config.settings."""
        import config.wsgi  # noqa: F401 – ensure the module is imported

        assert os.environ.get("DJANGO_SETTINGS_MODULE") == "config.settings"


# ---------------------------------------------------------------------------
# config/settings.py
# ---------------------------------------------------------------------------


class TestSettings:
    def test_dev_debug_is_true_by_default(self):
        """Without DJANGO_ENV=prod, DEBUG is True."""
        import config.settings as s

        assert s.DEBUG is True

    def test_prod_branch_sets_debug_false_and_proxy_headers(self, monkeypatch):
        """When DJANGO_ENV=prod, DEBUG is False and reverse-proxy headers are enabled."""
        import config.settings as s

        monkeypatch.setenv("DJANGO_ENV", "prod")
        importlib.reload(s)
        try:
            assert s.DEBUG is False
            assert s.ALLOWED_HOSTS == ["*"]
            assert s.USE_X_FORWARDED_HOST is True
            assert s.SECURE_PROXY_SSL_HEADER == ("HTTP_X_FORWARDED_PROTO", "https")
        finally:
            monkeypatch.delenv("DJANGO_ENV", raising=False)
            importlib.reload(s)

    def test_secret_key_is_non_empty_string(self):
        """SECRET_KEY is always a non-empty string (env var or default)."""
        import config.settings as s

        assert isinstance(s.SECRET_KEY, str)
        assert len(s.SECRET_KEY) > 0

    def test_db_port_is_integer(self):
        """Database PORT is cast to int."""
        import config.settings as s

        assert isinstance(s.DATABASES["default"]["PORT"], int)

    def test_webcam_test_root_is_subdirectory_of_webcam_root(self):
        """WEBCAM_TEST_ROOT is nested inside WEBCAM_ROOT."""
        import config.settings as s

        assert s.WEBCAM_TEST_ROOT.startswith(s.WEBCAM_ROOT)

    def test_static_and_media_roots_under_base_dir(self):
        """STATIC_ROOT, MEDIA_ROOT, and REPORTS_ROOT are all under BASE_DIR."""
        import config.settings as s

        assert s.STATIC_ROOT.startswith(s.BASE_DIR)
        assert s.MEDIA_ROOT.startswith(s.BASE_DIR)
        assert s.REPORTS_ROOT.startswith(s.BASE_DIR)


# ---------------------------------------------------------------------------
# config/dashboard.py
# ---------------------------------------------------------------------------


class TestCustomIndexDashboard:
    def test_init_with_context_appends_correct_modules(self):
        """init_with_context appends four dashboard modules in the expected order."""
        from grappelli.dashboard import modules

        from config.dashboard import CustomIndexDashboard

        dashboard = CustomIndexDashboard()
        context = MagicMock()

        with patch(
            "config.dashboard.get_admin_site_name", return_value="admin"
        ) as mock_get:
            dashboard.init_with_context(context)

        mock_get.assert_called_once_with(context)
        assert len(dashboard.children) == 4
        assert isinstance(dashboard.children[0], modules.RecentActions)
        assert isinstance(dashboard.children[1], modules.ModelList)
        assert isinstance(dashboard.children[2], modules.ModelList)
        assert isinstance(dashboard.children[3], modules.ModelList)


# ---------------------------------------------------------------------------
# config/urls.py
# ---------------------------------------------------------------------------


class TestProtectedServe:
    def test_anonymous_user_is_redirected_to_login(self, rf):
        """An unauthenticated request to protected_serve redirects to login."""
        from django.contrib.auth.models import AnonymousUser

        from config.urls import protected_serve

        request = rf.get("/webcam/test.webm")
        request.user = AnonymousUser()

        response = protected_serve(request, "test.webm", document_root="/tmp")

        assert response.status_code == 302

    @pytest.mark.django_db
    def test_authenticated_user_delegates_to_serve(self, rf, user):
        """An authenticated request to protected_serve calls django.views.static.serve."""
        from django.http import HttpResponse

        from config.urls import protected_serve

        request = rf.get("/webcam/test.webm")
        request.user = user

        mock_response = HttpResponse("ok")
        with patch("config.urls.serve", return_value=mock_response) as mock_serve:
            result = protected_serve(request, "test.webm", document_root="/path")

        mock_serve.assert_called_once_with(request, "test.webm", "/path", False)
        assert result is mock_response
