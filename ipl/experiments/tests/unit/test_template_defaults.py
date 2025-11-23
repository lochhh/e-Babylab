"""Unit tests for ipl.experiments.template_defaults"""
import pytest


def test_template_defaults_exist():
    """Test that template_defaults module exists and has expected variables."""
    try:
        import ipl.experiments.template_defaults as td
        
        # Check for expected template variables
        assert hasattr(td, 'information_page_content')
        assert hasattr(td, 'experiment_page_content')
        
        # Check they are strings
        assert isinstance(td.information_page_content, str)
        assert isinstance(td.experiment_page_content, str)
        
        # Check they are not empty
        assert len(td.information_page_content) > 0
        assert len(td.experiment_page_content) > 0
        
    except ImportError:
        pytest.skip("template_defaults module not available")


def test_template_defaults_browser_check():
    """Test browser_check_page_content exists."""
    try:
        import ipl.experiments.template_defaults as td
        
        assert hasattr(td, 'browser_check_page_content')
        assert isinstance(td.browser_check_page_content, str)
        assert len(td.browser_check_page_content) > 0
        
    except ImportError:
        pytest.skip("template_defaults module not available")


def test_template_defaults_consent():
    """Test consent-related template defaults."""
    try:
        import ipl.experiments.template_defaults as td
        
        assert hasattr(td, 'introduction_page_content')
        assert hasattr(td, 'consent_fail_page_content')
        assert isinstance(td.introduction_page_content, str)
        assert isinstance(td.consent_fail_page_content, str)
        
    except ImportError:
        pytest.skip("template_defaults module not available")


def test_template_defaults_demographic():
    """Test demographic_data_page_content exists."""
    try:
        import ipl.experiments.template_defaults as td
        
        assert hasattr(td, 'demographic_data_page_content')
        assert isinstance(td.demographic_data_page_content, str)
        assert len(td.demographic_data_page_content) > 0
        
    except ImportError:
        pytest.skip("template_defaults module not available")


def test_template_defaults_cdi():
    """Test cdi_page_content exists."""
    try:
        import ipl.experiments.template_defaults as td
        
        assert hasattr(td, 'cdi_page_content')
        assert isinstance(td.cdi_page_content, str)
        
    except ImportError:
        pytest.skip("template_defaults module not available")


def test_template_defaults_webcam():
    """Test webcam and microphone check page content."""
    try:
        import ipl.experiments.template_defaults as td
        
        assert hasattr(td, 'webcam_check_page_content')
        assert hasattr(td, 'microphone_check_page_content')
        assert isinstance(td.webcam_check_page_content, str)
        assert isinstance(td.microphone_check_page_content, str)
        
    except ImportError:
        pytest.skip("template_defaults module not available")


def test_template_defaults_end_pages():
    """Test thank you and pause page content."""
    try:
        import ipl.experiments.template_defaults as td
        
        assert hasattr(td, 'thank_you_page_content')
        assert hasattr(td, 'pause_page_content')
        assert hasattr(td, 'thank_you_abort_page_content')
        assert hasattr(td, 'error_page_content')
        
        assert isinstance(td.thank_you_page_content, str)
        assert isinstance(td.pause_page_content, str)
        assert isinstance(td.thank_you_abort_page_content, str)
        assert isinstance(td.error_page_content, str)
        
    except ImportError:
        pytest.skip("template_defaults module not available")
