"""Integration tests for ipl/experiments/urls.py"""
import pytest
from django.urls import reverse, resolve


class TestURLPatterns:
    """Test URL patterns resolve correctly."""
    
    def test_index_url_resolves(self):
        """Test index URL resolves."""
        url = reverse('experiments:index')
        assert url == '/experiments/'
    
    def test_information_page_url_resolves(self):
        """Test informationPage URL resolves."""
        test_id = '12345678-1234-1234-1234-123456789abc'
        url = reverse('experiments:informationPage', args=[test_id])
        assert f'{test_id}' in url
        assert url == f'/experiments/{test_id}/information/'
    
    def test_browser_check_url_resolves(self):
        """Test browserCheck URL resolves."""
        test_id = '12345678-1234-1234-1234-123456789abc'
        url = reverse('experiments:browserCheck', args=[test_id])
        assert f'{test_id}' in url
        assert url == f'/experiments/{test_id}/browsercheck/'
    
    def test_consent_form_url_resolves(self):
        """Test consentForm URL resolves."""
        test_id = '12345678-1234-1234-1234-123456789abc'
        url = reverse('experiments:consentForm', args=[test_id])
        assert f'{test_id}' in url
        assert url == f'/experiments/{test_id}/consentform/'
    
    def test_vocab_checklist_url_resolves(self):
        """Test vocabChecklist URL resolves."""
        test_uuid = 'test-uuid-123'
        url = reverse('experiments:vocabChecklist', args=[test_uuid])
        assert test_uuid in url
        assert url == f'/experiments/{test_uuid}/vocab'
