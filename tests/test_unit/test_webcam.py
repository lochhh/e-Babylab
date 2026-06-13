"""Unit tests that cover webcam.py behaviour.

These tests exercise:
- webcam_test and webcam_test_upload views: test that the correct templates are rendered
  for experiments with different recording options, and that the webcam test upload view
  correctly handles uploads of recorded media and returns the expected metadata.
- webcam_upload view: test that recorded chunks are uploaded, merged, and later deleted,
  and that the final merged file is saved and associated with the correct SubjectData.
  Also test error handling.
- find_files, merge_files helper functions: test that these functions correctly find and
  merge chunks belonging to the same trial, and that they handle edge cases.
"""

import uuid

import pytest
from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from experiments.webcam import find_files, merge_files

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_experiment(experiment_factory, recording_option="NON"):
    """Create an experiment with template fields populated."""
    exp = experiment_factory()
    exp.recording_option = recording_option
    exp.webcam_check_page_tpl = "WEBCAM_TEMPLATE"
    exp.microphone_check_page_tpl = "MIC_TEMPLATE"
    exp.save()
    return exp


def _webcam_test_url(run_uuid):
    """Return the URL for the webcam test view."""
    return reverse("experiments:webcamTest", args=(str(run_uuid),))


def _webcam_test_upload_url(run_uuid):
    """Return the URL for the webcam test upload view."""
    return reverse("experiments:webcamUpload", args=(str(run_uuid),))


def _webcam_upload_url(run_uuid):
    """Return the URL for the experiment webcam upload view."""
    return reverse("experiments:experimentWebcamUpload", args=(str(run_uuid),))


# ---------------------------------------------------------------------------
# webcam_test
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestWebcamTest:
    """Tests for the webcam_test view."""

    @pytest.mark.parametrize("recording_option", ["VID", "ALL"])
    def test_vid_or_all_renders_webcam_check_template(
        self, client, subjectdata_factory, experiment_factory, recording_option
    ):
        """VID and ALL recording options render the webcam check template."""
        exp = _make_experiment(experiment_factory, recording_option=recording_option)
        subject = subjectdata_factory(experiment=exp)
        response = client.get(_webcam_test_url(subject.id))
        assert response.status_code == 200
        assert b"WEBCAM_TEMPLATE" in response.content

    def test_aud_renders_microphone_check_template(
        self, client, subjectdata_factory, experiment_factory
    ):
        """AUD recording option renders the microphone check template."""
        exp = _make_experiment(experiment_factory, recording_option="AUD")
        subject = subjectdata_factory(experiment=exp)
        response = client.get(_webcam_test_url(subject.id))
        assert response.status_code == 200
        assert b"MIC_TEMPLATE" in response.content

    @pytest.mark.parametrize("recording_option", ["NON", "EYE"])
    def test_no_recording_redirects_to_experiment_run(
        self, client, subjectdata_factory, experiment_factory, recording_option
    ):
        """NON and EYE recording options redirect to the experiment run view."""
        exp = _make_experiment(experiment_factory, recording_option=recording_option)
        subject = subjectdata_factory(experiment=exp)
        response = client.get(_webcam_test_url(subject.id))
        assert response.status_code == 302
        assert response["Location"] == reverse(
            "experiments:experimentRun", args=(str(subject.id),)
        )

    def test_nonexistent_run_uuid_returns_404(self, client):
        """A run_uuid that does not exist returns a 404 response."""
        response = client.get(_webcam_test_url(uuid.uuid4()))
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# webcam_test_upload
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestWebcamTestUpload:
    """Tests for the webcam_test_upload view."""

    def test_post_with_file_returns_metadata(
        self, client, subjectdata_factory, experiment_factory, tmp_path, monkeypatch
    ):
        """A valid POST with a file returns JSON metadata for the uploaded file."""
        monkeypatch.setattr(settings, "WEBCAM_TEST_ROOT", str(tmp_path), raising=False)
        monkeypatch.setattr(settings, "WEBCAM_TEST_URL", "/webcam-test/", raising=False)
        exp = _make_experiment(experiment_factory)
        subject = subjectdata_factory(experiment=exp)
        fake_file = SimpleUploadedFile(
            "test.webm", b"fake video content", content_type="video/webm"
        )
        response = client.post(
            _webcam_test_upload_url(subject.id),
            data={"file": fake_file, "type": "video/webm"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "videoUrl" in data
        assert data["type"] == "video/webm"
        assert data["runUuid"] == str(subject.id)
        assert data["size"] > 0

    def test_get_request_returns_405(
        self, client, subjectdata_factory, experiment_factory
    ):
        """A GET request to webcam_test_upload returns 405 Method Not Allowed."""
        exp = _make_experiment(experiment_factory)
        subject = subjectdata_factory(experiment=exp)
        response = client.get(_webcam_test_upload_url(subject.id))
        assert response.status_code == 405

    def test_post_without_file_returns_404(
        self, client, subjectdata_factory, experiment_factory
    ):
        """A POST without a file field returns 404."""
        exp = _make_experiment(experiment_factory)
        subject = subjectdata_factory(experiment=exp)
        response = client.post(
            _webcam_test_upload_url(subject.id), data={"type": "video/webm"}
        )
        assert response.status_code == 404

    def test_nonexistent_run_uuid_returns_404(self, client, tmp_path, monkeypatch):
        """A run_uuid that does not exist returns 404 even with a valid file."""
        monkeypatch.setattr(settings, "WEBCAM_TEST_ROOT", str(tmp_path), raising=False)
        monkeypatch.setattr(settings, "WEBCAM_TEST_URL", "/webcam-test/", raising=False)
        fake_file = SimpleUploadedFile("test.webm", b"data", content_type="video/webm")
        response = client.post(
            _webcam_test_upload_url(uuid.uuid4()),
            data={"file": fake_file, "type": "video/webm"},
        )
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# webcam_upload
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestWebcamUpload:
    """Tests for the webcam_upload view."""

    def test_post_chunk_returns_204(
        self, client, subjectdata_factory, experiment_factory, tmp_path, monkeypatch
    ):
        """A POST with a chunk file returns HTTP 204 No Content."""
        monkeypatch.setattr(settings, "WEBCAM_ROOT", str(tmp_path), raising=False)
        exp = _make_experiment(experiment_factory)
        subject = subjectdata_factory(experiment=exp)
        chunk = SimpleUploadedFile(
            "trial-0.webm", b"chunk data", content_type="video/webm"
        )
        response = client.post(_webcam_upload_url(subject.id), data={"file": chunk})
        assert response.status_code == 204

    def test_post_chunk_overwrites_existing_file(
        self, client, subjectdata_factory, experiment_factory, tmp_path, monkeypatch
    ):
        """A chunk upload replaces a pre-existing file with the same name."""
        monkeypatch.setattr(settings, "WEBCAM_ROOT", str(tmp_path), raising=False)
        exp = _make_experiment(experiment_factory)
        subject = subjectdata_factory(experiment=exp)
        (tmp_path / "trial-0.webm").write_bytes(b"old data")
        chunk = SimpleUploadedFile(
            "trial-0.webm", b"new data", content_type="video/webm"
        )
        response = client.post(_webcam_upload_url(subject.id), data={"file": chunk})
        assert response.status_code == 204
        assert (tmp_path / "trial-0.webm").read_bytes() == b"new data"

    def test_post_merge_request_merges_chunks_and_saves_to_trial_result(
        self,
        client,
        subjectdata_factory,
        trialresult_factory,
        experiment_factory,
        tmp_path,
        monkeypatch,
    ):
        """Merge POST merges chunks, removes them, and saves path on TrialResult."""
        monkeypatch.setattr(settings, "WEBCAM_ROOT", str(tmp_path), raising=False)
        exp = _make_experiment(experiment_factory)
        subject = subjectdata_factory(experiment=exp)
        trial_result = trialresult_factory(subject=subject)
        (tmp_path / "trial-0.webm").write_bytes(b"part0")
        (tmp_path / "trial-1.webm").write_bytes(b"part1")

        response = client.post(
            _webcam_upload_url(subject.id),
            data={"filename": "trial", "trialResultId": str(trial_result.id)},
        )
        assert response.status_code == 204
        assert not (tmp_path / "trial-0.webm").exists()
        assert not (tmp_path / "trial-1.webm").exists()
        assert (tmp_path / "trial.webm").read_bytes() == b"part0part1"
        trial_result.refresh_from_db()
        assert trial_result.webcam_file.name == "trial.webm"

    def test_post_merge_invalid_trial_result_id_returns_404(
        self, client, subjectdata_factory, experiment_factory, tmp_path, monkeypatch
    ):
        """A merge POST with a non-integer trialResultId returns 404."""
        monkeypatch.setattr(settings, "WEBCAM_ROOT", str(tmp_path), raising=False)
        exp = _make_experiment(experiment_factory)
        subject = subjectdata_factory(experiment=exp)
        response = client.post(
            _webcam_upload_url(subject.id),
            data={"filename": "trial", "trialResultId": "not-an-int"},
        )
        assert response.status_code == 404

    def test_post_merge_nonexistent_trial_result_returns_404(
        self, client, subjectdata_factory, experiment_factory, tmp_path, monkeypatch
    ):
        """A merge POST with an unknown trialResultId returns 404."""
        monkeypatch.setattr(settings, "WEBCAM_ROOT", str(tmp_path), raising=False)
        exp = _make_experiment(experiment_factory)
        subject = subjectdata_factory(experiment=exp)
        response = client.post(
            _webcam_upload_url(subject.id),
            data={"filename": "trial", "trialResultId": "99999"},
        )
        assert response.status_code == 404

    def test_get_request_returns_405(
        self, client, subjectdata_factory, experiment_factory
    ):
        """A GET request to webcam_upload returns 405 Method Not Allowed."""
        exp = _make_experiment(experiment_factory)
        subject = subjectdata_factory(experiment=exp)
        response = client.get(_webcam_upload_url(subject.id))
        assert response.status_code == 405

    def test_post_without_file_or_trial_result_id_returns_404(
        self, client, subjectdata_factory, experiment_factory
    ):
        """A POST with neither a file nor trialResultId returns 404."""
        exp = _make_experiment(experiment_factory)
        subject = subjectdata_factory(experiment=exp)
        response = client.post(_webcam_upload_url(subject.id), data={})
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# find_files
# ---------------------------------------------------------------------------


class TestFindFiles:
    """Tests for the find_files helper function."""

    def test_returns_matching_files_sorted(self, tmp_path, monkeypatch):
        """Files matching base_filename + '-' prefix are returned in sorted order."""
        monkeypatch.setattr(settings, "WEBCAM_ROOT", str(tmp_path), raising=False)
        (tmp_path / "trial-2.webm").write_bytes(b"")
        (tmp_path / "trial-0.webm").write_bytes(b"")
        (tmp_path / "trial-1.webm").write_bytes(b"")
        result = find_files("trial")
        assert result == ["trial-0.webm", "trial-1.webm", "trial-2.webm"]

    def test_ignores_files_without_hyphen_separator(self, tmp_path, monkeypatch):
        """Files that don't start with base_filename + '-' are excluded."""
        monkeypatch.setattr(settings, "WEBCAM_ROOT", str(tmp_path), raising=False)
        (tmp_path / "trial-0.webm").write_bytes(b"")
        (tmp_path / "other-0.webm").write_bytes(b"")
        (tmp_path / "trial.webm").write_bytes(b"")
        result = find_files("trial")
        assert result == ["trial-0.webm"]

    def test_returns_empty_list_when_no_matches(self, tmp_path, monkeypatch):
        """An empty list is returned when no chunk files match the base filename."""
        monkeypatch.setattr(settings, "WEBCAM_ROOT", str(tmp_path), raising=False)
        result = find_files("nonexistent")
        assert result == []


# ---------------------------------------------------------------------------
# merge_files
# ---------------------------------------------------------------------------


class TestMergeFiles:
    """Tests for the merge_files helper function."""

    def test_merges_file_contents_in_order(self, tmp_path, monkeypatch):
        """Chunk contents are concatenated in order into the target file."""
        monkeypatch.setattr(settings, "WEBCAM_ROOT", str(tmp_path), raising=False)
        (tmp_path / "chunk-0.webm").write_bytes(b"hello ")
        (tmp_path / "chunk-1.webm").write_bytes(b"world")
        merge_files("merged.webm", ["chunk-0.webm", "chunk-1.webm"])
        assert (tmp_path / "merged.webm").read_bytes() == b"hello world"

    def test_overwrites_existing_target(self, tmp_path, monkeypatch):
        """An existing target file is replaced by the merge result."""
        monkeypatch.setattr(settings, "WEBCAM_ROOT", str(tmp_path), raising=False)
        (tmp_path / "output.webm").write_bytes(b"old content")
        (tmp_path / "chunk-0.webm").write_bytes(b"new content")
        merge_files("output.webm", ["chunk-0.webm"])
        assert (tmp_path / "output.webm").read_bytes() == b"new content"

    def test_empty_file_list_creates_empty_target(self, tmp_path, monkeypatch):
        """Merging an empty list of files creates an empty target file."""
        monkeypatch.setattr(settings, "WEBCAM_ROOT", str(tmp_path), raising=False)
        merge_files("empty.webm", [])
        assert (tmp_path / "empty.webm").exists()
        assert (tmp_path / "empty.webm").read_bytes() == b""
