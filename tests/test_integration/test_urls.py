"""Integration tests for URL resolution and routing.

Verifies that all named URL patterns resolve correctly, that UUID parameters
are accepted, and that non-existent IDs produce 404 responses.
"""

import uuid

import pytest
from django.urls import resolve, reverse


# ---------------------------------------------------------------------------
# URL reversing
# ---------------------------------------------------------------------------

class TestUrlReversing:
    def test_index_reverses(self):
        assert reverse("experiments:index") == "/"

    def test_information_page_reverses(self):
        exp_id = uuid.uuid4()
        url = reverse("experiments:informationPage", args=[exp_id])
        assert str(exp_id) in url

    def test_browser_check_reverses(self):
        exp_id = uuid.uuid4()
        url = reverse("experiments:browserCheck", args=[exp_id])
        assert str(exp_id) in url

    def test_consent_form_reverses(self):
        exp_id = uuid.uuid4()
        url = reverse("experiments:consentForm", args=[exp_id])
        assert str(exp_id) in url

    def test_consent_form_submit_reverses(self):
        exp_id = uuid.uuid4()
        url = reverse("experiments:consentFormSubmit", args=[exp_id])
        assert str(exp_id) in url

    def test_subject_form_reverses(self):
        exp_id = uuid.uuid4()
        url = reverse("experiments:subjectForm", args=[exp_id])
        assert str(exp_id) in url

    def test_subject_form_submit_reverses(self):
        exp_id = uuid.uuid4()
        url = reverse("experiments:subjectFormSubmit", args=[exp_id])
        assert str(exp_id) in url

    def test_experiment_run_reverses(self):
        run_uuid = uuid.uuid4()
        url = reverse("experiments:experimentRun", args=[run_uuid])
        assert str(run_uuid) in url

    def test_store_result_reverses(self):
        run_uuid = uuid.uuid4()
        url = reverse("experiments:storeResult", args=[run_uuid])
        assert str(run_uuid) in url

    def test_experiment_end_reverses(self):
        run_uuid = uuid.uuid4()
        url = reverse("experiments:experimentEnd", args=[run_uuid])
        assert str(run_uuid) in url

    def test_experiment_pause_reverses(self):
        run_uuid = uuid.uuid4()
        url = reverse("experiments:experimentPause", args=[run_uuid])
        assert str(run_uuid) in url

    def test_experiment_error_reverses(self):
        run_uuid = uuid.uuid4()
        url = reverse("experiments:experimentError", args=[run_uuid])
        assert str(run_uuid) in url

    def test_delete_subject_reverses(self):
        run_uuid = uuid.uuid4()
        url = reverse("experiments:deleteSubject", args=[run_uuid])
        assert str(run_uuid) in url

    def test_webcam_test_reverses(self):
        run_uuid = uuid.uuid4()
        url = reverse("experiments:webcamTest", args=[run_uuid])
        assert str(run_uuid) in url

    def test_vocab_checklist_reverses(self):
        run_uuid = uuid.uuid4()
        url = reverse("experiments:vocabChecklist", args=[run_uuid])
        assert str(run_uuid) in url

    def test_experiment_report_reverses(self):
        exp_id = uuid.uuid4()
        url = reverse("experiments:experimentReport", args=[exp_id])
        assert str(exp_id) in url

    def test_experiment_export_reverses(self):
        exp_id = uuid.uuid4()
        url = reverse("experiments:experimentExport", args=[exp_id])
        assert str(exp_id) in url

    def test_experiment_import_reverses(self):
        assert reverse("experiments:experimentImport") == "/admin/experiments/import"


# ---------------------------------------------------------------------------
# URL resolution
# ---------------------------------------------------------------------------

class TestUrlResolution:
    def test_index_resolves(self):
        match = resolve("/")
        assert match.url_name == "index"

    def test_information_page_resolves(self):
        exp_id = uuid.uuid4()
        match = resolve(f"/{exp_id}/information/")
        assert match.url_name == "informationPage"
        assert match.kwargs["experiment_id"] == str(exp_id)

    def test_consent_form_resolves(self):
        exp_id = uuid.uuid4()
        match = resolve(f"/{exp_id}/consentform/")
        assert match.url_name == "consentForm"

    def test_subject_form_resolves(self):
        exp_id = uuid.uuid4()
        match = resolve(f"/{exp_id}/form/")
        assert match.url_name == "subjectForm"

    def test_experiment_run_resolves(self):
        run_uuid = uuid.uuid4()
        match = resolve(f"/{run_uuid}/run")
        assert match.url_name == "experimentRun"
        assert match.kwargs["run_uuid"] == str(run_uuid)

    def test_store_result_resolves(self):
        run_uuid = uuid.uuid4()
        match = resolve(f"/{run_uuid}/run/storeresult")
        assert match.url_name == "storeResult"

    def test_experiment_end_resolves(self):
        run_uuid = uuid.uuid4()
        match = resolve(f"/{run_uuid}/run/thankyou")
        assert match.url_name == "experimentEnd"


# ---------------------------------------------------------------------------
# 404 for non-existent IDs (HTTP-level)
# ---------------------------------------------------------------------------

class TestNotFoundRoutes:
    @pytest.mark.django_db
    def test_information_page_nonexistent_uuid_returns_404(self, client):
        response = client.get(f"/{uuid.uuid4()}/information/")
        assert response.status_code == 404

    @pytest.mark.django_db
    def test_consent_form_nonexistent_uuid_returns_404(self, client):
        response = client.get(f"/{uuid.uuid4()}/consentform/")
        assert response.status_code == 404

    @pytest.mark.django_db
    def test_subject_form_nonexistent_uuid_returns_404(self, client):
        response = client.get(f"/{uuid.uuid4()}/form/")
        assert response.status_code == 404

    @pytest.mark.django_db
    def test_experiment_run_nonexistent_uuid_returns_404(self, client):
        response = client.get(f"/{uuid.uuid4()}/run")
        assert response.status_code == 404

    @pytest.mark.django_db
    def test_experiment_end_nonexistent_uuid_returns_404(self, client):
        response = client.get(f"/{uuid.uuid4()}/run/thankyou")
        assert response.status_code == 404

    @pytest.mark.django_db
    def test_experiment_error_nonexistent_uuid_returns_404(self, client):
        response = client.get(f"/{uuid.uuid4()}/run/error")
        assert response.status_code == 404
