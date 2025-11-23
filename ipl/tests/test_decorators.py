"""
Tests for custom decorators.

This module tests:
- Login required decorator
- User passes test decorator
- Redirect behavior
"""
from django.test import TestCase, RequestFactory
from django.contrib.auth.models import AnonymousUser
from django.http import HttpResponse
from experiments.decorators import login_required, user_passes_test
from tests.helpers import UserFactory


class LoginRequiredDecoratorTest(TestCase):
    """Test the login_required decorator."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.factory = RequestFactory()
    
    def test_login_required_authenticated_user(self):
        """Test decorator allows authenticated users."""
        @login_required
        def test_view(request):
            return HttpResponse('Success')
        
        user = UserFactory()
        request = self.factory.get('/test/')
        request.user = user
        
        response = test_view(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content.decode(), 'Success')
    
    def test_login_required_unauthenticated_user(self):
        """Test decorator redirects unauthenticated users."""
        @login_required
        def test_view(request):
            return HttpResponse('Success')
        
        request = self.factory.get('/test/')
        request.user = AnonymousUser()
        
        response = test_view(request)
        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response.url)
    
    def test_login_required_with_next_parameter(self):
        """Test decorator redirects to custom next URL."""
        @login_required(next='/custom/redirect/')
        def test_view(request):
            return HttpResponse('Success')
        
        request = self.factory.get('/test/')
        request.user = AnonymousUser()
        
        response = test_view(request)
        self.assertEqual(response.status_code, 302)
        self.assertIn('/custom/redirect/', response.url)


class UserPassesTestDecoratorTest(TestCase):
    """Test the user_passes_test decorator."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.factory = RequestFactory()
    
    def test_user_passes_test_success(self):
        """Test decorator allows users who pass the test."""
        def is_staff(user):
            return user.is_staff
        
        @user_passes_test(is_staff)
        def test_view(request):
            return HttpResponse('Success')
        
        user = UserFactory(is_staff=True)
        request = self.factory.get('/test/')
        request.user = user
        
        response = test_view(request)
        self.assertEqual(response.status_code, 200)
    
    def test_user_passes_test_failure(self):
        """Test decorator redirects users who fail the test."""
        def is_staff(user):
            return user.is_staff
        
        @user_passes_test(is_staff)
        def test_view(request):
            return HttpResponse('Success')
        
        user = UserFactory(is_staff=False)
        request = self.factory.get('/test/')
        request.user = user
        
        response = test_view(request)
        self.assertEqual(response.status_code, 302)
    
    def test_user_passes_test_anonymous_user(self):
        """Test decorator redirects anonymous users."""
        def is_authenticated(user):
            return user.is_authenticated
        
        @user_passes_test(is_authenticated)
        def test_view(request):
            return HttpResponse('Success')
        
        request = self.factory.get('/test/')
        request.user = AnonymousUser()
        
        response = test_view(request)
        self.assertEqual(response.status_code, 302)
