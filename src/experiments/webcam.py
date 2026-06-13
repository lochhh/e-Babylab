"""Views for webcam/microphone recording and file upload handling."""

import logging
import shutil
import uuid
from pathlib import Path

from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.http import Http404, HttpResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import get_object_or_404
from django.template import RequestContext, Template
from django.urls import reverse
from django.utils.text import get_valid_filename
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_POST

from .models import SubjectData, TrialResult

# Create a logger for this file
logger = logging.getLogger(__name__)


@ensure_csrf_cookie
def webcam_test(request, run_uuid):
    """Generate the webcam/microphone test page."""
    subject_data = get_object_or_404(SubjectData, pk=run_uuid)
    experiment = subject_data.experiment
    c = RequestContext(
        request,
        {
            "subject_data": subject_data,
            "experiment": experiment,
        },
    )

    if experiment.recording_option == "VID" or experiment.recording_option == "ALL":
        t = Template(experiment.webcam_check_page_tpl)
    elif experiment.recording_option == "AUD":  # audio
        t = Template(experiment.microphone_check_page_tpl)
    else:  # no recording required
        return HttpResponseRedirect(
            reverse("experiments:experimentRun", args=(str(run_uuid),))
        )
    return HttpResponse(t.render(c))


@require_POST
def webcam_test_upload(request, run_uuid):
    """Upload the webcam/microphone test file and return metadata."""
    webcam_file = request.FILES.get("file")
    if not webcam_file:
        logger.error("Failed to upload test media.")
        raise Http404("Page not found.")

    get_object_or_404(SubjectData, pk=run_uuid)
    webcam_file_type = request.POST.get("type")

    fs = FileSystemStorage(
        location=settings.WEBCAM_TEST_ROOT, base_url=settings.WEBCAM_TEST_URL
    )

    extension = Path(webcam_file.name).suffix
    random_file_name = str(uuid.uuid4()) + extension
    filename = fs.save(random_file_name, webcam_file)

    return JsonResponse(
        {
            "videoUrl": fs.url(filename),
            "size": fs.size(filename),
            "type": webcam_file_type,
            "runUuid": run_uuid,
        }
    )


def _upload_chunk(request):
    """Store a single uploaded chunk in WEBCAM_ROOT, replacing any existing file."""
    fs = FileSystemStorage(location=settings.WEBCAM_ROOT)
    webcam_file = request.FILES["file"]
    if fs.exists(webcam_file.name):
        fs.delete(webcam_file.name)
    fs.save(get_valid_filename(webcam_file.name), webcam_file)
    logger.info(f"Received upload request of {webcam_file.name}.")
    return HttpResponse(status=204)


def _upload_merge(request, run_uuid):
    """Merge uploaded chunks into a single file and associate it with a TrialResult."""
    fs = FileSystemStorage(location=settings.WEBCAM_ROOT)
    base_filename = get_valid_filename(request.POST["filename"])
    logger.info(f"Received last file of {base_filename}, merge files.")

    webcam_files = find_files(base_filename)
    merge_files(base_filename + ".webm", webcam_files)
    for webcam_file in webcam_files:
        fs.delete(webcam_file)

    try:
        trial_result_id = int(request.POST["trialResultId"])
    except ValueError as e:
        logger.exception("Failed to retrieve trial result ID: " + str(e))
        raise Http404("Invalid trialResultId.") from e
    trial_result = get_object_or_404(TrialResult, pk=trial_result_id, subject=run_uuid)
    trial_result.webcam_file = base_filename + ".webm"
    trial_result.save()
    logger.info("Successfully saved webcam file to trial result.")
    return HttpResponse(status=204)


@require_POST
def webcam_upload(request, run_uuid):
    """Receive uploaded video/audio chunks and merge them into a complete file."""
    if request.FILES.get("file"):
        return _upload_chunk(request)
    if request.POST.get("trialResultId"):
        return _upload_merge(request, run_uuid)
    logger.error("Failed to upload webcam file.")
    raise Http404("Page not found.")


def find_files(base_filename):
    """Retrieve uploaded chunk filenames matching the given base filename."""
    root = Path(settings.WEBCAM_ROOT)
    return sorted(p.name for p in root.glob(f"{base_filename}-*"))


def merge_files(target, files):
    """Merge chunk files into a single target file."""
    root = Path(settings.WEBCAM_ROOT)
    destination = root / target

    if destination.exists():
        destination.unlink()

    with destination.open("wb") as outfile:
        for fname in files:
            with (root / fname).open("rb") as infile:
                shutil.copyfileobj(infile, outfile)
