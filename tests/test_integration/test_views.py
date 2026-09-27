"""Integration tests for individual view responses.

Uses the Django test client to make real HTTP requests against the view layer,
verifying status codes, redirects, rendered content, and database side-effects.
"""

import json

import pytest
from django.test import override_settings
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
# subjectFormSubmit (POST) - Turnstile mocked
# ---------------------------------------------------------------------------


class TestSubjectFormSubmit:
    """Tests for POST requests to the subjectFormSubmit view."""

    @pytest.mark.django_db
    def test_valid_submission_creates_subject_data(
        self, client, simple_experiment, mocker
    ):
        """Verify a valid form submitted with passing Turnstile creates SubjectData."""
        mocker.patch(
            "experiments.captcha.requests.post",
            return_value=mocker.Mock(json=lambda: {"success": True}),
        )
        url = reverse("experiments:subjectFormSubmit", args=[simple_experiment.pk])
        response = client.post(
            url,
            {
                "resolution_w": 1920,
                "resolution_h": 1080,
                "cf-turnstile-response": "token",
            },
        )
        assert response.status_code == 302
        assert (
            exp_models.SubjectData.objects.filter(experiment=simple_experiment).count()
            == 1
        )

    @pytest.mark.django_db
    @override_settings(
        CAPTCHA_PROVIDER="turnstile",
        CLOUDFLARE_TURNSTILE_SITE_KEY="test-site",
        CLOUDFLARE_TURNSTILE_SECRET_KEY="test-secret",
    )
    def test_failed_captcha_does_not_create_subject(
        self, client, simple_experiment, mocker
    ):
        """Verify a failing CAPTCHA prevents SubjectData creation."""
        mocker.patch(
            "experiments.captcha.requests.post",
            return_value=mocker.Mock(json=lambda: {"success": False}),
        )
        url = reverse("experiments:subjectFormSubmit", args=[simple_experiment.pk])
        response = client.post(
            url,
            {
                "resolution_w": 1920,
                "resolution_h": 1080,
                "cf-turnstile-response": "bad",
            },
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
            "experiments.captcha.requests.post",
            return_value=mocker.Mock(json=lambda: {"success": True}),
        )
        url = reverse("experiments:subjectFormSubmit", args=[simple_experiment.pk])
        response = client.post(
            url,
            {"resolution_w": 0, "resolution_h": 0, "cf-turnstile-response": "token"},
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
            "experiments.captcha.requests.post",
            return_value=mocker.Mock(json=lambda: {"success": True}),
        )
        url = reverse("experiments:subjectFormSubmit", args=[simple_experiment.pk])
        client.post(
            url,
            {"resolution_w": 0, "resolution_h": 0, "cf-turnstile-response": "token"},
        )
        client.post(
            url,
            {"resolution_w": 0, "resolution_h": 0, "cf-turnstile-response": "token"},
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
        """Verify the response contains the first pending trial and no upcoming one."""
        exp, listitem, trial = experiment_with_trials
        sd = subjectdata_factory(experiment=exp, listitem=listitem)
        exp.experiment_page_tpl = "{% autoescape off %}{{ trials }}{% endautoescape %}"
        exp.save()
        url = reverse("experiments:experimentRun", args=[sd.pk])
        response = client.get(url)
        assert response.status_code == 200
        payload = json.loads(response.content.decode())
        assert payload["trial"]["label"] == trial.label
        assert payload["upcoming"] is None

    @pytest.mark.django_db
    def test_only_first_trial_returned_for_multi_trial_experiment(
        self,
        client,
        subjectdata_factory,
        trialitem_factory,
        experiment_with_trials,
    ):
        """Verify experimentRun returns the first trial, with the second
        only as upcoming.
        """
        exp, listitem, first_trial = experiment_with_trials
        # Add a second trial to the same block
        block = first_trial.blockitem
        trialitem_factory(blockitem=block, label="Trial2", code="C2", position=2)
        sd = subjectdata_factory(experiment=exp, listitem=listitem)
        exp.experiment_page_tpl = "{% autoescape off %}{{ trials }}{% endautoescape %}"
        exp.save()
        url = reverse("experiments:experimentRun", args=[sd.pk])
        response = client.get(url)
        payload = json.loads(response.content.decode())
        assert payload["trial"]["label"] == first_trial.label
        assert payload["upcoming"]["label"] == "Trial2"

    @pytest.mark.django_db
    def test_completed_trials_excluded(
        self, client, subjectdata_factory, trialresult_factory, experiment_with_trials
    ):
        """Verify experimentRun returns no trial when the only trial is already done."""
        exp, listitem, trial = experiment_with_trials
        sd = subjectdata_factory(experiment=exp, listitem=listitem)
        trialresult_factory(subject=sd, trialitem=trial)
        exp.experiment_page_tpl = "{% autoescape off %}{{ trials }}{% endautoescape %}"
        exp.save()
        url = reverse("experiments:experimentRun", args=[sd.pk])
        response = client.get(url)
        payload = json.loads(response.content.decode())
        assert payload == {"trial": None, "upcoming": None, "videos": []}

    @pytest.mark.django_db
    def test_videos_lists_pending_video_trials(
        self,
        client,
        subjectdata_factory,
        trialitem_factory,
        trialresult_factory,
        filer_file_factory,
        experiment_with_trials,
    ):
        """Verify videos lists every pending video trial, so the page can unlock
        them up front.
        """
        exp, listitem, image_trial = experiment_with_trials
        block = image_trial.blockitem
        image_trial.visual_file = filer_file_factory("picture.jpg")
        image_trial.save()
        done_video = trialitem_factory(
            blockitem=block, label="V1", code="C2", position=2
        )
        pending_video = trialitem_factory(
            blockitem=block, label="V2", code="C3", position=3
        )
        for t, name in [(done_video, "done.mp4"), (pending_video, "pending.webm")]:
            t.visual_file = filer_file_factory(name)
            t.save()
        sd = subjectdata_factory(experiment=exp, listitem=listitem)
        trialresult_factory(subject=sd, trialitem=done_video)
        exp.experiment_page_tpl = "{% autoescape off %}{{ trials }}{% endautoescape %}"
        exp.save()
        url = reverse("experiments:experimentRun", args=[sd.pk])
        payload = json.loads(client.get(url).content.decode())
        assert payload["videos"] == [
            {"trial_id": pending_video.pk, "visual_file": pending_video.visual_file.url}
        ]


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
    def test_get_returns_405(self, client, subjectdata_factory, simple_experiment):
        """Verify a GET request to storeResult returns 405 Method Not Allowed."""
        sd = subjectdata_factory(experiment=simple_experiment)
        url = reverse("experiments:storeResult", args=[sd.pk])
        response = client.get(url)
        assert response.status_code == 405


# ---------------------------------------------------------------------------
# nextTrial
# ---------------------------------------------------------------------------


class TestNextTrial:
    """Tests for the nextTrial view."""

    @pytest.mark.django_db
    def test_get_returns_405(self, client, subjectdata_factory, simple_experiment):
        """Verify a GET request to nextTrial returns 405 Method Not Allowed."""
        sd = subjectdata_factory(experiment=simple_experiment)
        url = reverse("experiments:nextTrial", args=[sd.pk])
        response = client.get(url)
        assert response.status_code == 405

    @pytest.mark.django_db
    def test_returns_first_trial_when_none_completed(
        self, client, subjectdata_factory, experiment_with_trials
    ):
        """Verify nextTrial returns the first pending trial when nothing is complete."""
        exp, listitem, trial = experiment_with_trials
        sd = subjectdata_factory(experiment=exp, listitem=listitem)
        url = reverse("experiments:nextTrial", args=[sd.pk])
        response = client.post(url)
        assert response.status_code == 200
        data = json.loads(response.content)
        assert data["done"] is False
        assert data["trial"]["trial_id"] == trial.pk
        assert data["trial"]["label"] == trial.label

    @pytest.mark.django_db
    def test_returns_second_trial_after_first_completed(
        self,
        client,
        subjectdata_factory,
        trialitem_factory,
        trialresult_factory,
        experiment_with_trials,
    ):
        """Verify nextTrial returns the second trial after the first is stored."""
        exp, listitem, first_trial = experiment_with_trials
        block = first_trial.blockitem
        second_trial = trialitem_factory(
            blockitem=block, label="Trial2", code="C2", position=2
        )
        sd = subjectdata_factory(experiment=exp, listitem=listitem)
        trialresult_factory(subject=sd, trialitem=first_trial)
        url = reverse("experiments:nextTrial", args=[sd.pk])
        response = client.post(url)
        data = json.loads(response.content)
        assert data["done"] is False
        assert data["trial"]["trial_id"] == second_trial.pk
        assert data["upcoming"] is None

    @pytest.mark.django_db
    def test_returns_upcoming_trial_after_next(
        self, client, subjectdata_factory, trialitem_factory, experiment_with_trials
    ):
        """Verify nextTrial returns the trial after the next one as upcoming,
        numbered after it.
        """
        exp, listitem, first_trial = experiment_with_trials
        second_trial = trialitem_factory(
            blockitem=first_trial.blockitem, label="Trial2", code="C2", position=2
        )
        sd = subjectdata_factory(experiment=exp, listitem=listitem)
        url = reverse("experiments:nextTrial", args=[sd.pk])
        data = json.loads(client.post(url).content)
        assert data["trial"]["trial_id"] == first_trial.pk
        assert data["upcoming"]["trial_id"] == second_trial.pk
        assert data["upcoming"]["trial_number"] == 2

    @pytest.mark.django_db
    def test_returns_500_when_trial_lookup_fails(
        self, client, subjectdata_factory, experiment_with_trials
    ):
        """Verify nextTrial reports a JSON error when the subject has
        no list assigned.
        """
        exp, listitem, _ = experiment_with_trials
        sd = subjectdata_factory(experiment=exp, listitem=listitem)
        exp_models.SubjectData.objects.filter(pk=sd.pk).update(listitem=None)
        url = reverse("experiments:nextTrial", args=[sd.pk])
        response = client.post(url)
        assert response.status_code == 500
        assert "error" in json.loads(response.content)

    @pytest.mark.django_db
    def test_returns_done_when_all_trials_complete(
        self, client, subjectdata_factory, trialresult_factory, experiment_with_trials
    ):
        """Verify nextTrial returns done=true when all trials have TrialResults."""
        exp, listitem, trial = experiment_with_trials
        sd = subjectdata_factory(experiment=exp, listitem=listitem)
        trialresult_factory(subject=sd, trialitem=trial)
        url = reverse("experiments:nextTrial", args=[sd.pk])
        response = client.post(url)
        data = json.loads(response.content)
        assert data == {"done": True}

    @pytest.mark.django_db
    def test_pause_result_does_not_count_as_completed(
        self, client, subjectdata_factory, trialresult_factory, experiment_with_trials
    ):
        """Verify PAUSE TrialResults do not exclude the trial from nexttrial."""
        exp, listitem, trial = experiment_with_trials
        sd = subjectdata_factory(experiment=exp, listitem=listitem)
        trialresult_factory(subject=sd, trialitem=trial)
        # Overwrite with PAUSE key
        exp_models.TrialResult.objects.filter(subject=sd).update(key_pressed="PAUSE")
        url = reverse("experiments:nextTrial", args=[sd.pk])
        response = client.post(url)
        data = json.loads(response.content)
        assert data["done"] is False
        assert data["trial"]["trial_id"] == trial.pk

    @pytest.mark.django_db
    def test_trial_number_stable_across_calls(
        self,
        client,
        subjectdata_factory,
        trialitem_factory,
        trialresult_factory,
        experiment_with_trials,
    ):
        """Verify trial_number for a given trial is the same before and
        after another trial completes.
        """
        exp, listitem, first_trial = experiment_with_trials
        block = first_trial.blockitem
        trialitem_factory(blockitem=block, label="Trial2", code="C2", position=2)
        sd = subjectdata_factory(experiment=exp, listitem=listitem)

        # Before completing anything: first trial should have trial_number=1
        url = reverse("experiments:nextTrial", args=[sd.pk])
        data_before = json.loads(client.post(url).content)
        assert data_before["trial"]["trial_number"] == 1

        # Complete the first trial; second trial should have trial_number=2
        trialresult_factory(subject=sd, trialitem=first_trial)
        data_after = json.loads(client.post(url).content)
        assert data_after["trial"]["trial_number"] == 2


# ---------------------------------------------------------------------------
# Attention getter / dwell check
# ---------------------------------------------------------------------------


@pytest.fixture
def dwell_experiment(experiment_with_trials, blockitem_factory, trialitem_factory):
    """EYE experiment: T1 (dwell check 500 ms → AG), T2, and AG in its own block."""
    exp, listitem, trial = experiment_with_trials
    exp.recording_option = "EYE"
    exp.save()
    second = trialitem_factory(
        blockitem=trial.blockitem, label="Trial2", code="C2", position=2
    )
    ag_block = blockitem_factory(
        outerblock=trial.blockitem.outerblockitem, label="AGs", position=2
    )
    ag = trialitem_factory(blockitem=ag_block, label="AG", code="AG")
    ag.is_attention_getter = True
    ag.save()
    trial.attention_getter, trial.min_dwell_time = ag, 500
    trial.save()
    return exp, listitem, trial, second, ag


def _store(sd, trial, dwell_ms, trial_number=1):
    """Store a result whose on-screen gaze totals dwell_ms (multiple of 25)."""
    samples = [{"x": 10, "y": 10, "t": float(t)} for t in range(0, dwell_ms + 1, 25)]
    return exp_models.TrialResult.objects.create(
        subject=sd,
        trialitem=trial,
        trial_number=trial_number,
        key_pressed="",
        resolution_w=100,
        resolution_h=100,
        webgazer_data=samples,
    )


def _next(client, sd):
    return json.loads(
        client.post(reverse("experiments:nextTrial", args=[sd.pk])).content
    )


class TestAttentionGetter:
    """nexttrial shows a trial's attention getter once when dwell is too low."""

    @pytest.mark.django_db
    def test_low_dwell_returns_attention_getter(
        self, client, subjectdata_factory, dwell_experiment
    ):
        """Dwell below threshold → AG with the trial's number, then T2 upcoming."""
        exp, listitem, trial, second, ag = dwell_experiment
        sd = subjectdata_factory(experiment=exp, listitem=listitem)
        _store(sd, trial, 250)
        data = _next(client, sd)
        assert data["trial"]["trial_id"] == ag.pk
        assert data["trial"]["trial_number"] == 1
        assert data["trial"]["is_attention_getter"] is True
        assert data["upcoming"]["trial_id"] == second.pk

    @pytest.mark.django_db
    @pytest.mark.parametrize("dwell_ms", [500, 750])
    def test_enough_dwell_continues_sequence(
        self, client, subjectdata_factory, dwell_experiment, dwell_ms
    ):
        """Dwell at or above threshold → next trial in sequence."""
        exp, listitem, trial, second, _ = dwell_experiment
        sd = subjectdata_factory(experiment=exp, listitem=listitem)
        _store(sd, trial, dwell_ms)
        assert _next(client, sd)["trial"]["trial_id"] == second.pk

    @pytest.mark.django_db
    def test_no_gaze_samples_counts_as_zero_dwell(
        self, client, subjectdata_factory, dwell_experiment
    ):
        """A trial with no gaze samples at all triggers the attention getter."""
        exp, listitem, trial, _, ag = dwell_experiment
        sd = subjectdata_factory(experiment=exp, listitem=listitem)
        result = _store(sd, trial, 0)
        result.webgazer_data = []
        result.save()
        assert _next(client, sd)["trial"]["trial_id"] == ag.pk

    @pytest.mark.django_db
    def test_malformed_gaze_data_does_not_error(
        self, client, subjectdata_factory, dwell_experiment
    ):
        """Garbage webgazer_data is treated as no samples, never a 500."""
        exp, listitem, trial, _, ag = dwell_experiment
        sd = subjectdata_factory(experiment=exp, listitem=listitem)
        result = _store(sd, trial, 0)
        result.webgazer_data = [{"x": "a"}, 5, None]
        result.save()
        assert _next(client, sd)["trial"]["trial_id"] == ag.pk

    @pytest.mark.django_db
    def test_attention_getter_shown_once_then_sequence_continues(
        self, client, subjectdata_factory, dwell_experiment
    ):
        """After the AG's result is stored, the sequence moves on."""
        exp, listitem, trial, second, ag = dwell_experiment
        sd = subjectdata_factory(experiment=exp, listitem=listitem)
        _store(sd, trial, 0)
        _store(sd, ag, 0)
        assert _next(client, sd)["trial"]["trial_id"] == second.pk

    @pytest.mark.django_db
    def test_no_attention_getter_after_final_trial(
        self, client, subjectdata_factory, dwell_experiment
    ):
        """A failed check on the final trial finishes the experiment.

        There is no next trial to regain attention for.
        """
        exp, listitem, trial, second, ag = dwell_experiment
        second.attention_getter, second.min_dwell_time = ag, 500
        second.save()
        sd = subjectdata_factory(experiment=exp, listitem=listitem)
        _store(sd, trial, 500)
        _store(sd, second, 0, trial_number=2)
        assert _next(client, sd) == {"done": True}

    @pytest.mark.django_db
    @pytest.mark.parametrize("recording_option", ["NON", "AUD", "VID"])
    def test_no_check_without_eye_tracking(
        self, client, subjectdata_factory, dwell_experiment, recording_option
    ):
        """Dwell is only checked when the experiment records eye-tracking."""
        exp, listitem, trial, second, _ = dwell_experiment
        exp.recording_option = recording_option
        exp.save()
        sd = subjectdata_factory(experiment=exp, listitem=listitem)
        _store(sd, trial, 0)
        assert _next(client, sd)["trial"]["trial_id"] == second.pk

    @pytest.mark.django_db
    def test_no_check_when_trial_does_not_record_gaze(
        self, client, subjectdata_factory, dwell_experiment
    ):
        """Dwell is only checked for trials with eye-tracking enabled."""
        exp, listitem, trial, second, _ = dwell_experiment
        trial.record_gaze = False
        trial.save()
        sd = subjectdata_factory(experiment=exp, listitem=listitem)
        _store(sd, trial, 0)
        assert _next(client, sd)["trial"]["trial_id"] == second.pk

    @pytest.mark.django_db
    def test_pause_between_trial_and_attention_getter_still_shows_it(
        self, client, subjectdata_factory, dwell_experiment
    ):
        """Resuming after a pause still shows the pending attention getter.

        A PAUSE row is stored when the global timeout fires with the pause page
        enabled — e.g. before or while the attention getter plays. On resume, the
        latest non-PAUSE result is still the failed trial, so its attention getter
        is shown.
        """
        exp, listitem, trial, _, ag = dwell_experiment
        sd = subjectdata_factory(experiment=exp, listitem=listitem)
        _store(sd, trial, 0)
        exp_models.TrialResult.objects.create(
            subject=sd, trialitem=trial, key_pressed="PAUSE", trial_number=2
        )
        assert _next(client, sd)["trial"]["trial_id"] == ag.pk

    @pytest.mark.django_db
    def test_attention_getters_skipped_in_sequence(
        self, client, subjectdata_factory, dwell_experiment
    ):
        """Flagged trials never appear as regular trials."""
        exp, listitem, trial, second, _ = dwell_experiment
        sd = subjectdata_factory(experiment=exp, listitem=listitem)
        _store(sd, trial, 500)
        _store(sd, second, 500, trial_number=2)
        assert _next(client, sd) == {"done": True}

    @pytest.mark.django_db
    def test_attention_getter_shown_at_block_boundary(
        self, client, subjectdata_factory, blockitem_factory, dwell_experiment
    ):
        """A failed check on a block's last trial still shows the AG.

        The block boundary doesn't hide it; ``upcoming`` is the next block's
        first trial. Only the experiment's very last trial skips the AG.
        """
        exp, listitem, trial, second, ag = dwell_experiment
        next_block = blockitem_factory(
            outerblock=trial.blockitem.outerblockitem, label="Next", position=3
        )
        second.blockitem = next_block
        second.save()
        sd = subjectdata_factory(experiment=exp, listitem=listitem)
        _store(sd, trial, 0)
        data = _next(client, sd)
        assert data["trial"]["trial_id"] == ag.pk
        assert data["upcoming"]["trial_id"] == second.pk

    @pytest.mark.django_db
    def test_experiment_run_resumes_with_attention_getter(
        self, client, subjectdata_factory, dwell_experiment
    ):
        """Reloading /run after a failed check starts with the attention getter."""
        exp, listitem, trial, _, ag = dwell_experiment
        exp.experiment_page_tpl = "{% autoescape off %}{{ trials }}{% endautoescape %}"
        exp.save()
        sd = subjectdata_factory(experiment=exp, listitem=listitem)
        _store(sd, trial, 0)
        url = reverse("experiments:experimentRun", args=[sd.pk])
        payload = json.loads(client.get(url).content.decode())
        assert payload["trial"]["trial_id"] == ag.pk

    @pytest.mark.django_db
    def test_experiment_run_videos_include_attention_getters(
        self, client, subjectdata_factory, filer_file_factory, dwell_experiment
    ):
        """AG videos get an element up front so iOS can unlock them."""
        exp, listitem, _, _, ag = dwell_experiment
        ag.visual_file = filer_file_factory("spinner.mp4")
        ag.save()
        exp.experiment_page_tpl = "{% autoescape off %}{{ trials }}{% endautoescape %}"
        exp.save()
        sd = subjectdata_factory(experiment=exp, listitem=listitem)
        url = reverse("experiments:experimentRun", args=[sd.pk])
        payload = json.loads(client.get(url).content.decode())
        assert {"trial_id": ag.pk, "visual_file": ag.visual_file.url} in payload[
            "videos"
        ]

    @pytest.mark.django_db
    @pytest.mark.parametrize(
        "completed,expected",
        [("trials", b"COMPLETE"), ("first_and_ag", b"INCOMPLETE")],
    )
    def test_experiment_end_ignores_attention_getters(
        self, client, subjectdata_factory, dwell_experiment, completed, expected
    ):
        """Completion counts distinct regular trials only; AG results don't count."""
        exp, listitem, trial, second, ag = dwell_experiment
        exp.thank_you_page_tpl, exp.thank_you_abort_page_tpl = "COMPLETE", "INCOMPLETE"
        exp.save()
        sd = subjectdata_factory(experiment=exp, listitem=listitem)
        _store(sd, trial, 500)
        _store(sd, second if completed == "trials" else ag, 500, trial_number=2)
        response = client.get(reverse("experiments:experimentEnd", args=[sd.pk]))
        # equality, not `in`: b"COMPLETE" is a substring of b"INCOMPLETE"
        assert response.content.strip() == expected


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
    def test_get_returns_405(self, client, subjectdata_factory, simple_experiment):
        """Verify a GET request to deleteSubject returns 405 Method Not Allowed."""
        sd = subjectdata_factory(experiment=simple_experiment)
        url = reverse("experiments:deleteSubject", args=[sd.pk])
        response = client.get(url)
        assert response.status_code == 405


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
    def test_export_returns_zip_response(self, client, simple_experiment):
        """Verify the export endpoint returns a ZIP response with the expected keys."""
        import io
        import zipfile as _zipfile

        url = reverse("experiments:experimentExport", args=[simple_experiment.pk])
        response = client.get(url)
        assert response.status_code == 200
        assert response["Content-Type"] == "application/zip"
        with _zipfile.ZipFile(io.BytesIO(response.content)) as zf:
            data = json.loads(zf.read("experiment.json"))
        assert "experiment" in data
        assert "lists" in data

    @pytest.mark.django_db
    def test_export_contains_experiment_name(self, client, simple_experiment):
        """Verify exported ZIP contains the experiment name in experiment.json."""
        import io
        import zipfile as _zipfile

        url = reverse("experiments:experimentExport", args=[simple_experiment.pk])
        response = client.get(url)
        with _zipfile.ZipFile(io.BytesIO(response.content)) as zf:
            data = json.loads(zf.read("experiment.json"))
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
        """Verify that importing a valid ZIP creates a new experiment."""
        from filer.models import Folder

        Folder.objects.get_or_create(name="experiments", parent=None)

        export_url = reverse(
            "experiments:experimentExport", args=[simple_experiment.pk]
        )
        zip_bytes = client.get(export_url).content

        client.force_login(user)

        import_url = reverse("experiments:experimentImport")
        from django.core.files.uploadedfile import SimpleUploadedFile

        uploaded = SimpleUploadedFile(
            "exp.zip", zip_bytes, content_type="application/zip"
        )
        response = client.post(import_url, {"import_file": uploaded})
        assert response.status_code == 302
        # Original name + copy name → total 2 experiments
        assert exp_models.Experiment.objects.count() == 2
        assert exp_models.Experiment.objects.filter(
            exp_name=f"{simple_experiment.exp_name} copy"
        ).exists()
