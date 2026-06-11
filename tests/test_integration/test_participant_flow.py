"""Integration tests for end-to-end participant flows.

Tests the complete journey through the experiment, list selection strategies,
recording option branching, and trial ordering/randomisation.
"""

import pytest
from django.urls import reverse

from experiments import models as exp_models

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _post_consent(client, exp, consent_questions, all_yes=True):
    """POST to consentFormSubmit with all questions answered."""
    data = {f"question_{q.pk}": "yes" if all_yes else "no" for q in consent_questions}
    return client.post(reverse("experiments:consentFormSubmit", args=[exp.pk]), data)


def _post_subject_form(client, exp, mocker):
    """POST to subjectFormSubmit with reCAPTCHA mocked to succeed."""
    mocker.patch(
        "experiments.views.requests.post",
        return_value=mocker.Mock(json=lambda: {"success": True}),
    )
    return client.post(
        reverse("experiments:subjectFormSubmit", args=[exp.pk]),
        {"resolution_w": 1920, "resolution_h": 1080, "g-recaptcha-response": "token"},
    )


# ---------------------------------------------------------------------------
# Full participant flow (NON recording)
# ---------------------------------------------------------------------------


class TestParticipantFlowNonRecording:
    """Tests for the participant flow when no recording is enabled."""

    @pytest.mark.django_db
    def test_consent_to_experiment_run_redirect_chain(
        self, client, simple_experiment, consent_question_factory, mocker
    ):
        """POST consent → POST subject form → land on experiment run URL."""
        q = consent_question_factory(experiment=simple_experiment)

        # Step 1: consent
        resp = _post_consent(client, simple_experiment, [q])
        assert resp.status_code == 302
        assert (
            reverse("experiments:subjectForm", args=[simple_experiment.pk])
            in resp["Location"]
        )

        # Step 2: subject form
        resp = _post_subject_form(client, simple_experiment, mocker)
        assert resp.status_code == 302
        # NON recording → goes to experimentRun
        assert "/run" in resp["Location"]

    @pytest.mark.django_db
    def test_subject_data_created_after_form_submit(
        self, client, simple_experiment, mocker
    ):
        """Verify that a SubjectData record is created after a valid form submission."""
        _post_subject_form(client, simple_experiment, mocker)
        assert (
            exp_models.SubjectData.objects.filter(experiment=simple_experiment).count()
            == 1
        )

    @pytest.mark.django_db
    def test_full_flow_information_to_thankyou(
        self,
        client,
        simple_experiment,
        mocker,
        consent_question_factory,
        trialitem_factory,
        listitem_factory,
        outerblock_factory,
        blockitem_factory,
        trialresult_factory,
    ):
        """Walk every step of the participant flow and verify status codes."""
        # Set up a list with a trial so experimentRun can load
        li = listitem_factory(experiment=simple_experiment)
        ob = outerblock_factory(listitem=li)
        block = blockitem_factory(outerblock=ob)
        trialitem_factory(blockitem=block)

        # 1. Information page
        resp = client.get(
            reverse("experiments:informationPage", args=[simple_experiment.pk])
        )
        assert resp.status_code == 200

        # 2. Browser check
        resp = client.get(
            reverse("experiments:browserCheck", args=[simple_experiment.pk])
        )
        assert resp.status_code == 200

        # 3. Consent form
        q = consent_question_factory(experiment=simple_experiment)
        resp = client.get(
            reverse("experiments:consentForm", args=[simple_experiment.pk])
        )
        assert resp.status_code == 200

        # 4. Consent submit
        resp = _post_consent(client, simple_experiment, [q])
        assert resp.status_code == 302

        # 5. Subject form
        resp = client.get(
            reverse("experiments:subjectForm", args=[simple_experiment.pk])
        )
        assert resp.status_code == 200

        # 6. Subject form submit → creates SubjectData
        resp = _post_subject_form(client, simple_experiment, mocker)
        assert resp.status_code == 302
        run_url = resp["Location"]

        sd = exp_models.SubjectData.objects.get(experiment=simple_experiment)
        run_uuid = sd.pk

        # 7. Experiment run
        resp = client.get(run_url)
        assert resp.status_code == 200

        # 8. Thank you page
        resp = client.get(reverse("experiments:experimentEnd", args=[run_uuid]))
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Recording option branching
# ---------------------------------------------------------------------------


class TestRecordingOptionBranching:
    """Tests verifying redirects based on the experiment recording option."""

    @pytest.mark.django_db
    def test_non_recording_redirects_to_experiment_run(
        self, client, simple_experiment, mocker
    ):
        """Verify NON recording option redirects directly to the experiment run page."""
        simple_experiment.recording_option = "NON"
        simple_experiment.save()
        resp = _post_subject_form(client, simple_experiment, mocker)
        assert "/run" in resp["Location"]
        assert "/test" not in resp["Location"]

    @pytest.mark.django_db
    def test_eye_tracking_redirects_to_experiment_run(
        self, client, simple_experiment, mocker
    ):
        """Verify EYE tracking option redirects directly to the experiment run page."""
        simple_experiment.recording_option = "EYE"
        simple_experiment.save()
        resp = _post_subject_form(client, simple_experiment, mocker)
        assert "/run" in resp["Location"]
        assert "/test" not in resp["Location"]

    @pytest.mark.django_db
    def test_audio_redirects_to_webcam_test(self, client, simple_experiment, mocker):
        """Verify AUD recording option redirects to the webcam/microphone test page."""
        simple_experiment.recording_option = "AUD"
        simple_experiment.save()
        resp = _post_subject_form(client, simple_experiment, mocker)
        assert "/test" in resp["Location"]

    @pytest.mark.django_db
    def test_video_redirects_to_webcam_test(self, client, simple_experiment, mocker):
        """Verify VID recording option redirects to the webcam test page."""
        simple_experiment.recording_option = "VID"
        simple_experiment.save()
        resp = _post_subject_form(client, simple_experiment, mocker)
        assert "/test" in resp["Location"]

    @pytest.mark.django_db
    def test_all_redirects_to_webcam_test(self, client, simple_experiment, mocker):
        """Verify ALL recording option redirects to the webcam test page."""
        simple_experiment.recording_option = "ALL"
        simple_experiment.save()
        resp = _post_subject_form(client, simple_experiment, mocker)
        assert "/test" in resp["Location"]


# ---------------------------------------------------------------------------
# List selection strategies
# ---------------------------------------------------------------------------


class TestListSelectionStrategies:
    """Tests for list selection strategies (LPF, SEQ, RAN, excluded lists)."""

    @pytest.mark.django_db
    def test_lpf_selects_least_played_list(
        self, client, simple_experiment, listitem_factory, subjectdata_factory, mocker
    ):
        """With LPF strategy, the list with fewer participants is selected."""
        simple_experiment.list_selection_strategy = "LPF"
        simple_experiment.save()
        l1 = listitem_factory(list_name="L1", experiment=simple_experiment)
        l2 = listitem_factory(list_name="L2", experiment=simple_experiment)
        # Assign one subject to L1 so L2 is the least played
        subjectdata_factory(experiment=simple_experiment, listitem=l1)

        resp = _post_subject_form(client, simple_experiment, mocker)
        sd = (
            exp_models.SubjectData.objects.filter(experiment=simple_experiment)
            .order_by("-participant_id")
            .first()
        )
        # Trigger list assignment by visiting the run page
        client.get(resp["Location"])
        sd.refresh_from_db()
        assert sd.listitem == l2

    @pytest.mark.django_db
    def test_seq_selects_next_list_in_order(
        self, client, simple_experiment, listitem_factory, subjectdata_factory, mocker
    ):
        """With SEQ strategy, lists are selected in round-robin order by ID."""
        simple_experiment.list_selection_strategy = "SEQ"
        simple_experiment.save()
        _l1 = listitem_factory(list_name="L1", experiment=simple_experiment)
        _l2 = listitem_factory(list_name="L2", experiment=simple_experiment)

        # Assign one previous subject to the first list (lowest ID)
        first_list = (
            exp_models.ListItem.objects.filter(experiment=simple_experiment)
            .order_by("id")
            .first()
        )
        subjectdata_factory(experiment=simple_experiment, listitem=first_list)

        resp = _post_subject_form(client, simple_experiment, mocker)
        sd = (
            exp_models.SubjectData.objects.filter(experiment=simple_experiment)
            .order_by("-participant_id")
            .first()
        )
        client.get(resp["Location"])
        sd.refresh_from_db()
        # The next subject should get the other list
        assert sd.listitem != first_list

    @pytest.mark.django_db
    def test_ran_selects_a_valid_list(
        self, client, simple_experiment, listitem_factory, mocker
    ):
        """With RAN strategy, a valid ListItem is selected."""
        simple_experiment.list_selection_strategy = "RAN"
        simple_experiment.save()
        l1 = listitem_factory(list_name="L1", experiment=simple_experiment)
        l2 = listitem_factory(list_name="L2", experiment=simple_experiment)

        resp = _post_subject_form(client, simple_experiment, mocker)
        sd = exp_models.SubjectData.objects.get(experiment=simple_experiment)
        client.get(resp["Location"])
        sd.refresh_from_db()
        assert sd.listitem in [l1, l2]

    @pytest.mark.django_db
    def test_excluded_list_is_not_selected(
        self, client, simple_experiment, listitem_factory, mocker
    ):
        """Lists marked exclude_list=True must never be assigned."""
        simple_experiment.list_selection_strategy = "RAN"
        simple_experiment.save()
        included = listitem_factory(
            list_name="Include", experiment=simple_experiment, exclude_list=False
        )
        listitem_factory(
            list_name="Exclude", experiment=simple_experiment, exclude_list=True
        )

        for _ in range(5):
            resp = _post_subject_form(client, simple_experiment, mocker)
            sd = (
                exp_models.SubjectData.objects.filter(experiment=simple_experiment)
                .order_by("-participant_id")
                .first()
            )
            client.get(resp["Location"])
            sd.refresh_from_db()
            assert sd.listitem == included


# ---------------------------------------------------------------------------
# Trial ordering
# ---------------------------------------------------------------------------


class TestTrialOrdering:
    """Tests for trial ordering and deduplication in the experiment run view."""

    @pytest.mark.django_db
    def test_fixed_order_trials_appear_in_position_order(
        self,
        client,
        subjectdata_factory,
        experiment_factory,
        listitem_factory,
        outerblock_factory,
        blockitem_factory,
        trialitem_factory,
    ):
        """Verify trials with randomise_trials=False appear in their defined order."""
        exp = experiment_factory()
        exp.experiment_page_tpl = "{% autoescape off %}{{ trials }}{% endautoescape %}"
        for f in [
            "information_page_tpl",
            "browser_check_page_tpl",
            "introduction_page_tpl",
            "consent_fail_page_tpl",
            "demographic_data_page_tpl",
            "cdi_page_tpl",
            "webcam_check_page_tpl",
            "microphone_check_page_tpl",
            "pause_page_tpl",
            "thank_you_page_tpl",
            "thank_you_abort_page_tpl",
            "error_page_tpl",
        ]:
            setattr(exp, f, "OK")
        exp.save()

        li = listitem_factory(experiment=exp)
        ob = outerblock_factory(listitem=li)
        block = blockitem_factory(outerblock=ob)
        block.randomise_trials = False
        block.save()

        _t1 = trialitem_factory(blockitem=block, label="First", position=1)
        _t2 = trialitem_factory(blockitem=block, label="Second", position=2)
        _t3 = trialitem_factory(blockitem=block, label="Third", position=3)

        sd = subjectdata_factory(experiment=exp, listitem=li)
        import json

        response = client.get(reverse("experiments:experimentRun", args=[sd.pk]))
        trials = json.loads(response.content.decode())
        labels = [t["label"] for t in trials]
        assert labels == ["First", "Second", "Third"]

    @pytest.mark.django_db
    def test_completed_trial_not_repeated(
        self, client, subjectdata_factory, trialresult_factory, experiment_with_trials
    ):
        """Verify that a completed trial (has TrialResult) is excluded from the run."""
        exp, listitem, trial = experiment_with_trials
        exp.experiment_page_tpl = "{% autoescape off %}{{ trials }}{% endautoescape %}"
        exp.save()
        sd = subjectdata_factory(experiment=exp, listitem=listitem)
        trialresult_factory(subject=sd, trialitem=trial)

        import json

        response = client.get(reverse("experiments:experimentRun", args=[sd.pk]))
        trials = json.loads(response.content.decode())
        assert all(t["trial_id"] != trial.pk for t in trials)


# ---------------------------------------------------------------------------
# Data deletion
# ---------------------------------------------------------------------------


class TestDataDeletion:
    """Tests for the deleteSubject endpoint and cascade behaviour."""

    @pytest.mark.django_db
    def test_delete_removes_subject_and_cascades_trial_results(
        self, client, subjectdata_factory, trialresult_factory, experiment_with_trials
    ):
        """Verify that deleting a subject also removes all associated trial results."""
        exp, listitem, trial = experiment_with_trials
        sd = subjectdata_factory(experiment=exp, listitem=listitem)
        trialresult_factory(subject=sd, trialitem=trial)
        pk = sd.pk

        resp = client.post(reverse("experiments:deleteSubject", args=[pk]))
        assert resp.status_code == 204
        assert not exp_models.SubjectData.objects.filter(pk=pk).exists()
        assert not exp_models.TrialResult.objects.filter(subject_id=pk).exists()

    @pytest.mark.django_db
    def test_deleted_run_uuid_returns_404(
        self, client, subjectdata_factory, simple_experiment
    ):
        """Verify that accessing the end page for a deleted subject returns 404."""
        sd = subjectdata_factory(experiment=simple_experiment)
        pk = sd.pk
        client.post(reverse("experiments:deleteSubject", args=[pk]))
        resp = client.get(reverse("experiments:experimentEnd", args=[pk]))
        assert resp.status_code == 404
