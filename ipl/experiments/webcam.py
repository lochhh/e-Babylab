import os.path
import uuid
import re

from django.shortcuts import get_object_or_404, render
from django.http import Http404, JsonResponse, HttpResponse, HttpResponseRedirect
from django.urls import reverse
from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.utils.text import get_valid_filename
from django.template import Template, RequestContext

from .models import SubjectData, TrialResult, Experiment

def webcam_test(request, run_uuid):
    """
    Generates webcam/microphone test page.
    """
    subject_data = get_object_or_404(SubjectData, pk=run_uuid)
    experiment = get_object_or_404(Experiment, pk=subject_data.experiment.pk)
    c = RequestContext(request, {'subject_data': subject_data, 'experiment': experiment,})
    
    if experiment.recording_option == 'VID':
        t = Template(experiment.webcam_check_page_tpl)
    elif experiment.recording_option == 'AUD': # audio
        t = Template(experiment.microphone_check_page_tpl)  
    else: # no recording required
        return HttpResponseRedirect(reverse('experiments:experimentRun', args = (str(run_uuid),)))
    #return render(request, experiment.webcam_check_page_tpl.path, {'subject_data': subject_data, 'experiment': experiment,})
    return HttpResponse(t.render(c))

def webcam_test_upload(request, run_uuid):
    """
    Uploads the webcam/microphone test file and returns metadata of the uploaded file.
    """
    # TODO: Delete video in following step
    # TODO: Add property to subject_data that webcam test was succesful

    if request.method == 'POST' and request.FILES.get('file'):
        subject_data = get_object_or_404(SubjectData, pk=run_uuid)

        webcam_file = request.FILES.get('file')
        webcam_file_type = request.POST.get("type")

        fs = FileSystemStorage(
            location=settings.WEBCAM_TEST_ROOT, base_url=settings.WEBCAM_TEST_URL)

        # Generate random file name
        extension = os.path.splitext(webcam_file.name)[1]
        random_file_name = str(uuid.uuid4()) + extension
        filename = fs.save(random_file_name, webcam_file)

        # Return metadata of uploaded video
        return JsonResponse({'videoUrl': fs.url(filename), 'size': fs.size(filename), 'type': webcam_file_type, 'runUuid': run_uuid})
    else:
        raise Http404("Page not found.")


def webcam_upload(request, run_uuid):
    """
    Receives upload requests for video/audio chunks during the experiment and
    merges these chunks into a file.
    """

    fs = FileSystemStorage(location=settings.WEBCAM_ROOT)

    # Upload request
    if request.method == 'POST' and request.FILES.get('file'):
        webcam_file = request.FILES.get('file')
        # webcam_file_type = request.POST.get("type")

        # Delete existing file
        if fs.exists(webcam_file.name):
            fs.delete(webcam_file.name)

        fs.save(get_valid_filename(webcam_file.name), webcam_file)

        return HttpResponse(status=204)

    # Merge request
    elif request.method == 'POST' and request.POST.get("trialResultId"):
        # Get base filename, by removing chunk number at the end
        base_filename = request.POST.get("filename")
        base_filename = get_valid_filename(base_filename)
        print("Received last file of %s, merge files" % base_filename)

        # Find and merge individual chunks
        webcam_files = find_files(base_filename)
        merge_files(base_filename + ".webm", webcam_files)

        # Delete chunks
        for webcam_file in webcam_files:
            fs.delete(webcam_file)

        # Add filename to trial result
        trial_result_id = 0
        try:
            trial_result_id = int(request.POST.get("trialResultId"))
        except ValueError:
            raise Http404("Invalid trialResultId.")
        trial_result = get_object_or_404(TrialResult, pk=trial_result_id, subject=run_uuid)
        trial_result.webcam_file = base_filename + ".webm"
        trial_result.save()

        return HttpResponse(status=204)

    else:
        raise Http404("Page not found.")


def find_files(base_filename):
    """
    Retrieves uploaded chunks for merging. 
    """
    result = []
    for fname in os.listdir(settings.WEBCAM_ROOT):
        if fname.startswith(base_filename + "-"):
            result.append(fname)

    # Sort alphabetically
    result.sort()

    return result

def merge_files(target, files):
    """
    Merges chunks into a file.
    """
    fs = FileSystemStorage(location=settings.WEBCAM_ROOT)

    destination_file = os.path.join(
        settings.WEBCAM_ROOT, target)

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
