"""Integration tests for views."""
import pytest
from django.urls import reverse
from django.test import Client
from unittest.mock import Mock, patch


@pytest.mark.django_db
class TestIndexView:
    """Test index view."""
    
    def test_index_accessible(self, monkeypatch):
        """Test that index view is accessible."""
        # Mock settings.MEDIA_ROOT and render
        from django.conf import settings
        settings.MEDIA_ROOT = '/tmp/media'
        
        # Mock the render function to avoid file system access
        def mock_render(request, template, *args, **kwargs):
            from django.http import HttpResponse
            return HttpResponse('Index page')
        
        monkeypatch.setattr('ipl.experiments.views.render', mock_render)
        
        client = Client()
        response = client.get(reverse('experiments:index'))
        
        assert response.status_code == 200


@pytest.mark.django_db
class TestInformationPageView:
    """Test information page view."""
    
    def test_information_page_existing_experiment(self, experiment_factory):
        """Test information page returns 200 for existing experiment."""
        experiment = experiment_factory(exp_name='Test Exp')
        
        client = Client()
        url = reverse('experiments:informationPage', args=[str(experiment.id)])
        response = client.get(url)
        
        assert response.status_code == 200
    
    def test_information_page_nonexistent_experiment(self):
        """Test information page returns 404 for nonexistent experiment."""
        client = Client()
        url = reverse('experiments:informationPage', args=['00000000-0000-0000-0000-000000000000'])
        response = client.get(url)
        
        assert response.status_code == 404


@pytest.mark.django_db
class TestBrowserCheckView:
    """Test browser check view."""
    
    def test_browser_check_existing_experiment(self, experiment_factory):
        """Test browser check page returns 200 for existing experiment."""
        experiment = experiment_factory(exp_name='Test Exp')
        
        client = Client()
        url = reverse('experiments:browserCheck', args=[str(experiment.id)])
        response = client.get(url)
        
        assert response.status_code == 200
    
    def test_browser_check_nonexistent_experiment(self):
        """Test browser check page returns 404 for nonexistent experiment."""
        client = Client()
        url = reverse('experiments:browserCheck', args=['00000000-0000-0000-0000-000000000000'])
        response = client.get(url)
        
        assert response.status_code == 404


@pytest.mark.django_db
class TestConsentFormView:
    """Test consent form view."""
    
    def test_consent_form_existing_experiment(self, experiment_factory):
        """Test consent form returns 200 for existing experiment."""
        experiment = experiment_factory(exp_name='Test Exp')
        
        client = Client()
        url = reverse('experiments:consentForm', args=[str(experiment.id)])
        response = client.get(url)
        
        assert response.status_code == 200
    
    def test_consent_form_nonexistent_experiment(self):
        """Test consent form returns 404 for nonexistent experiment."""
        client = Client()
        url = reverse('experiments:consentForm', args=['00000000-0000-0000-0000-000000000000'])
        response = client.get(url)
        
        assert response.status_code == 404


@pytest.mark.django_db
class TestSubjectFormView:
    """Test subject form view."""
    
    def test_subject_form_existing_experiment(self, experiment_factory, monkeypatch):
        """Test subject form returns 200 for existing experiment."""
        experiment = experiment_factory(exp_name='Test Exp')
        
        # Mock settings
        from django.conf import settings
        settings.GOOGLE_RECAPTCHA_SITE_KEY = 'test-key'
        
        client = Client()
        url = reverse('experiments:subjectForm', args=[str(experiment.id)])
        response = client.get(url)
        
        assert response.status_code == 200
    
    def test_subject_form_nonexistent_experiment(self):
        """Test subject form returns 404 for nonexistent experiment."""
        client = Client()
        url = reverse('experiments:subjectForm', args=['00000000-0000-0000-0000-000000000000'])
        response = client.get(url)
        
        assert response.status_code == 404
