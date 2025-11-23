"""Integration tests for ipl.experiments.urls"""
import pytest
from django.urls import reverse, resolve


def test_index_url_resolves():
    """Test that 'experiments:index' URL name resolves."""
    url = reverse('experiments:index')
    assert url == '/'


def test_information_page_url_resolves():
    """Test that 'experiments:informationPage' URL name resolves."""
    # Use a sample UUID
    experiment_id = '12345678-1234-1234-1234-123456789012'
    url = reverse('experiments:informationPage', args=[experiment_id])
    assert f'/{experiment_id}/information/' in url


def test_browser_check_url_resolves():
    """Test that 'experiments:browserCheck' URL name resolves."""
    experiment_id = '12345678-1234-1234-1234-123456789012'
    url = reverse('experiments:browserCheck', args=[experiment_id])
    assert f'/{experiment_id}/browsercheck/' in url


def test_consent_form_url_resolves():
    """Test that 'experiments:consentForm' URL name resolves."""
    experiment_id = '12345678-1234-1234-1234-123456789012'
    url = reverse('experiments:consentForm', args=[experiment_id])
    assert f'/{experiment_id}/consentform/' in url


def test_subject_form_url_resolves():
    """Test that 'experiments:subjectForm' URL name resolves."""
    experiment_id = '12345678-1234-1234-1234-123456789012'
    url = reverse('experiments:subjectForm', args=[experiment_id])
    assert f'/{experiment_id}/form/' in url


def test_vocab_checklist_url_resolves():
    """Test that 'experiments:vocabChecklist' URL name resolves."""
    run_uuid = '12345678-1234-1234-1234-123456789012'
    url = reverse('experiments:vocabChecklist', args=[run_uuid])
    assert f'/{run_uuid}/vocab' in url


def test_experiment_run_url_resolves():
    """Test that 'experiments:experimentRun' URL name resolves."""
    run_uuid = '12345678-1234-1234-1234-123456789012'
    url = reverse('experiments:experimentRun', args=[run_uuid])
    assert f'/{run_uuid}/run' in url


def test_webcam_test_url_resolves():
    """Test that 'experiments:webcamTest' URL name resolves."""
    run_uuid = '12345678-1234-1234-1234-123456789012'
    url = reverse('experiments:webcamTest', args=[run_uuid])
    assert f'/{run_uuid}/test' in url


def test_experiment_end_url_resolves():
    """Test that 'experiments:experimentEnd' URL name resolves."""
    run_uuid = '12345678-1234-1234-1234-123456789012'
    url = reverse('experiments:experimentEnd', args=[run_uuid])
    assert f'/{run_uuid}/run/thankyou' in url


def test_url_pattern_matching():
    """Test that URL patterns match correctly."""
    # Test that the index URL resolves to the correct view
    match = resolve('/')
    assert match.view_name == 'experiments:index'
    
    # Test that experiment information page resolves
    experiment_id = '12345678-1234-1234-1234-123456789012'
    match = resolve(f'/{experiment_id}/information/')
    assert match.view_name == 'experiments:informationPage'
