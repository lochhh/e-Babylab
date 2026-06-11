"""Integration tests for individual view responses.

Uses the Django test client to make real HTTP requests against the view layer,
verifying status codes, redirects, rendered content, and database side-effects.
"""

import json

import pytest
from django.urls import reverse

from experiments import models as exp_models

# ---------------------------------------------------------------------------
# informationPage
# ---------------------------------------------------------------------------


class TestInformationPage:
    """Tests for the informationPage view."""

    @pytest.mark.django_db
    def test_returns_200_for_existing_experiment(self, client, simple_experiment):
        """Verify the information page returns 200 for a valid experiment."""
        url = reverse("experiments:informationPage", args=[simple_experiment.pk])
        response = client.get(url)
        assert response.status_code == 200

    @pytest.mark.django_db
    def test_renders_template_content(self, client, experiment_factory):
        """Verify the information page renders the experiment name from the template."""
        exp = experiment_factory()
        exp.information_page_tpl = "<h1>Welcome to {{ experiment.exp_name }}</h1>"
        exp.save()
        url = reverse("experiments:informationPage", args=[exp.pk])
        response = client.get(url)
        assert b"Welcome to" in response.content
        assert exp.exp_name.encode() in response.content


# ---------------------------------------------------------------------------
# browserCheck
# ---------------------------------------------------------------------------


class TestBrowserCheck:
    """Tests for the browserCheck view."""

    @pytest.mark.django_db
    def test_returns_200(self, client, simple_experiment):
        """Verify the browser check page returns 200 for a valid experiment."""
        url = reverse("experiments:browserCheck", args=[simple_experiment.pk])
        response = client.get(url)
        assert response.status_code == 200


# ---------------------------------------------------------------------------
# consentForm (GET)
# ---------------------------------------------------------------------------


class TestConsentFormGet:
    """Tests for GET requests to the consentForm view."""

    @pytest.mark.django_db
    def test_returns_200_without_questions(self, client, simple_experiment):
        """Verify the consent form returns 200 when no consent questions exist."""
        url = reverse("experiments:consentForm", args=[simple_experiment.pk])
        response = client.get(url)
        assert response.status_code == 200

    @pytest.mark.django_db
    def test_renders_consent_question_text(
        self, client, simple_experiment, consent_question_factory
    ):
        """Verify consent question text appears in the rendered consent form page."""
        q = consent_question_factory(text="Do you agree?", experiment=simple_experiment)
        url = reverse("experiments:consentForm", args=[simple_experiment.pk])
        # Render the introduction template with the question text
        simple_experiment.introduction_page_tpl = (
            "{% for field in consent_form %}{{ field.label }}{% endfor %}"
        )
        simple_experiment.save()
        response = client.get(url)
        assert q.text.encode() in response.content


# ---------------------------------------------------------------------------
# consentFormSubmit (POST)
# ---------------------------------------------------------------------------


class TestConsentFormSubmit:
    """Tests for POST requests to the consentFormSubmit view."""

    @pytest.mark.django_db
    def test_all_yes_redirects_to_subject_form(
        self, client, simple_experiment, consent_question_factory
    ):
        """Verify answering all questions yes redirects to the subject form."""
        q = consent_question_factory(experiment=simple_experiment)
        url = reverse("experiments:consentFormSubmit", args=[simple_experiment.pk])
        response = client.post(url, {f"question_{q.pk}": "yes"})
        assert response.status_code == 302
        assert (
            reverse("experiments:subjectForm", args=[simple_experiment.pk])
            in response["Location"]
        )

    @pytest.mark.django_db
    def test_any_no_renders_consent_fail(
        self, client, experiment_factory, consent_question_factory
    ):
        """Verify answering any question no renders the consent fail page."""
        exp = experiment_factory()
        for field in [
            "introduction_page_tpl",
            "consent_fail_page_tpl",
            "information_page_tpl",
            "browser_check_page_tpl",
            "demographic_data_page_tpl",
            "cdi_page_tpl",
            "webcam_check_page_tpl",
            "microphone_check_page_tpl",
            "experiment_page_tpl",
            "pause_page_tpl",
            "thank_you_page_tpl",
            "thank_you_abort_page_tpl",
            "error_page_tpl",
        ]:
            setattr(exp, field, "OK")
        exp.consent_fail_page_tpl = "CONSENT_FAILED"
        exp.save()
        q = consent_question_factory(experiment=exp)
        url = reverse("experiments:consentFormSubmit", args=[exp.pk])
        response = client.post(url, {f"question_{q.pk}": "no"})
        assert response.status_code == 200
        assert b"CONSENT_FAILED" in response.content

    @pytest.mark.django_db
    def test_no_questions_redirects_to_subject_form(self, client, simple_experiment):
        """Verify submitting with no consent questions redirects to the subject form."""
        url = reverse("experiments:consentFormSubmit", args=[simple_experiment.pk])
        response = client.post(url, {})
        assert response.status_code == 302
        assert (
            reverse("experiments:subjectForm", args=[simple_experiment.pk])
            in response["Location"]
        )


# ---------------------------------------------------------------------------
# subjectForm (GET)
# ---------------------------------------------------------------------------


class TestSubjectFormGet:
    """Tests for GET requests to the subjectForm view."""

    @pytest.mark.django_db
    def test_returns_200_without_questions(self, client, simple_experiment):
        """Verify the subject form returns 200 when no demographic questions exist."""
        url = reverse("experiments:subjectForm", args=[simple_experiment.pk])
        response = client.get(url)
        assert response.status_code == 200

    @pytest.mark.django_db
    def test_renders_question_text(self, client, experiment_factory, question_factory):
        """Verify demographic question appears in the rendered subject form page."""
        exp = experiment_factory()
        for field in [
            "information_page_tpl",
            "browser_check_page_tpl",
            "introduction_page_tpl",
            "consent_fail_page_tpl",
            "cdi_page_tpl",
            "webcam_check_page_tpl",
            "microphone_check_page_tpl",
            "experiment_page_tpl",
            "pause_page_tpl",
            "thank_you_page_tpl",
            "thank_you_abort_page_tpl",
            "error_page_tpl",
        ]:
            setattr(exp, field, "OK")
        exp.demographic_data_page_tpl = (
            "{% for field in subject_data_form %}{{ field.label }}{% endfor %}"
        )
        exp.save()
        q = question_factory(text="What is your name?", experiment=exp)
        url = reverse("experiments:subjectForm", args=[exp.pk])
        response = client.get(url)
        assert q.text.encode() in response.content


# ---------------------------------------------------------------------------
# subjectFormSubmit (POST) - reCAPTCHA mocked
# ---------------------------------------------------------------------------


class TestSubjectFormSubmit:
    """Tests for POST requests to the subjectFormSubmit view."""

    @pytest.mark.django_db
    def test_valid_submission_creates_subject_data(
        self, client, simple_experiment, mocker
    ):
        """Verify a valid form submitted with passing reCAPTCHA creates SubjectData."""
        mocker.patch(
            "experiments.views.requests.post",
            return_value=mocker.Mock(json=lambda: {"success": True}),
        )
        url = reverse("experiments:subjectFormSubmit", args=[simple_experiment.pk])
        response = client.post(
            url,
            {
                "resolution_w": 1920,
                "resolution_h": 1080,
                "g-recaptcha-response": "token",
            },
        )
        assert response.status_code == 302
        assert (
            exp_models.SubjectData.objects.filter(experiment=simple_experiment).count()
            == 1
        )

    @pytest.mark.django_db
    def test_failed_recaptcha_does_not_create_subject(
        self, client, simple_experiment, mocker
    ):
        """Verify a failing reCAPTCHA prevents SubjectData creation."""
        mocker.patch(
            "experiments.views.requests.post",
            return_value=mocker.Mock(json=lambda: {"success": False}),
        )
        url = reverse("experiments:subjectFormSubmit", args=[simple_experiment.pk])
        response = client.post(
            url,
            {"resolution_w": 1920, "resolution_h": 1080, "g-recaptcha-response": "bad"},
        )
        assert response.status_code == 200
        assert (
            exp_models.SubjectData.objects.filter(experiment=simple_experiment).count()
            == 0
        )

    @pytest.mark.django_db
    def test_valid_submission_redirects_to_experiment_run_when_no_instrument(
        self, client, simple_experiment, mocker
    ):
        """Verify a successful submission without CDI redirects to run."""
        mocker.patch(
            "experiments.views.requests.post",
            return_value=mocker.Mock(json=lambda: {"success": True}),
        )
        url = reverse("experiments:subjectFormSubmit", args=[simple_experiment.pk])
        response = client.post(
            url, {"resolution_w": 0, "resolution_h": 0, "g-recaptcha-response": "token"}
        )
        # NON recording → direct to experimentRun
        assert response.status_code == 302
        assert "/run" in response["Location"]

    @pytest.mark.django_db
    def test_participant_ids_increment_across_submissions(
        self, client, simple_experiment, mocker
    ):
        """Verify subject IDs are assigned sequentially across multiple submissions."""
        mocker.patch(
            "experiments.views.requests.post",
            return_value=mocker.Mock(json=lambda: {"success": True}),
        )
        url = reverse("experiments:subjectFormSubmit", args=[simple_experiment.pk])
        client.post(
            url, {"resolution_w": 0, "resolution_h": 0, "g-recaptcha-response": "token"}
        )
        client.post(
            url, {"resolution_w": 0, "resolution_h": 0, "g-recaptcha-response": "token"}
        )
        ids = list(
            exp_models.SubjectData.objects.filter(experiment=simple_experiment)
            .order_by("participant_id")
            .values_list("participant_id", flat=True)
        )
        assert ids == [1, 2]


# ---------------------------------------------------------------------------
# experimentRun
# ---------------------------------------------------------------------------


class TestExperimentRun:
    """Tests for the experimentRun view."""

    @pytest.mark.django_db
    def test_returns_200_with_subject_data(
        self, client, subjectdata_factory, simple_experiment
    ):
        """Verify the experiment run page returns 200 for a valid subject."""
        sd = subjectdata_factory(experiment=simple_experiment)
        url = reverse("experiments:experimentRun", args=[sd.pk])
        response = client.get(url)
        assert response.status_code == 200

    @pytest.mark.django_db
    def test_trial_json_included_in_response(
        self, client, subjectdata_factory, experiment_with_trials
    ):
        """Verify the response contains serialised trial data for the assigned list."""
        exp, listitem, trial = experiment_with_trials
        sd = subjectdata_factory(experiment=exp, listitem=listitem)
        exp.experiment_page_tpl = "{% autoescape off %}{{ trials }}{% endautoescape %}"
        exp.save()
        url = reverse("experiments:experimentRun", args=[sd.pk])
        response = client.get(url)
        assert response.status_code == 200
        content = response.content.decode()
        trials = json.loads(content)
        assert len(trials) == 1
        assert trials[0]["label"] == trial.label

    @pytest.mark.django_db
    def test_completed_trials_excluded(
        self, client, subjectdata_factory, trialresult_factory, experiment_with_trials
    ):
        """Verify trials with existing TrialResult records are excluded from the run."""
        exp, listitem, trial = experiment_with_trials
        sd = subjectdata_factory(experiment=exp, listitem=listitem)
        trialresult_factory(subject=sd, trialitem=trial)
        exp.experiment_page_tpl = "{% autoescape off %}{{ trials }}{% endautoescape %}"
        exp.save()
        url = reverse("experiments:experimentRun", args=[sd.pk])
        response = client.get(url)
        trials = json.loads(response.content.decode())
        assert trials == []


# ---------------------------------------------------------------------------
# storeResult
# ---------------------------------------------------------------------------


class TestStoreResult:
    """Tests for the storeResult view."""

    @pytest.mark.django_db
    def test_post_creates_trial_result(
        self, client, subjectdata_factory, trialitem_factory, simple_experiment
    ):
        """Verify a POST to storeResult creates a TrialResult and returns a resultId."""
        sd = subjectdata_factory(experiment=simple_experiment)
        trial = trialitem_factory()
        url = reverse("experiments:storeResult", args=[sd.pk])
        response = client.post(
            url,
            {
                "trialitem": trial.pk,
                "start_time": 100.0,
                "end_time": 200.0,
                "key_pressed": "a",
                "trial_number": 1,
                "resolution_w": 1920,
                "resolution_h": 1080,
                "webgazer_data": "[]",
            },
        )
        assert response.status_code == 200
        data = json.loads(response.content)
        assert "resultId" in data
        assert (
            exp_models.TrialResult.objects.filter(subject=sd, trialitem=trial).count()
            == 1
        )

    @pytest.mark.django_db
    def test_get_returns_404(self, client, subjectdata_factory, simple_experiment):
        """Verify a GET request to storeResult returns 404."""
        sd = subjectdata_factory(experiment=simple_experiment)
        url = reverse("experiments:storeResult", args=[sd.pk])
        response = client.get(url)
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# experimentEnd (thank you page)
# ---------------------------------------------------------------------------


class TestExperimentEnd:
    """Tests for the experimentEnd (thank you) view."""

    @pytest.mark.django_db
    def test_returns_200(self, client, subjectdata_factory, simple_experiment):
        """Verify the experiment end page returns 200 for a valid subject."""
        sd = subjectdata_factory(experiment=simple_experiment)
        url = reverse("experiments:experimentEnd", args=[sd.pk])
        response = client.get(url)
        assert response.status_code == 200

    @pytest.mark.django_db
    def test_renders_abort_template_when_incomplete(
        self, client, subjectdata_factory, experiment_with_trials
    ):
        """Verify the abort template is shown when not all trials are completed."""
        exp, listitem, _trial = experiment_with_trials
        # abort template distinguishable from normal end template
        exp.thank_you_page_tpl = "COMPLETE"
        exp.thank_you_abort_page_tpl = "INCOMPLETE"
        exp.save()
        sd = subjectdata_factory(experiment=exp, listitem=listitem)
        # no TrialResults → 0/1 completed → abort page
        url = reverse("experiments:experimentEnd", args=[sd.pk])
        response = client.get(url)
        assert b"INCOMPLETE" in response.content

    @pytest.mark.django_db
    def test_renders_standard_template_when_complete(
        self, client, subjectdata_factory, trialresult_factory, experiment_with_trials
    ):
        """Verify the standard thank-you page is shown when all trials are completed."""
        exp, listitem, trial = experiment_with_trials
        exp.thank_you_page_tpl = "COMPLETE"
        exp.thank_you_abort_page_tpl = "INCOMPLETE"
        exp.save()
        sd = subjectdata_factory(experiment=exp, listitem=listitem)
        trialresult_factory(subject=sd, trialitem=trial)
        url = reverse("experiments:experimentEnd", args=[sd.pk])
        response = client.get(url)
        assert b"COMPLETE" in response.content


# ---------------------------------------------------------------------------
# deleteSubject
# ---------------------------------------------------------------------------


class TestDeleteSubject:
    """Tests for the deleteSubject view."""

    @pytest.mark.django_db
    def test_post_deletes_subject_data(
        self, client, subjectdata_factory, simple_experiment
    ):
        """Verify a POST to deleteSubject removes the SubjectData and returns 204."""
        sd = subjectdata_factory(experiment=simple_experiment)
        pk = sd.pk
        url = reverse("experiments:deleteSubject", args=[pk])
        response = client.post(url)
        assert response.status_code == 204
        assert not exp_models.SubjectData.objects.filter(pk=pk).exists()

    @pytest.mark.django_db
    def test_get_returns_404(self, client, subjectdata_factory, simple_experiment):
        """Verify a GET request to deleteSubject returns 404."""
        sd = subjectdata_factory(experiment=simple_experiment)
        url = reverse("experiments:deleteSubject", args=[sd.pk])
        response = client.get(url)
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# experimentPause
# ---------------------------------------------------------------------------


class TestExperimentPause:
    """Tests for the experimentPause view."""

    @pytest.mark.django_db
    def test_get_returns_200(self, client, subjectdata_factory, simple_experiment):
        """Verify the pause page returns 200 for a valid subject."""
        sd = subjectdata_factory(experiment=simple_experiment)
        url = reverse("experiments:experimentPause", args=[sd.pk])
        response = client.get(url)
        assert response.status_code == 200

    @pytest.mark.django_db
    def test_post_stores_pause_result_after_first_trial(
        self, client, subjectdata_factory, trialresult_factory, experiment_with_trials
    ):
        """Verify POSTing to the pause view creates a PAUSE TrialResult record."""
        exp, listitem, trial = experiment_with_trials
        sd = subjectdata_factory(experiment=exp, listitem=listitem)
        trialresult_factory(subject=sd, trialitem=trial)
        url = reverse("experiments:experimentPause", args=[sd.pk])
        client.post(url, {"trialitem": trial.pk})
        pause_results = exp_models.TrialResult.objects.filter(
            subject=sd, key_pressed="PAUSE"
        )
        assert pause_results.count() == 1


# ---------------------------------------------------------------------------
# experimentReport (login-required)
# ---------------------------------------------------------------------------


class TestExperimentReport:
    """Tests for the experimentReport view (login-required)."""

    @pytest.mark.django_db
    def test_unauthenticated_redirects_to_login(self, client, simple_experiment):
        """Verify an unauthenticated request to the report view redirects to login."""
        url = reverse("experiments:experimentReport", args=[simple_experiment.pk])
        response = client.get(url)
        assert response.status_code == 302
        assert "/admin" in response["Location"] or "login" in response["Location"]


# ---------------------------------------------------------------------------
# experimentExport / experimentImport
# ---------------------------------------------------------------------------


class TestExperimentExport:
    """Tests for the experimentExport view."""

    @pytest.mark.django_db
    def test_export_returns_json_response(self, client, simple_experiment):
        """Verify the export endpoint returns a JSON response with the expected keys."""
        url = reverse("experiments:experimentExport", args=[simple_experiment.pk])
        response = client.get(url)
        assert response.status_code == 200
        assert response["Content-Type"] == "application/json"
        data = json.loads(response.content)
        assert "experiment" in data
        assert "lists" in data

    @pytest.mark.django_db
    def test_export_contains_experiment_name(self, client, simple_experiment):
        """Verify exported JSON contains the experiment name in the experiment key."""
        url = reverse("experiments:experimentExport", args=[simple_experiment.pk])
        response = client.get(url)
        data = json.loads(response.content)
        exp_names = [e["fields"]["exp_name"] for e in data["experiment"]]
        assert simple_experiment.exp_name in exp_names


class TestExperimentImport:
    """Tests for the experimentImport view."""

    @pytest.mark.django_db
    def test_get_import_page_returns_200(self, client):
        """Verify the import page returns 200 for a GET request."""
        url = reverse("experiments:experimentImport")
        response = client.get(url)
        assert response.status_code == 200

    @pytest.mark.django_db
    def test_import_creates_new_experiment(self, client, user, simple_experiment):
        """Verify that importing a valid JSON file creates a new experiment."""
        # Export the experiment first
        export_url = reverse(
            "experiments:experimentExport", args=[simple_experiment.pk]
        )
        export_response = client.get(export_url)
        json_bytes = export_response.content

        # Authenticate as the owner before importing
        client.force_login(user)

        import_url = reverse("experiments:experimentImport")
        from django.core.files.uploadedfile import SimpleUploadedFile

        uploaded = SimpleUploadedFile(
            "exp.json", json_bytes, content_type="application/json"
        )
        response = client.post(import_url, {"import_file": uploaded})
        # Should redirect after successful import
        assert response.status_code == 302
        # A new experiment with the same name should exist (original + import)
        assert (
            exp_models.Experiment.objects.filter(
                exp_name=simple_experiment.exp_name
            ).count()
            == 2
        )
