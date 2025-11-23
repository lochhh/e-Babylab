"""Integration tests for experiments URLs."""
import pytest
from django.urls import reverse, resolve


class TestURLPatterns:
    """Test URL patterns are configured correctly."""
    
    def test_index_url_resolves(self):
        """Test that index URL resolves correctly."""
        url = reverse('experiments:index')
        assert url == '/'
        assert resolve(url).view_name == 'experiments:index'
    
    def test_information_page_url_resolves(self):
        """Test that information page URL resolves correctly."""
        import uuid
        test_id = uuid.uuid4()
        url = reverse('experiments:informationPage', args=[test_id])
        assert str(test_id) in url
        assert resolve(url).view_name == 'experiments:informationPage'
    
    def test_browser_check_url_resolves(self):
        """Test that browser check URL resolves correctly."""
        import uuid
        test_id = uuid.uuid4()
        url = reverse('experiments:browserCheck', args=[test_id])
        assert str(test_id) in url
        assert resolve(url).view_name == 'experiments:browserCheck'
    
    def test_consent_form_url_resolves(self):
        """Test that consent form URL resolves correctly."""
        import uuid
        test_id = uuid.uuid4()
        url = reverse('experiments:consentForm', args=[test_id])
        assert str(test_id) in url
        assert resolve(url).view_name == 'experiments:consentForm'
    
    def test_subject_form_url_resolves(self):
        """Test that subject form URL resolves correctly."""
        import uuid
        test_id = uuid.uuid4()
        url = reverse('experiments:subjectForm', args=[test_id])
        assert str(test_id) in url
        assert resolve(url).view_name == 'experiments:subjectForm'
