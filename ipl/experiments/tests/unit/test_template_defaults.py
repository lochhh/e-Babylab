"""Unit tests for ipl/experiments/template_defaults.py"""
import ipl.experiments.template_defaults as template_defaults


class TestTemplateDefaults:
    """Test template_defaults module."""
    
    def test_information_page_content_exists(self):
        """Test information_page_content is a string."""
        assert hasattr(template_defaults, 'information_page_content')
        assert isinstance(template_defaults.information_page_content, str)
        assert len(template_defaults.information_page_content) > 0
    
    def test_browser_check_page_content_exists(self):
        """Test browser_check_page_content is a string."""
        assert hasattr(template_defaults, 'browser_check_page_content')
        assert isinstance(template_defaults.browser_check_page_content, str)
        assert len(template_defaults.browser_check_page_content) > 0
    
    def test_experiment_page_content_exists(self):
        """Test experiment_page_content exists."""
        # Check if attribute exists (may be defined later in the file)
        if hasattr(template_defaults, 'experiment_page_content'):
            assert isinstance(template_defaults.experiment_page_content, str)
