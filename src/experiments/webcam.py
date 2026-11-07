"""Views for webcam/microphone recording and file upload handling."""

import logging
import re
import shutil
import time
import uuid
from datetime import timedelta
from pathlib import Path

from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.db.models import Q
from django.http import (
    HttpResponse,
    HttpResponseBadRequest,
    HttpResponseRedirect,
    JsonResponse,
)
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
        return HttpResponseBadRequest("Missing file.")

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
    """Store a single uploaded chunk in WEBCAM_ROOT, replacing any existing file.

    The first chunk of a recording also removes unmerged chunks left under the
    same name, e.g. by a trial that was interrupted by a pause and restarted.
    """
    fs = FileSystemStorage(location=settings.WEBCAM_ROOT)
    webcam_file = request.FILES["file"]
    first_chunk = re.fullmatch(r"(.+)-0{5}\.webm", webcam_file.name)
    if first_chunk:
        for stale in find_files(get_valid_filename(first_chunk.group(1))):
            fs.delete(stale)
    if fs.exists(webcam_file.name):
        fs.delete(webcam_file.name)
    fs.save(get_valid_filename(webcam_file.name), webcam_file)
    logger.info(f"Received upload request of {webcam_file.name}.")
    return HttpResponse(status=204)


def _upload_merge(request, run_uuid):
    """Merge uploaded chunks into a single file and associate it with a TrialResult."""
    fs = FileSystemStorage(location=settings.WEBCAM_ROOT)
    base_filename = get_valid_filename(request.POST["filename"])
    target = base_filename + ".webm"
    logger.info(f"Received last file of {base_filename}, merge files.")

    webcam_files = find_files(base_filename)
    if webcam_files:
        # New chunks under a taken name are a new recording (e.g. a calibration
        # repeated twice before the same trial), so number it rather than
        # overwrite; a retried merge has no chunks and keeps the existing file.
        target = _unused_name(fs, base_filename)
    merge_files(target, webcam_files)

    try:
        trial_result_id = int(request.POST["trialResultId"])
    except ValueError as e:
        logger.exception("Failed to retrieve trial result ID: " + str(e))
        return HttpResponseBadRequest("Invalid trialResultId.")
    trial_result = get_object_or_404(TrialResult, pk=trial_result_id, subject=run_uuid)
    if not fs.exists(target):
        logger.warning(f"No webcam chunks received for {base_filename}.")
        return HttpResponse(status=204)
    trial_result.webcam_file = target
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
    return HttpResponseBadRequest("Missing file or trialResultId.")


def _unused_name(fs, stem):
    """Return ``stem.webm``, or ``stem_2.webm``, ``stem_3.webm``... if taken."""
    target = f"{stem}.webm"
    n = 2
    while fs.exists(target):
        target = f"{stem}_{n}.webm"
        n += 1
    return target


def recover_recordings(subject: SubjectData, min_age: timedelta = timedelta(0)) -> None:
    """Attach chunks left behind by finished trials whose merge request never came.

    A participant who leaves the run page before the upload queue empties
    leaves a finished trial's chunks on disk, unmerged. They are always the
    start of the recording, so they are merged into ``<name>_partial.webm`` and
    attached to the trial result. Chunks of interrupted trials (no result) are
    left alone; they are discarded when the trial restarts.

    Args:
        subject (SubjectData): The participant whose trial results are checked.
        min_age (timedelta): Only recover chunks older than this, so that
            recordings still uploading are left to their merge request.

    """
    fs = FileSystemStorage(location=settings.WEBCAM_ROOT)
    root = Path(settings.WEBCAM_ROOT)
    cutoff = time.time() - min_age.total_seconds()
    results = (
        subject.trialresult_set.filter(Q(webcam_file="") | Q(webcam_file__isnull=True))
        # A pause row shares the interrupted trial's number and label, but that
        # trial never finished; its chunks are discarded when it restarts
        .exclude(key_pressed="PAUSE")
        .select_related("trialitem")
        .order_by("-pk")
    )
    for result in results:
        # The run page prefixes the participant ID, which the run template sets,
        # so match on the part the server knows: _trial<n>_<label>_<uuid>
        suffix = get_valid_filename(
            f"_trial{result.trial_number}_{result.trialitem.label}_{subject.id}"
        )
        chunks = sorted(p.name for p in root.glob(f"*{suffix}-{'[0-9]' * 5}.webm"))
        if not chunks:
            continue
        if min_age and any((root / c).stat().st_mtime > cutoff for c in chunks):
            continue
        target = _unused_name(fs, chunks[0].rsplit("-", 1)[0] + "_partial")
        merge_files(target, chunks)
        result.webcam_file = target
        result.save(update_fields=["webcam_file"])
        logger.info(f"Recovered {len(chunks)} unmerged chunks into {target}.")


def find_files(base_filename):
    """Retrieve uploaded chunk filenames matching the given base filename."""
    root = Path(settings.WEBCAM_ROOT)
    return sorted(p.name for p in root.glob(f"{base_filename}-*"))


def merge_files(target, files):
    """Merge chunk files into a single target file, then delete the chunks.

    An existing target is overwritten. If ``files`` is empty, nothing is
    written and any existing target is left untouched, so a retried merge
    (whose chunks were already merged and deleted) keeps the merged file.
    Chunks are only deleted once the target is fully written.
    """
    if not files:
        return
    root = Path(settings.WEBCAM_ROOT)
    destination = root / target

    if destination.exists():
        destination.unlink()

    with destination.open("wb") as outfile:
        for fname in files:
            with (root / fname).open("rb") as infile:
                shutil.copyfileobj(infile, outfile)
    for fname in files:
        (root / fname).unlink()
