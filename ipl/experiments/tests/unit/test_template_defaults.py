"""Unit tests for template_defaults.py"""
import pytest


class TestTemplateDefaults:
    """Test template default variables."""
    
    def test_template_defaults_are_strings(self):
        """Test that template variables are strings."""
        from ipl.experiments import template_defaults
        
        # Check that common template variables exist and are strings
        assert hasattr(template_defaults, 'information_page_content')
        assert isinstance(template_defaults.information_page_content, str)
        assert len(template_defaults.information_page_content) > 0
        
        assert hasattr(template_defaults, 'browser_check_page_content')
        assert isinstance(template_defaults.browser_check_page_content, str)
        
        assert hasattr(template_defaults, 'introduction_page_content')
        assert isinstance(template_defaults.introduction_page_content, str)
        
        assert hasattr(template_defaults, 'consent_fail_page_content')
        assert isinstance(template_defaults.consent_fail_page_content, str)
        
        assert hasattr(template_defaults, 'demographic_data_page_content')
        assert isinstance(template_defaults.demographic_data_page_content, str)
        
        assert hasattr(template_defaults, 'cdi_page_content')
        assert isinstance(template_defaults.cdi_page_content, str)
        
        assert hasattr(template_defaults, 'webcam_check_page_content')
        assert isinstance(template_defaults.webcam_check_page_content, str)
        
        assert hasattr(template_defaults, 'microphone_check_page_content')
        assert isinstance(template_defaults.microphone_check_page_content, str)
        
        assert hasattr(template_defaults, 'experiment_page_content')
        assert isinstance(template_defaults.experiment_page_content, str)
        
        assert hasattr(template_defaults, 'pause_page_content')
        assert isinstance(template_defaults.pause_page_content, str)
        
        assert hasattr(template_defaults, 'thank_you_page_content')
        assert isinstance(template_defaults.thank_you_page_content, str)
        
        assert hasattr(template_defaults, 'thank_you_abort_page_content')
        assert isinstance(template_defaults.thank_you_abort_page_content, str)
        
        assert hasattr(template_defaults, 'error_page_content')
        assert isinstance(template_defaults.error_page_content, str)
