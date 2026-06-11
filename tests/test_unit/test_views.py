"""Unit tests for experiments/views.py.

Covers: proceedToExperiment, createTrialDict, experimentReport, experimentExport,
        experimentImport, informationPage, browserCheck, consentForm,
        consentFormSubmit, subjectForm, subjectFormSubmit, experimentRun,
        storeResult, experimentPause, experimentError, experimentEnd,
        deleteSubject, index.
"""

import json
import uuid

import pytest
from django.urls import reverse

from experiments import models as exp_models
from experiments.views import createTrialDict, proceedToExperiment

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SIMPLE_TPL = "OK"


def _simple_experiment(experiment_factory, **kwargs):
    """Create an experiment with all template fields set to a trivial string."""
    exp = experiment_factory(**kwargs)
    for field in [
        "information_page_tpl",
        "browser_check_page_tpl",
        "introduction_page_tpl",
        "consent_fail_page_tpl",
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
        setattr(exp, field, SIMPLE_TPL)
    exp.save()
    return exp


def _mock_trial(
    visual_file=None,
    audio_file=None,
    response_keys="a,b",
    user_input="NO",
    record_media=True,
    record_gaze=True,
    is_calibration=False,
    calibration_points=None,
    label="T1",
    visual_onset=0,
    audio_onset=0,
    max_duration=1000,
    tid=1,
):
    from unittest.mock import MagicMock

    trial = MagicMock()
    trial.id = tid
    trial.visual_file = visual_file
    trial.audio_file = audio_file
    trial.response_keys = response_keys
    trial.user_input = user_input
    trial.record_media = record_media
    trial.record_gaze = record_gaze
    trial.is_calibration = is_calibration
    trial.calibration_points = calibration_points or []
    trial.label = label
    trial.visual_onset = visual_onset
    trial.audio_onset = audio_onset
    trial.max_duration = max_duration
    return trial


def _mock_block(background_colour="#FFFFFF"):
    from unittest.mock import MagicMock

    block = MagicMock()
    block.background_colour = background_colour
    return block


# ---------------------------------------------------------------------------
# proceedToExperiment
# ---------------------------------------------------------------------------


class TestProceedToExperiment:
    """Tests for the proceedToExperiment helper function."""

    @pytest.mark.parametrize("recording_option", ["NON", "EYE"])
    def test_non_or_eye_redirects_to_experiment_run(self, recording_option):
        """Verify NON and EYE recording options redirect to experimentRun."""
        from unittest.mock import MagicMock

        experiment = MagicMock(recording_option=recording_option)
        run_uuid = str(uuid.uuid4())
        response = proceedToExperiment(experiment, run_uuid)
        assert response.status_code == 302
        assert response["Location"] == reverse(
            "experiments:experimentRun", args=(run_uuid,)
        )

    @pytest.mark.parametrize("recording_option", ["AUD", "VID", "ALL"])
    def test_audio_video_all_redirects_to_webcam_test(self, recording_option):
        """Verify AUD, VID, and ALL recording options redirect to webcamTest."""
        from unittest.mock import MagicMock

        experiment = MagicMock(recording_option=recording_option)
        run_uuid = str(uuid.uuid4())
        response = proceedToExperiment(experiment, run_uuid)
        assert response.status_code == 302
        assert response["Location"] == reverse(
            "experiments:webcamTest", args=(run_uuid,)
        )


# ---------------------------------------------------------------------------
# createTrialDict
# ---------------------------------------------------------------------------


class TestCreateTrialDict:
    """Tests for the createTrialDict helper function."""

    def test_no_media_files_returns_empty_strings_and_blank_type(self):
        """Verify empty strings and blank trial_type when no media files are set."""
        result = createTrialDict(
            _mock_trial(visual_file=None, audio_file=None), _mock_block(), 1
        )
        assert result["visual_file"] == ""
        assert result["audio_file"] == ""
        assert result["trial_type"] == ""

    def test_video_visual_file_sets_type_and_url(self):
        """Verify .mp4 visual file sets trial_type to video and includes the URL."""
        from unittest.mock import MagicMock

        vf = MagicMock(url="/media/clip.mp4", original_filename="clip.mp4")
        result = createTrialDict(_mock_trial(visual_file=vf), _mock_block(), 1)
        assert result["visual_file"] == "/media/clip.mp4"
        assert result["trial_type"] == "video"

    def test_image_visual_file_sets_type_and_url(self):
        """Verify .png visual file sets trial_type to image and includes the URL."""
        from unittest.mock import MagicMock

        vf = MagicMock(url="/media/img.png", original_filename="img.png")
        result = createTrialDict(_mock_trial(visual_file=vf), _mock_block(), 1)
        assert result["visual_file"] == "/media/img.png"
        assert result["trial_type"] == "image"

    def test_audio_file_sets_url(self):
        """Verify an audio file URL is included in the trial dict."""
        from unittest.mock import MagicMock

        af = MagicMock(url="/media/sound.mp3")
        result = createTrialDict(_mock_trial(audio_file=af), _mock_block(), 1)
        assert result["audio_file"] == "/media/sound.mp3"

    def test_response_keys_parsed_to_lowercase_stripped_list(self):
        """Verify response_keys are lowercased and stripped into a list."""
        result = createTrialDict(
            _mock_trial(response_keys="Left, Right"), _mock_block(), 1
        )
        assert result["response_keys"] == ["left", "right"]

    def test_null_response_keys_defaults_to_list_with_empty_string(self):
        """Verify null response_keys produces a list with a single empty string."""
        result = createTrialDict(_mock_trial(response_keys=None), _mock_block(), 1)
        assert result["response_keys"] == [""]

    def test_calibration_points_included_when_is_calibration(self):
        """Verify calibration_points are included when is_calibration is True."""
        result = createTrialDict(
            _mock_trial(is_calibration=True, calibration_points=[[50, 50]]),
            _mock_block(),
            1,
        )
        assert result["is_calibration"] is True
        assert result["calibration_points"] == [[50, 50]]

    def test_calibration_points_empty_when_not_calibration(self):
        """Verify calibration_points is empty when is_calibration is False."""
        result = createTrialDict(
            _mock_trial(is_calibration=False, calibration_points=[[50, 50]]),
            _mock_block(),
            1,
        )
        assert result["is_calibration"] is False
        assert result["calibration_points"] == []

    def test_trial_id_and_number_set_correctly(self):
        """Verify trial_id and trial_number are set from the trial and its position."""
        result = createTrialDict(_mock_trial(tid=42), _mock_block(), 7)
        assert result["trial_id"] == 42
        assert result["trial_number"] == 7

    def test_background_colour_comes_from_block(self):
        """Verify background_colour is taken from the block, not the trial."""
        result = createTrialDict(
            _mock_trial(), _mock_block(background_colour="#123456"), 1
        )
        assert result["background_colour"] == "#123456"

    def test_all_expected_keys_present(self):
        """Verify all expected keys are present in the returned trial dict."""
        result = createTrialDict(_mock_trial(), _mock_block(), 1)
        expected_keys = {
            "trial_id",
            "trial_number",
            "background_colour",
            "label",
            "visual_onset",
            "audio_onset",
            "audio_file",
            "visual_file",
            "max_duration",
            "response_keys",
            "require_user_input",
            "trial_type",
            "record_media",
            "record_gaze",
            "is_calibration",
            "calibration_points",
        }
        assert expected_keys == set(result.keys())


# ---------------------------------------------------------------------------
# experimentReport
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestExperimentReport:
    """Tests for the experimentReport view."""

    def test_unauthenticated_redirects_to_login(self, client, experiment_factory):
        """Verify unauthenticated experimentReport requests are redirected to login."""
        exp = _simple_experiment(experiment_factory)
        url = reverse("experiments:experimentReport", args=(str(exp.pk),))
        response = client.get(url)
        assert response.status_code == 302
        assert (
            "login" in response["Location"].lower()
            or "accounts" in response["Location"].lower()
        )

    def test_authenticated_creates_report_and_redirects(
        self, client, user, experiment_factory, mocker
    ):
        """Verify an authenticated request triggers report creation and redirects."""
        exp = _simple_experiment(experiment_factory)
        client.force_login(user)
        mock_reporter = mocker.patch("experiments.views.Reporter")
        mock_reporter.return_value.create_report.return_value = "/reports/report.zip"
        mock_fs = mocker.patch("experiments.views.FileSystemStorage")
        mock_fs.return_value.url.return_value = "/reports/report.zip"
        url = reverse("experiments:experimentReport", args=(str(exp.pk),))
        response = client.get(url)
        assert response.status_code == 302
        mock_reporter.return_value.create_report.assert_called_once()

    def test_returns_404_for_nonexistent_experiment(self, client, user):
        """Verify a 404 is returned for a report request on a nonexistent experiment."""
        client.force_login(user)
        url = reverse("experiments:experimentReport", args=(str(uuid.uuid4()),))
        response = client.get(url)
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# experimentExport
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestExperimentExport:
    """Tests for the experimentExport view."""

    def test_returns_json_response(self, client, experiment_factory):
        """Verify the export view returns a JSON response with status 200."""
        exp = _simple_experiment(experiment_factory)
        url = reverse("experiments:experimentExport", args=(str(exp.pk),))
        response = client.get(url)
        assert response.status_code == 200
        assert response["Content-Type"] == "application/json"

    def test_content_disposition_contains_experiment_name(
        self, client, experiment_factory
    ):
        """Verify the Content-Disposition header includes the experiment name."""
        exp = _simple_experiment(experiment_factory, exp_name="MyExperiment")
        url = reverse("experiments:experimentExport", args=(str(exp.pk),))
        response = client.get(url)
        assert "MyExperiment" in response["Content-Disposition"]
        assert "attachment" in response["Content-Disposition"]

    def test_exported_json_contains_experiment_key(self, client, experiment_factory):
        """Verify the exported JSON contains the experiment and lists keys."""
        exp = _simple_experiment(experiment_factory)
        url = reverse("experiments:experimentExport", args=(str(exp.pk),))
        response = client.get(url)
        data = json.loads(response.content)
        assert "experiment" in data
        assert "lists" in data


# ---------------------------------------------------------------------------
# experimentImport
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestExperimentImport:
    """Tests for the experimentImport view."""

    def test_get_renders_import_form(self, client):
        """Verify a GET to the import view returns status 200."""
        url = reverse("experiments:experimentImport")
        response = client.get(url)
        assert response.status_code == 200

    def test_post_with_invalid_form_rerenders_page(self, client):
        """Verify a POST with no file re-renders the import page with status 200."""
        url = reverse("experiments:experimentImport")
        response = client.post(url, {})
        assert response.status_code == 200

    def test_post_with_valid_file_calls_import_and_redirects(
        self, client, user, experiment_factory, mocker
    ):
        """Verify a POST with a valid JSON file calls importFromJSON and redirects."""
        exp = _simple_experiment(experiment_factory)
        mock_import = mocker.patch("experiments.views.ExperimentAdmin.importFromJSON")
        url = reverse("experiments:experimentImport")
        from django.core.files.uploadedfile import SimpleUploadedFile

        json_content = json.dumps({"experiment": [], "lists": []}).encode()
        file_obj = SimpleUploadedFile(
            "exp.json", json_content, content_type="application/json"
        )
        response = client.post(url, {"import_file": file_obj})
        assert response.status_code == 302
        assert "/admin/experiments/experiment" in response["Location"]
        mock_import.assert_called_once()


# ---------------------------------------------------------------------------
# informationPage
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestInformationPage:
    """Tests for the informationPage view."""

    def test_returns_200_for_valid_experiment(self, client, experiment_factory):
        """Verify the information page returns 200 for a valid experiment."""
        exp = _simple_experiment(experiment_factory)
        url = reverse("experiments:informationPage", args=(str(exp.pk),))
        response = client.get(url)
        assert response.status_code == 200
        assert b"OK" in response.content

    def test_returns_404_for_nonexistent_experiment(self, client):
        """Verify a 404 is returned for an unknown experiment UUID."""
        url = reverse("experiments:informationPage", args=(str(uuid.uuid4()),))
        response = client.get(url)
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# browserCheck
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestBrowserCheck:
    """Tests for the browserCheck view."""

    def test_returns_200_for_valid_experiment(self, client, experiment_factory):
        """Verify the browser check page returns 200 for a valid experiment."""
        exp = _simple_experiment(experiment_factory)
        url = reverse("experiments:browserCheck", args=(str(exp.pk),))
        response = client.get(url)
        assert response.status_code == 200

    def test_returns_404_for_nonexistent_experiment(self, client):
        """Verify a 404 is returned for an unknown experiment UUID."""
        url = reverse("experiments:browserCheck", args=(str(uuid.uuid4()),))
        response = client.get(url)
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# consentForm
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestConsentForm:
    """Tests for the consentForm view."""

    def test_returns_200_for_valid_experiment(self, client, experiment_factory):
        """Verify the consent form returns 200 for a valid experiment."""
        exp = _simple_experiment(experiment_factory)
        url = reverse("experiments:consentForm", args=(str(exp.pk),))
        response = client.get(url)
        assert response.status_code == 200

    def test_returns_404_for_nonexistent_experiment(self, client):
        """Verify a 404 is returned for an unknown experiment UUID."""
        url = reverse("experiments:consentForm", args=(str(uuid.uuid4()),))
        response = client.get(url)
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# consentFormSubmit
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestConsentFormSubmit:
    """Tests for the consentFormSubmit view."""

    def test_all_yes_answers_redirect_to_subject_form(
        self, client, experiment_factory, consent_question_factory
    ):
        """Verify answering all questions yes redirects to the subject form."""
        exp = _simple_experiment(experiment_factory)
        cq = consent_question_factory(experiment=exp)
        url = reverse("experiments:consentFormSubmit", args=(str(exp.pk),))
        response = client.post(url, {f"question_{cq.pk}": "yes"})
        assert response.status_code == 302
        assert (
            reverse("experiments:subjectForm", args=(str(exp.pk),))
            in response["Location"]
        )

    def test_no_answer_renders_consent_fail_page(
        self, client, experiment_factory, consent_question_factory
    ):
        """Verify answering any question no renders the consent fail template."""
        exp = _simple_experiment(experiment_factory)
        exp.consent_fail_page_tpl = "CONSENT_FAIL"
        exp.save()
        cq = consent_question_factory(experiment=exp)
        url = reverse("experiments:consentFormSubmit", args=(str(exp.pk),))
        response = client.post(url, {f"question_{cq.pk}": "no"})
        assert response.status_code == 200
        assert b"CONSENT_FAIL" in response.content

    def test_no_consent_questions_redirects_to_subject_form(
        self, client, experiment_factory
    ):
        """Verify submitting with no consent questions redirects to the subject form."""
        exp = _simple_experiment(experiment_factory)
        url = reverse("experiments:consentFormSubmit", args=(str(exp.pk),))
        response = client.post(url, {})
        assert response.status_code == 302
        assert (
            reverse("experiments:subjectForm", args=(str(exp.pk),))
            in response["Location"]
        )

    def test_invalid_form_missing_required_answer_rerenders_intro_page(
        self, client, experiment_factory, consent_question_factory
    ):
        """Verify a missing required answer re-renders the intro page."""
        exp = _simple_experiment(experiment_factory)
        exp.introduction_page_tpl = "INTRO_PAGE"
        exp.save()
        # Create a consent question (ChoiceField is required by default)
        consent_question_factory(experiment=exp)
        url = reverse("experiments:consentFormSubmit", args=(str(exp.pk),))
        # POST without any answer → form is invalid
        response = client.post(url, {})
        assert response.status_code == 200
        assert b"INTRO_PAGE" in response.content

    def test_returns_404_for_nonexistent_experiment(self, client):
        """Verify a 404 is returned for an unknown experiment UUID."""
        url = reverse("experiments:consentFormSubmit", args=(str(uuid.uuid4()),))
        response = client.post(url, {})
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# subjectForm
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestSubjectForm:
    """Tests for the subjectForm view."""

    def test_returns_200_for_valid_experiment(self, client, experiment_factory):
        """Verify the subject form returns 200 for a valid experiment."""
        exp = _simple_experiment(experiment_factory)
        url = reverse("experiments:subjectForm", args=(str(exp.pk),))
        response = client.get(url)
        assert response.status_code == 200

    def test_returns_404_for_nonexistent_experiment(self, client):
        """Verify a 404 is returned for an unknown experiment UUID."""
        url = reverse("experiments:subjectForm", args=(str(uuid.uuid4()),))
        response = client.get(url)
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# subjectFormSubmit
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestSubjectFormSubmit:
    """Tests for the subjectFormSubmit view."""

    def _url(self, exp):
        """Return the subjectFormSubmit URL for the given experiment."""
        return reverse("experiments:subjectFormSubmit", args=(str(exp.pk),))

    def _base_post_data(self, extra=None):
        """Return a base POST dict with resolution and reCAPTCHA fields."""
        data = {
            "resolution_w": "1920",
            "resolution_h": "1080",
            "g-recaptcha-response": "test-token",
        }
        if extra:
            data.update(extra)
        return data

    def test_valid_form_recaptcha_success_no_instrument_redirects(
        self, client, experiment_factory, mocker
    ):
        """Verify a valid reCAPTCHA submission redirects to the experiment run."""
        exp = _simple_experiment(experiment_factory)
        mock_post = mocker.patch("experiments.views.requests.post")
        mock_post.return_value.json.return_value = {"success": True}
        response = client.post(self._url(exp), self._base_post_data())
        assert response.status_code == 302
        location = response["Location"]
        # recording_option is NON by default → experimentRun
        assert "run" in location

    def test_valid_form_recaptcha_success_with_instrument_redirects_to_cdi(
        self, client, experiment_factory, instrument_factory, mocker
    ):
        """Verify a valid submission with an instrument redirects to the CDI page."""
        exp = _simple_experiment(experiment_factory)
        exp.instrument = instrument_factory()
        exp.save()
        mock_post = mocker.patch("experiments.views.requests.post")
        mock_post.return_value.json.return_value = {"success": True}
        response = client.post(self._url(exp), self._base_post_data())
        assert response.status_code == 302
        assert "vocab" in response["Location"]

    def test_recaptcha_failure_renders_demographic_page(
        self, client, experiment_factory, mocker
    ):
        """Verify a failing reCAPTCHA re-renders the demographic page."""
        exp = _simple_experiment(experiment_factory)
        exp.demographic_data_page_tpl = "DEMOG_PAGE"
        exp.save()
        mock_post = mocker.patch("experiments.views.requests.post")
        mock_post.return_value.json.return_value = {"success": False}
        response = client.post(self._url(exp), self._base_post_data())
        assert response.status_code == 200
        assert b"DEMOG_PAGE" in response.content

    def test_invalid_form_rerenders_demographic_page(
        self, client, experiment_factory, question_factory
    ):
        """Verify a missing required field re-renders the demographic page."""
        exp = _simple_experiment(experiment_factory)
        exp.demographic_data_page_tpl = "DEMOG_FORM"
        exp.save()
        question_factory(
            experiment=exp,
            question_type=exp_models.Question.TEXT,
            required=True,
        )
        # POST without the required question answer → form invalid
        response = client.post(
            self._url(exp),
            {"resolution_w": "0", "resolution_h": "0"},
        )
        assert response.status_code == 200
        assert b"DEMOG_FORM" in response.content

    def test_returns_404_for_nonexistent_experiment(self, client):
        """Verify a 404 is returned for an unknown experiment UUID."""
        url = reverse("experiments:subjectFormSubmit", args=(str(uuid.uuid4()),))
        response = client.post(url, {"resolution_w": "0", "resolution_h": "0"})
        assert response.status_code == 404

    def test_valid_form_creates_subject_data_record(
        self, client, experiment_factory, mocker
    ):
        """Verify a valid submission creates a SubjectData record in the database."""
        exp = _simple_experiment(experiment_factory)
        mock_post = mocker.patch("experiments.views.requests.post")
        mock_post.return_value.json.return_value = {"success": True}
        assert exp_models.SubjectData.objects.filter(experiment=exp).count() == 0
        client.post(self._url(exp), self._base_post_data())
        assert exp_models.SubjectData.objects.filter(experiment=exp).count() == 1


# ---------------------------------------------------------------------------
# experimentRun
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestExperimentRun:
    """Tests for the experimentRun view."""

    def _setup(
        self,
        experiment_factory,
        listitem_factory,
        outerblock_factory,
        blockitem_factory,
        trialitem_factory,
        subjectdata_factory,
    ):
        """Build a minimal experiment+subject fixture and return (exp, listitem, sd)."""
        exp = _simple_experiment(experiment_factory)
        li = listitem_factory(experiment=exp)
        ob = outerblock_factory(listitem=li)
        bi = blockitem_factory(outerblock=ob)
        trialitem_factory(blockitem=bi)
        sd = subjectdata_factory(experiment=exp, listitem=li)
        return exp, li, sd

    def test_returns_200_for_valid_subject(
        self,
        client,
        experiment_factory,
        listitem_factory,
        outerblock_factory,
        blockitem_factory,
        trialitem_factory,
        subjectdata_factory,
    ):
        """Verify the experiment run page returns 200 for a valid subject."""
        _, _, sd = self._setup(
            experiment_factory,
            listitem_factory,
            outerblock_factory,
            blockitem_factory,
            trialitem_factory,
            subjectdata_factory,
        )
        response = client.get(reverse("experiments:experimentRun", args=(sd.pk,)))
        assert response.status_code == 200

    def test_response_contains_trials_json(
        self,
        client,
        experiment_factory,
        listitem_factory,
        outerblock_factory,
        blockitem_factory,
        trialitem_factory,
        subjectdata_factory,
    ):
        """Verify the response includes serialised trial JSON in the page content."""
        exp = _simple_experiment(experiment_factory)
        # Use a template that renders the trials context variable
        exp.experiment_page_tpl = "{{ trials }}"
        exp.save()
        li = listitem_factory(experiment=exp)
        ob = outerblock_factory(listitem=li)
        bi = blockitem_factory(outerblock=ob)
        trialitem_factory(blockitem=bi)
        sd = subjectdata_factory(experiment=exp, listitem=li)
        response = client.get(reverse("experiments:experimentRun", args=(sd.pk,)))
        assert response.status_code == 200
        # The view serialises trials to JSON and injects it into the template context
        assert b"trial_id" in response.content

    def test_returns_404_for_nonexistent_subject(self, client):
        """Verify a 404 is returned for an unknown run UUID."""
        url = reverse("experiments:experimentRun", args=(str(uuid.uuid4()),))
        response = client.get(url)
        assert response.status_code == 404

    def test_assigns_list_item_when_subject_has_none(
        self,
        client,
        experiment_factory,
        listitem_factory,
        outerblock_factory,
        blockitem_factory,
        trialitem_factory,
    ):
        """Verify a list item is assigned on first run when the subject has none."""
        exp = _simple_experiment(experiment_factory)
        li = listitem_factory(experiment=exp)
        ob = outerblock_factory(listitem=li)
        bi = blockitem_factory(outerblock=ob)
        trialitem_factory(blockitem=bi)
        # Create SubjectData with no listitem directly
        sd = exp_models.SubjectData.objects.create(
            id=str(uuid.uuid4()), experiment=exp, participant_id=1
        )
        assert sd.listitem is None
        response = client.get(reverse("experiments:experimentRun", args=(sd.pk,)))
        assert response.status_code == 200
        sd.refresh_from_db()
        assert sd.listitem is not None

    def test_redirects_to_error_when_experiment_has_no_lists(
        self, client, experiment_factory
    ):
        """Verify a redirect to experimentError when no list items exist."""
        exp = _simple_experiment(experiment_factory)
        # Subject with no listitem and experiment has no list items
        sd = exp_models.SubjectData.objects.create(
            id=str(uuid.uuid4()), experiment=exp, participant_id=1
        )
        response = client.get(reverse("experiments:experimentRun", args=(sd.pk,)))
        assert response.status_code == 302
        assert (
            reverse("experiments:experimentError", args=(sd.pk,))
            in response["Location"]
        )

    def test_skips_completed_trials(
        self,
        client,
        experiment_factory,
        listitem_factory,
        outerblock_factory,
        blockitem_factory,
        trialitem_factory,
        subjectdata_factory,
        trialresult_factory,
    ):
        """Verify already-completed trials are excluded from the run response."""
        exp = _simple_experiment(experiment_factory)
        exp.experiment_page_tpl = "{{ trials }}"
        exp.save()
        li = listitem_factory(experiment=exp)
        ob = outerblock_factory(listitem=li)
        bi = blockitem_factory(outerblock=ob)
        ti = trialitem_factory(blockitem=bi)
        sd = subjectdata_factory(experiment=exp, listitem=li)
        # Mark trial as already completed
        trialresult_factory(subject=sd, trialitem=ti)
        response = client.get(reverse("experiments:experimentRun", args=(sd.pk,)))
        assert response.status_code == 200
        # The completed trial should not appear in the rendered trials list
        trials = json.loads(response.content.decode())
        assert all(t["trial_id"] != ti.pk for t in trials)

    def test_randomised_inner_blocks_does_not_crash(
        self,
        client,
        experiment_factory,
        listitem_factory,
        outerblock_factory,
        blockitem_factory,
        trialitem_factory,
        subjectdata_factory,
    ):
        """Verify randomised inner blocks do not cause an error during run."""
        exp = _simple_experiment(experiment_factory)
        li = listitem_factory(experiment=exp)
        ob = exp_models.OuterBlockItem.objects.create(
            listitem=li, outer_block_name="OB", position=1, randomise_inner_blocks=True
        )
        bi = blockitem_factory(outerblock=ob)
        trialitem_factory(blockitem=bi)
        sd = subjectdata_factory(experiment=exp, listitem=li)
        response = client.get(reverse("experiments:experimentRun", args=(sd.pk,)))
        assert response.status_code == 200

    def test_randomised_trials_within_block_does_not_crash(
        self,
        client,
        experiment_factory,
        listitem_factory,
        outerblock_factory,
        subjectdata_factory,
        trialitem_factory,
    ):
        """Verify randomised trials within a block do not cause an error during run."""
        exp = _simple_experiment(experiment_factory)
        li = listitem_factory(experiment=exp)
        ob = outerblock_factory(listitem=li)
        bi = exp_models.BlockItem.objects.create(
            outerblockitem=ob, label="RandomBlock", position=1, randomise_trials=True
        )
        trialitem_factory(blockitem=bi, position=1)
        trialitem_factory(blockitem=bi, label="Trial2", code="C2", position=2)
        sd = subjectdata_factory(experiment=exp, listitem=li)
        response = client.get(reverse("experiments:experimentRun", args=(sd.pk,)))
        assert response.status_code == 200


# ---------------------------------------------------------------------------
# storeResult
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestStoreResult:
    """Tests for the storeResult view."""

    def _post_data(self, trial_item):
        """Return a valid POST payload for storeResult with the given trial item."""
        return {
            "trialitem": str(trial_item.pk),
            "start_time": "0.0",
            "end_time": "1.5",
            "key_pressed": "a",
            "trial_number": "1",
            "resolution_w": "1920",
            "resolution_h": "1080",
            "webgazer_data": "[]",
        }

    def test_post_creates_trial_result_and_returns_json(
        self, client, subjectdata_factory, trialitem_factory
    ):
        """Verify a valid POST creates a TrialResult and returns a JSON resultId."""
        sd = subjectdata_factory()
        ti = trialitem_factory()
        url = reverse("experiments:storeResult", args=(sd.pk,))
        response = client.post(url, self._post_data(ti))
        assert response.status_code == 200
        data = json.loads(response.content)
        assert "resultId" in data
        assert exp_models.TrialResult.objects.filter(subject=sd).count() == 1

    def test_post_stores_correct_fields(
        self, client, subjectdata_factory, trialitem_factory
    ):
        """Verify the stored TrialResult has the correct field values from the POST."""
        sd = subjectdata_factory()
        ti = trialitem_factory()
        url = reverse("experiments:storeResult", args=(sd.pk,))
        client.post(url, self._post_data(ti))
        tr = exp_models.TrialResult.objects.get(subject=sd)
        assert tr.trialitem == ti
        assert tr.key_pressed == "a"
        assert tr.trial_number == 1
        assert tr.resolution_w == 1920
        assert tr.resolution_h == 1080

    def test_get_raises_404(self, client, subjectdata_factory):
        """Verify a GET to storeResult returns 404."""
        sd = subjectdata_factory()
        url = reverse("experiments:storeResult", args=(sd.pk,))
        response = client.get(url)
        assert response.status_code == 404

    def test_nonexistent_subject_returns_404(self, client, trialitem_factory):
        """Verify a POST with an unknown run UUID returns 404."""
        run_uuid = str(uuid.uuid4())
        ti = trialitem_factory()
        url = reverse("experiments:storeResult", args=(run_uuid,))
        response = client.post(url, self._post_data(ti))
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# experimentPause
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestExperimentPause:
    """Tests for the experimentPause view."""

    def test_get_renders_pause_page(
        self, client, subjectdata_factory, experiment_factory, listitem_factory
    ):
        """Verify the pause page renders the pause template content."""
        exp = _simple_experiment(experiment_factory)
        exp.pause_page_tpl = "PAUSE_CONTENT"
        exp.save()
        li = listitem_factory(experiment=exp)
        sd = subjectdata_factory(experiment=exp, listitem=li)
        url = reverse("experiments:experimentPause", args=(sd.pk,))
        response = client.get(url)
        assert response.status_code == 200
        assert b"PAUSE_CONTENT" in response.content

    def test_post_with_prior_trial_result_creates_pause_record(
        self,
        client,
        experiment_factory,
        listitem_factory,
        subjectdata_factory,
        trialitem_factory,
        trialresult_factory,
    ):
        """Verify POSTing after a trial result creates a PAUSE TrialResult record."""
        exp = _simple_experiment(experiment_factory)
        li = listitem_factory(experiment=exp)
        sd = subjectdata_factory(experiment=exp, listitem=li)
        ti = trialitem_factory()
        trialresult_factory(subject=sd, trialitem=ti)
        assert (
            exp_models.TrialResult.objects.filter(
                subject=sd, key_pressed="PAUSE"
            ).count()
            == 0
        )
        url = reverse("experiments:experimentPause", args=(sd.pk,))
        client.post(url, {"trialitem": str(ti.pk)})
        assert (
            exp_models.TrialResult.objects.filter(
                subject=sd, key_pressed="PAUSE"
            ).count()
            == 1
        )

    def test_post_without_prior_trial_result_does_not_create_pause_record(
        self,
        client,
        experiment_factory,
        listitem_factory,
        subjectdata_factory,
        trialitem_factory,
    ):
        """Verify no PAUSE record is created when no prior trial result exists."""
        exp = _simple_experiment(experiment_factory)
        li = listitem_factory(experiment=exp)
        sd = subjectdata_factory(experiment=exp, listitem=li)
        ti = trialitem_factory()
        url = reverse("experiments:experimentPause", args=(sd.pk,))
        client.post(url, {"trialitem": str(ti.pk)})
        assert (
            exp_models.TrialResult.objects.filter(
                subject=sd, key_pressed="PAUSE"
            ).count()
            == 0
        )

    def test_post_passes_trial_id_to_context(
        self,
        client,
        experiment_factory,
        listitem_factory,
        subjectdata_factory,
        trialitem_factory,
        trialresult_factory,
    ):
        """Verify the trial_id context variable is rendered in the pause page."""
        exp = _simple_experiment(experiment_factory)
        exp.pause_page_tpl = "{{ trial_id }}"
        exp.save()
        li = listitem_factory(experiment=exp)
        sd = subjectdata_factory(experiment=exp, listitem=li)
        ti = trialitem_factory()
        trialresult_factory(subject=sd, trialitem=ti)
        url = reverse("experiments:experimentPause", args=(sd.pk,))
        response = client.post(url, {"trialitem": str(ti.pk)})
        assert str(ti.pk).encode() in response.content

    def test_returns_404_for_nonexistent_subject(self, client):
        """Verify a 404 is returned for an unknown run UUID on the pause page."""
        url = reverse("experiments:experimentPause", args=(str(uuid.uuid4()),))
        response = client.get(url)
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# experimentError
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestExperimentError:
    """Tests for the experimentError view."""

    def test_returns_200_and_renders_error_template(
        self, client, experiment_factory, subjectdata_factory, listitem_factory
    ):
        """Verify the error page returns 200 and renders the error template."""
        exp = _simple_experiment(experiment_factory)
        exp.error_page_tpl = "ERROR_CONTENT"
        exp.save()
        li = listitem_factory(experiment=exp)
        sd = subjectdata_factory(experiment=exp, listitem=li)
        url = reverse("experiments:experimentError", args=(sd.pk,))
        response = client.get(url)
        assert response.status_code == 200
        assert b"ERROR_CONTENT" in response.content

    def test_returns_404_for_nonexistent_subject(self, client):
        """Verify a 404 is returned for an unknown run UUID on the error page."""
        url = reverse("experiments:experimentError", args=(str(uuid.uuid4()),))
        response = client.get(url)
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# experimentEnd
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestExperimentEnd:
    """Tests for the experimentEnd (thank-you) view."""

    def test_renders_thank_you_page_when_subject_has_no_listitem(
        self, client, experiment_factory
    ):
        """Verify the thank-you page is shown when the subject has no list item."""
        exp = _simple_experiment(experiment_factory)
        exp.thank_you_page_tpl = "THANK_YOU"
        exp.save()
        sd = exp_models.SubjectData.objects.create(
            id=str(uuid.uuid4()), experiment=exp, participant_id=1
        )
        url = reverse("experiments:experimentEnd", args=(sd.pk,))
        response = client.get(url)
        assert response.status_code == 200
        assert b"THANK_YOU" in response.content

    def test_renders_thank_you_page_when_all_trials_completed(
        self,
        client,
        experiment_factory,
        listitem_factory,
        outerblock_factory,
        blockitem_factory,
        trialitem_factory,
        subjectdata_factory,
        trialresult_factory,
    ):
        """Verify the thank-you template is rendered when all trials are complete."""
        exp = _simple_experiment(experiment_factory)
        exp.thank_you_page_tpl = "THANK_YOU_COMPLETE"
        exp.thank_you_abort_page_tpl = "THANK_YOU_ABORT"
        exp.save()
        li = listitem_factory(experiment=exp)
        ob = outerblock_factory(listitem=li)
        bi = blockitem_factory(outerblock=ob)
        ti = trialitem_factory(blockitem=bi)
        sd = subjectdata_factory(experiment=exp, listitem=li)
        trialresult_factory(subject=sd, trialitem=ti)
        url = reverse("experiments:experimentEnd", args=(sd.pk,))
        response = client.get(url)
        assert response.status_code == 200
        assert b"THANK_YOU_COMPLETE" in response.content
        assert b"THANK_YOU_ABORT" not in response.content

    def test_renders_abort_page_when_trials_incomplete(
        self,
        client,
        experiment_factory,
        listitem_factory,
        outerblock_factory,
        blockitem_factory,
        trialitem_factory,
        subjectdata_factory,
    ):
        """Verify the abort template is rendered when not all trials are completed."""
        exp = _simple_experiment(experiment_factory)
        exp.thank_you_abort_page_tpl = "THANK_YOU_ABORT"
        exp.save()
        li = listitem_factory(experiment=exp)
        ob = outerblock_factory(listitem=li)
        bi = blockitem_factory(outerblock=ob)
        trialitem_factory(blockitem=bi)  # 1 trial, 0 completed
        sd = subjectdata_factory(experiment=exp, listitem=li)
        url = reverse("experiments:experimentEnd", args=(sd.pk,))
        response = client.get(url)
        assert response.status_code == 200
        assert b"THANK_YOU_ABORT" in response.content

    def test_returns_404_for_nonexistent_subject(self, client):
        """Verify a 404 is returned for an unknown run UUID on the end page."""
        url = reverse("experiments:experimentEnd", args=(str(uuid.uuid4()),))
        response = client.get(url)
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# deleteSubject
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestDeleteSubject:
    """Tests for the deleteSubject view."""

    def test_post_deletes_subject_and_returns_204(self, client, subjectdata_factory):
        """Verify a POST to deleteSubject removes the subject and returns 204."""
        sd = subjectdata_factory()
        run_uuid = sd.pk
        url = reverse("experiments:deleteSubject", args=(run_uuid,))
        response = client.post(url)
        assert response.status_code == 204
        assert not exp_models.SubjectData.objects.filter(pk=run_uuid).exists()

    def test_get_raises_404(self, client, subjectdata_factory):
        """Verify a GET to deleteSubject returns 404."""
        sd = subjectdata_factory()
        url = reverse("experiments:deleteSubject", args=(sd.pk,))
        response = client.get(url)
        assert response.status_code == 404

    def test_returns_404_for_nonexistent_subject(self, client):
        """Verify a POST with an unknown run UUID returns 404."""
        url = reverse("experiments:deleteSubject", args=(str(uuid.uuid4()),))
        response = client.post(url)
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# index
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestIndex:
    """Tests for the index view."""

    def test_index_renders(self, client):
        """Verify the index page returns 200 and uses the expected template."""
        response = client.get(reverse("experiments:index"))
        assert response.status_code == 200
        assert "experiments/index.html" in [t.name for t in response.templates]
