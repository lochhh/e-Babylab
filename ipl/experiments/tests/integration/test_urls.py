"""Integration tests for URL routing."""
import pytest
from django.urls import reverse, resolve


class TestURLRouting:
    """Test URL name resolution."""
    
    def test_index_url_resolves(self):
        """Test that index URL resolves correctly."""
        url = reverse('experiments:index')
        assert url == '/'
        assert resolve(url).view_name == 'experiments:index'
    
    def test_information_page_url_resolves(self):
        """Test that informationPage URL resolves correctly."""
        experiment_id = '12345678-1234-1234-1234-123456789abc'
        url = reverse('experiments:informationPage', args=[experiment_id])
        assert experiment_id in url
        assert resolve(url).view_name == 'experiments:informationPage'
    
    def test_browser_check_url_resolves(self):
        """Test that browserCheck URL resolves correctly."""
        experiment_id = '12345678-1234-1234-1234-123456789abc'
        url = reverse('experiments:browserCheck', args=[experiment_id])
        assert experiment_id in url
        assert resolve(url).view_name == 'experiments:browserCheck'
    
    def test_consent_form_url_resolves(self):
        """Test that consentForm URL resolves correctly."""
        experiment_id = '12345678-1234-1234-1234-123456789abc'
        url = reverse('experiments:consentForm', args=[experiment_id])
        assert experiment_id in url
        assert resolve(url).view_name == 'experiments:consentForm'
    
    def test_subject_form_url_resolves(self):
        """Test that subjectForm URL resolves correctly."""
        experiment_id = '12345678-1234-1234-1234-123456789abc'
        url = reverse('experiments:subjectForm', args=[experiment_id])
        assert experiment_id in url
        assert resolve(url).view_name == 'experiments:subjectForm'
    
    def test_vocab_checklist_url_resolves(self):
        """Test that vocabChecklist URL resolves correctly."""
        run_uuid = 'abcdef1234567890'
        url = reverse('experiments:vocabChecklist', args=[run_uuid])
        assert run_uuid in url
        assert resolve(url).view_name == 'experiments:vocabChecklist'
    
    def test_experiment_run_url_resolves(self):
        """Test that experimentRun URL resolves correctly."""
        run_uuid = 'abcdef1234567890'
        url = reverse('experiments:experimentRun', args=[run_uuid])
        assert run_uuid in url
        assert resolve(url).view_name == 'experiments:experimentRun'
    
    def test_experiment_end_url_resolves(self):
        """Test that experimentEnd URL resolves correctly."""
        run_uuid = 'abcdef1234567890'
        url = reverse('experiments:experimentEnd', args=[run_uuid])
        assert run_uuid in url
        assert resolve(url).view_name == 'experiments:experimentEnd'
    
    def test_experiment_report_url_resolves(self):
        """Test that experimentReport URL resolves correctly."""
        experiment_id = '12345678-1234-1234-1234-123456789abc'
        url = reverse('experiments:experimentReport', args=[experiment_id])
        assert experiment_id in url
        assert resolve(url).view_name == 'experiments:experimentReport'
