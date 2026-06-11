"""Unit tests for experiments/decorators.py.

Covers:
- login_required used as a bare decorator (no parentheses): unauthenticated user is
  redirected; authenticated user reaches the view.
- login_required used as a decorator factory with arguments: unauthenticated user is
  redirected to the login URL with a hardcoded ``next`` value; authenticated user
  reaches the view.
- user_passes_test: custom predicate is evaluated; failing users are redirected.
"""

import pytest
from django.contrib.auth.models import User
from django.test import RequestFactory

from experiments.decorators import login_required, user_passes_test

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_view():
    """Return a trivial view and a sentinel to detect it was called."""
    sentinel = {"called": False}

    def view(request, *args, **kwargs):
        sentinel["called"] = True
        from django.http import HttpResponse

        return HttpResponse("ok")

    return view, sentinel


@pytest.fixture
def factory():
    """Return a Django RequestFactory instance."""
    return RequestFactory()


@pytest.fixture
def auth_user(db):
    """Return an authenticated User fixture."""
    user = User.objects.create_user(username="alice", password="pass")
    user.is_authenticated  # pre-warm
    return user


@pytest.fixture
def anon_user():
    """Return an AnonymousUser instance."""
    from django.contrib.auth.models import AnonymousUser

    return AnonymousUser()


# ---------------------------------------------------------------------------
# login_required — bare decorator (the untested branch)
# ---------------------------------------------------------------------------


class TestLoginRequiredBareDecorator:
    """Tests for login_required applied without parentheses: @login_required."""

    def test_authenticated_user_can_access_view(self, factory, auth_user):
        """Verify authenticated users can access a view protected by login_required."""
        view, sentinel = _make_view()
        protected = login_required(view)  # bare — passes function directly
        request = factory.get("/some/path/")
        request.user = auth_user
        response = protected(request)
        assert response.status_code == 200
        assert sentinel["called"]

    def test_unauthenticated_user_is_redirected(self, factory, anon_user, settings):
        """Verify unauthenticated users are redirected to the login URL."""
        settings.LOGIN_URL = "/accounts/login/"
        view, sentinel = _make_view()
        protected = login_required(view)
        request = factory.get("/some/path/")
        request.user = anon_user
        response = protected(request)
        assert response.status_code == 302
        assert not sentinel["called"]
        assert "/accounts/login/" in response["Location"]


# ---------------------------------------------------------------------------
# login_required — decorator factory with arguments
# ---------------------------------------------------------------------------


class TestLoginRequiredWithArguments:
    """Tests for login_required applied with explicit arguments, e.g. next_url."""

    def test_authenticated_user_can_access_view(self, factory, auth_user):
        """Verify authenticated users can access a view protected by login_required."""
        view, sentinel = _make_view()
        protected = login_required(next_url="/admin/experiments/experiment")(view)
        request = factory.get("/some/path/")
        request.user = auth_user
        response = protected(request)
        assert response.status_code == 200
        assert sentinel["called"]

    def test_unauthenticated_user_redirected_to_hardcoded_next(
        self, factory, anon_user, settings
    ):
        """Verify unauthenticated users are redirected to the hardcoded next_url."""
        settings.LOGIN_URL = "/accounts/login/"
        view, sentinel = _make_view()
        protected = login_required(next_url="/admin/experiments/experiment")(view)
        request = factory.get("/some/path/")
        request.user = anon_user
        response = protected(request)
        assert response.status_code == 302
        assert not sentinel["called"]
        assert "/admin/experiments/experiment" in response["Location"]


# ---------------------------------------------------------------------------
# user_passes_test
# ---------------------------------------------------------------------------


class TestUserPassesTest:
    """Tests for the user_passes_test decorator."""

    def test_passing_predicate_allows_access(self, factory, auth_user):
        """Verify a user satisfying the predicate is granted access."""
        view, sentinel = _make_view()
        protected = user_passes_test(lambda u: True)(view)
        request = factory.get("/")
        request.user = auth_user
        response = protected(request)
        assert response.status_code == 200
        assert sentinel["called"]

    def test_failing_predicate_redirects(self, factory, auth_user, settings):
        """Verify a user failing the predicate is redirected."""
        settings.LOGIN_URL = "/accounts/login/"
        view, sentinel = _make_view()
        protected = user_passes_test(lambda u: False)(view)
        request = factory.get("/")
        request.user = auth_user
        response = protected(request)
        assert response.status_code == 302
        assert not sentinel["called"]
