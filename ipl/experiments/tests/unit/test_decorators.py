"""
Unit tests for the experiments app decorators.

Tests custom decorators for authentication and authorization.
"""

import pytest
from django.contrib.auth.models import AnonymousUser
from django.http import HttpRequest, HttpResponse
from django.test import RequestFactory


class TestLoginRequired:
    """Tests for the login_required decorator."""

    def test_login_required_authenticated_user(self, user):
        """Test that authenticated users can access decorated views."""
        from experiments.decorators import login_required
        
        @login_required
        def view(request):
            return HttpResponse("Success")
        
        factory = RequestFactory()
        request = factory.get("/test/")
        request.user = user
        
        response = view(request)
        assert response.status_code == 200
        assert response.content == b"Success"

    def test_login_required_anonymous_user(self):
        """Test that anonymous users are redirected to login."""
        from experiments.decorators import login_required
        
        @login_required
        def view(request):
            return HttpResponse("Success")
        
        factory = RequestFactory()
        request = factory.get("/test/")
        request.user = AnonymousUser()
        
        response = view(request)
        # Should redirect to login page
        assert response.status_code == 302
        assert "/accounts/login/" in response.url

    def test_login_required_with_next_parameter(self):
        """Test login_required with custom next parameter."""
        from experiments.decorators import login_required
        
        @login_required(next="/custom/next/")
        def view(request):
            return HttpResponse("Success")
        
        factory = RequestFactory()
        request = factory.get("/test/")
        request.user = AnonymousUser()
        
        response = view(request)
        assert response.status_code == 302
        assert "next=" in response.url or "/custom/next/" in response.url


class TestUserPassesTest:
    """Tests for the user_passes_test decorator."""

    def test_user_passes_test_passing(self, user):
        """Test user_passes_test when test passes."""
        from experiments.decorators import user_passes_test
        
        @user_passes_test(lambda u: u.is_authenticated)
        def view(request):
            return HttpResponse("Success")
        
        factory = RequestFactory()
        request = factory.get("/test/")
        request.user = user
        
        response = view(request)
        assert response.status_code == 200

    def test_user_passes_test_failing(self):
        """Test user_passes_test when test fails."""
        from experiments.decorators import user_passes_test
        
        @user_passes_test(lambda u: u.is_superuser)
        def view(request):
            return HttpResponse("Success")
        
        factory = RequestFactory()
        request = factory.get("/test/")
        request.user = AnonymousUser()
        
        response = view(request)
        # Should redirect to login
        assert response.status_code == 302

    def test_user_passes_test_with_custom_test(self, admin_user):
        """Test user_passes_test with custom test function."""
        from experiments.decorators import user_passes_test
        
        @user_passes_test(lambda u: u.is_superuser)
        def view(request):
            return HttpResponse("Admin only")
        
        factory = RequestFactory()
        request = factory.get("/test/")
        request.user = admin_user
        
        response = view(request)
        assert response.status_code == 200
        assert response.content == b"Admin only"
