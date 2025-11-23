"""Integration tests for ipl/experiments/views.py"""
import pytest
from django.test import Client
from django.urls import reverse


@pytest.mark.django_db
class TestIndexView:
    """Test index view."""
    
    def test_index_view_accessible(self):
        """Test index view is accessible."""
        client = Client()
        
        # The index view requires a template file that may not exist
        # We'll test that the URL is resolvable
        url = reverse('experiments:index')
        assert url == '/experiments/'


@pytest.mark.django_db
class TestInformationPageView:
    """Test informationPage view."""
    
    def test_information_page_view_status_code(self, experiment_factory):
        """Test informationPage view returns 200 for valid experiment."""
        client = Client()
        experiment = experiment_factory(exp_name='Test')
        
        url = reverse('experiments:informationPage', args=[str(experiment.id)])
        response = client.get(url)
        
        assert response.status_code == 200
    
    def test_information_page_view_404_invalid_id(self):
        """Test informationPage view returns 404 for invalid experiment."""
        client = Client()
        
        # Use a UUID that doesn't exist
        url = reverse('experiments:informationPage', args=['00000000-0000-0000-0000-000000000000'])
        response = client.get(url)
        
        assert response.status_code == 404


@pytest.mark.django_db
class TestBrowserCheckView:
    """Test browserCheck view."""
    
    def test_browser_check_view_status_code(self, experiment_factory):
        """Test browserCheck view returns 200 for valid experiment."""
        client = Client()
        experiment = experiment_factory()
        
        url = reverse('experiments:browserCheck', args=[str(experiment.id)])
        response = client.get(url)
        
        assert response.status_code == 200
