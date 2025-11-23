"""Unit tests for template_defaults module."""
import pytest


class TestTemplateDefaults:
    """Test template_defaults variables are present and valid."""

    def test_imports_successfully(self):
        """Test template_defaults module can be imported."""
        from experiments import template_defaults
        assert template_defaults is not None

    def test_information_page_content_exists(self):
        """Test information_page_content variable exists and is a string."""
        from experiments.template_defaults import information_page_content
        assert isinstance(information_page_content, str)
        assert len(information_page_content) > 0

    def test_browser_check_page_content_exists(self):
        """Test browser_check_page_content variable exists and is a string."""
        from experiments.template_defaults import browser_check_page_content
        assert isinstance(browser_check_page_content, str)
        assert len(browser_check_page_content) > 0

    def test_introduction_page_content_exists(self):
        """Test introduction_page_content variable exists and is a string."""
        from experiments.template_defaults import introduction_page_content
        assert isinstance(introduction_page_content, str)
        assert len(introduction_page_content) > 0

    def test_consent_fail_page_content_exists(self):
        """Test consent_fail_page_content variable exists and is a string."""
        from experiments.template_defaults import consent_fail_page_content
        assert isinstance(consent_fail_page_content, str)
        assert len(consent_fail_page_content) > 0

    def test_demographic_data_page_content_exists(self):
        """Test demographic_data_page_content variable exists and is a string."""
        from experiments.template_defaults import demographic_data_page_content
        assert isinstance(demographic_data_page_content, str)
        assert len(demographic_data_page_content) > 0

    def test_webcam_check_page_content_exists(self):
        """Test webcam_check_page_content variable exists and is a string."""
        from experiments.template_defaults import webcam_check_page_content
        assert isinstance(webcam_check_page_content, str)
        assert len(webcam_check_page_content) > 0

    def test_microphone_check_page_content_exists(self):
        """Test microphone_check_page_content variable exists and is a string."""
        from experiments.template_defaults import microphone_check_page_content
        assert isinstance(microphone_check_page_content, str)
        assert len(microphone_check_page_content) > 0

    def test_experiment_page_content_exists(self):
        """Test experiment_page_content variable exists and is a string."""
        from experiments.template_defaults import experiment_page_content
        assert isinstance(experiment_page_content, str)
        assert len(experiment_page_content) > 0

    def test_pause_page_content_exists(self):
        """Test pause_page_content variable exists and is a string."""
        from experiments.template_defaults import pause_page_content
        assert isinstance(pause_page_content, str)
        assert len(pause_page_content) > 0

    def test_thank_you_page_content_exists(self):
        """Test thank_you_page_content variable exists and is a string."""
        from experiments.template_defaults import thank_you_page_content
        assert isinstance(thank_you_page_content, str)
        assert len(thank_you_page_content) > 0

    def test_thank_you_abort_page_content_exists(self):
        """Test thank_you_abort_page_content variable exists and is a string."""
        from experiments.template_defaults import thank_you_abort_page_content
        assert isinstance(thank_you_abort_page_content, str)
        assert len(thank_you_abort_page_content) > 0

    def test_error_page_content_exists(self):
        """Test error_page_content variable exists and is a string."""
        from experiments.template_defaults import error_page_content
        assert isinstance(error_page_content, str)
        assert len(error_page_content) > 0

    def test_cdi_page_content_exists(self):
        """Test cdi_page_content variable exists and is a string."""
        from experiments.template_defaults import cdi_page_content
        assert isinstance(cdi_page_content, str)
        assert len(cdi_page_content) > 0
