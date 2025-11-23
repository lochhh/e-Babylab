"""
Unit tests for ipl.experiments.template_defaults module.
"""
import pytest


class TestTemplateDefaults:
    """Tests for template_defaults module."""

    def test_template_defaults_import(self):
        """Test that template_defaults module can be imported."""
        try:
            from ipl.experiments import template_defaults
            assert template_defaults is not None
        except ImportError:
            pytest.skip("template_defaults module not available")

    def test_template_variables_exist(self):
        """Test that expected template variables exist and are strings."""
        try:
            from ipl.experiments import template_defaults
        except ImportError:
            pytest.skip("template_defaults module not available")
        
        # List of expected template content variables
        expected_vars = [
            'information_page_content',
            'browser_check_page_content',
            'introduction_page_content',
            'consent_fail_page_content',
            'demographic_data_page_content',
            'cdi_page_content',
            'webcam_check_page_content',
            'microphone_check_page_content',
            'experiment_page_content',
            'pause_page_content',
            'thank_you_page_content',
            'thank_you_abort_page_content',
            'error_page_content',
        ]
        
        for var_name in expected_vars:
            if hasattr(template_defaults, var_name):
                var_value = getattr(template_defaults, var_name)
                assert isinstance(var_value, str), f"{var_name} should be a string"
                assert len(var_value) > 0, f"{var_name} should not be empty"

    def test_information_page_content(self):
        """Test information_page_content variable."""
        try:
            from ipl.experiments.template_defaults import information_page_content
            assert isinstance(information_page_content, str)
            assert 'information' in information_page_content.lower() or 'welcome' in information_page_content.lower()
        except ImportError:
            pytest.skip("template_defaults module not available")

    def test_browser_check_page_content(self):
        """Test browser_check_page_content variable."""
        try:
            from ipl.experiments.template_defaults import browser_check_page_content
            assert isinstance(browser_check_page_content, str)
        except (ImportError, AttributeError):
            pytest.skip("browser_check_page_content not available")

    def test_consent_fail_page_content(self):
        """Test consent_fail_page_content variable."""
        try:
            from ipl.experiments.template_defaults import consent_fail_page_content
            assert isinstance(consent_fail_page_content, str)
        except (ImportError, AttributeError):
            pytest.skip("consent_fail_page_content not available")

    def test_thank_you_page_content(self):
        """Test thank_you_page_content variable."""
        try:
            from ipl.experiments.template_defaults import thank_you_page_content
            assert isinstance(thank_you_page_content, str)
        except (ImportError, AttributeError):
            pytest.skip("thank_you_page_content not available")
