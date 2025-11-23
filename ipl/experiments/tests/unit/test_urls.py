"""
Unit tests for the experiments app URLs.

Tests URL patterns, reverse lookups, and view mapping.
"""

import uuid

import pytest
from django.urls import resolve, reverse


class TestExperimentUrls:
    """Tests for experiment URLs."""

    def test_information_page_url(self):
        """Test information page URL pattern."""
        experiment_id = uuid.uuid4()
        url = reverse("experiments:informationPage", args=[experiment_id])
        assert url == f"/{experiment_id}/information/"
        
        # Test that URL resolves to correct view
        resolved = resolve(url)
        assert resolved.view_name == "experiments:informationPage"

    def test_browser_check_url(self):
        """Test browser check URL pattern."""
        experiment_id = uuid.uuid4()
        url = reverse("experiments:browserCheck", args=[experiment_id])
        assert url == f"/{experiment_id}/browsercheck/"

    def test_consent_form_url(self):
        """Test consent form URL pattern."""
        experiment_id = uuid.uuid4()
        url = reverse("experiments:consentForm", args=[experiment_id])
        assert url == f"/{experiment_id}/consentform/"

    def test_consent_form_submit_url(self):
        """Test consent form submit URL pattern."""
        experiment_id = uuid.uuid4()
        url = reverse("experiments:consentFormSubmit", args=[experiment_id])
        assert url == f"/{experiment_id}/consentform/submit"

    def test_subject_form_url(self):
        """Test subject form URL pattern."""
        experiment_id = uuid.uuid4()
        url = reverse("experiments:subjectForm", args=[experiment_id])
        assert url == f"/{experiment_id}/form/"

    def test_subject_form_submit_url(self):
        """Test subject form submit URL pattern."""
        experiment_id = uuid.uuid4()
        url = reverse("experiments:subjectFormSubmit", args=[experiment_id])
        assert url == f"/{experiment_id}/form/submit"

    def test_experiment_run_url(self):
        """Test experiment run URL pattern."""
        run_uuid = uuid.uuid4()
        url = reverse("experiments:experimentRun", args=[run_uuid])
        assert url == f"/{run_uuid}/run"

    def test_store_result_url(self):
        """Test store result URL pattern."""
        run_uuid = uuid.uuid4()
        url = reverse("experiments:storeResult", args=[run_uuid])
        assert url == f"/{run_uuid}/run/storeresult"

    def test_experiment_pause_url(self):
        """Test experiment pause URL pattern."""
        run_uuid = uuid.uuid4()
        url = reverse("experiments:experimentPause", args=[run_uuid])
        assert url == f"/{run_uuid}/run/pause"

    def test_experiment_end_url(self):
        """Test experiment end URL pattern."""
        run_uuid = uuid.uuid4()
        url = reverse("experiments:experimentEnd", args=[run_uuid])
        assert url == f"/{run_uuid}/run/thankyou"

    def test_delete_subject_url(self):
        """Test delete subject URL pattern."""
        run_uuid = uuid.uuid4()
        url = reverse("experiments:deleteSubject", args=[run_uuid])
        assert url == f"/{run_uuid}/run/deletesubject"

    def test_experiment_error_url(self):
        """Test experiment error URL pattern."""
        run_uuid = uuid.uuid4()
        url = reverse("experiments:experimentError", args=[run_uuid])
        assert url == f"/{run_uuid}/run/error"

    def test_index_url(self):
        """Test index URL pattern."""
        url = reverse("experiments:index")
        assert url == "/"

    def test_webcam_test_url(self):
        """Test webcam test URL pattern."""
        run_uuid = uuid.uuid4()
        url = reverse("experiments:webcamTest", args=[run_uuid])
        assert url == f"/{run_uuid}/test"

    def test_webcam_upload_url(self):
        """Test webcam upload URL pattern."""
        run_uuid = uuid.uuid4()
        url = reverse("experiments:experimentWebcamUpload", args=[run_uuid])
        assert url == f"/{run_uuid}/run/upload"

    def test_vocab_checklist_url(self):
        """Test vocab checklist (CDI) URL pattern."""
        run_uuid = uuid.uuid4()
        url = reverse("experiments:vocabChecklist", args=[run_uuid])
        assert url == f"/{run_uuid}/vocab"

    def test_vocab_checklist_submit_url(self):
        """Test vocab checklist submit URL pattern."""
        run_uuid = uuid.uuid4()
        url = reverse("experiments:vocabChecklistSubmit", args=[run_uuid])
        assert url == f"/{run_uuid}/vocab/submit"
