"""Views for webcam/microphone recording and file upload handling."""

import logging
import os.path
import uuid

from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.http import Http404, HttpResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import get_object_or_404
from django.template import RequestContext, Template
from django.urls import reverse
from django.utils.text import get_valid_filename
from django.views.decorators.csrf import ensure_csrf_cookie

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


def webcam_test_upload(request, run_uuid):
    """Upload the webcam/microphone test file and return metadata."""
    webcam_file = request.FILES.get("file")
    if request.method == "POST" and webcam_file:
        get_object_or_404(SubjectData, pk=run_uuid)
        webcam_file_type = request.POST.get("type")

        fs = FileSystemStorage(
            location=settings.WEBCAM_TEST_ROOT, base_url=settings.WEBCAM_TEST_URL
        )

        # Generate random file name
        extension = os.path.splitext(webcam_file.name)[1]
        random_file_name = str(uuid.uuid4()) + extension
        filename = fs.save(random_file_name, webcam_file)

        # Return metadata of uploaded video
        return JsonResponse(
            {
                "videoUrl": fs.url(filename),
                "size": fs.size(filename),
                "type": webcam_file_type,
                "runUuid": run_uuid,
            }
        )
    else:
        logger.error("Failed to upload test media.")
        raise Http404("Page not found.")


def webcam_upload(request, run_uuid):
    """Receive uploaded video/audio chunks and merge them into a complete file."""
    fs = FileSystemStorage(location=settings.WEBCAM_ROOT)

    # Upload request
    if request.method == "POST" and request.FILES.get("file"):
        webcam_file = request.FILES.get("file")

        # Delete existing file
        if fs.exists(webcam_file.name):
            fs.delete(webcam_file.name)

        fs.save(get_valid_filename(webcam_file.name), webcam_file)
        logger.info(f"Received upload request of {webcam_file.name}.")
        return HttpResponse(status=204)

    # Merge request
    elif request.method == "POST" and request.POST.get("trialResultId"):
        # Get base filename, by removing chunk number at the end
        base_filename = request.POST.get("filename")
        base_filename = get_valid_filename(base_filename)
        logger.info(f"Received last file of {base_filename}, merge files.")

        # Find and merge individual chunks
        webcam_files = find_files(base_filename)
        merge_files(base_filename + ".webm", webcam_files)

        # Delete chunks
        for webcam_file in webcam_files:
            fs.delete(webcam_file)

        # Add filename to trial result
        try:
            trial_result_id = int(request.POST.get("trialResultId"))
        except ValueError as e:
            logger.exception("Failed to retrieve trial result ID: " + str(e))
            raise Http404("Invalid trialResultId.") from e
        trial_result = get_object_or_404(
            TrialResult, pk=trial_result_id, subject=run_uuid
        )
        trial_result.webcam_file = base_filename + ".webm"
        trial_result.save()
        logger.info("Successfully saved webcam file to trial result.")
        return HttpResponse(status=204)

    else:
        logger.error("Failed to upload webcam file.")
        raise Http404("Page not found.")


def find_files(base_filename):
    """Retrieve uploaded chunk filenames matching the given base filename."""
    result = []
    for fname in os.listdir(settings.WEBCAM_ROOT):
        if fname.startswith(base_filename + "-"):
            result.append(fname)

    # Sort alphabetically
    result.sort()

    return result


def merge_files(target, files):
    """Merge chunk files into a single target file."""
    fs = FileSystemStorage(location=settings.WEBCAM_ROOT)

    destination_file = os.path.join(settings.WEBCAM_ROOT, target)

    # Delete any existing file
    if fs.exists(target):
        fs.delete(target)

    # Merge
    with open(destination_file, "wb") as outfile:
        for fname in files:
            with open(os.path.join(settings.WEBCAM_ROOT, fname), "rb") as infile:
                while True:
                    data = infile.read(65536)
                    if not data:
                        break
                    outfile.write(data)
