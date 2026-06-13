"""Views for the experiment participant flow and admin actions."""

import json
import logging
import os.path
from pathlib import Path
from random import shuffle

import requests
from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template import RequestContext, Template
from django.urls import reverse
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_POST

from .admin import ExperimentAdmin
from .decorators import login_required
from .forms import ConsentForm, ImportForm, SubjectDataForm
from .models import (
    BlockItem,
    Experiment,
    ListItem,
    OuterBlockItem,
    SubjectData,
    TrialItem,
    TrialResult,
)
from .reporter import Reporter

# Create a logger for this file
logger = logging.getLogger(__name__)


def _render_tpl(request, tpl_string, context=None):
    return HttpResponse(
        Template(tpl_string).render(RequestContext(request, context or {}))
    )


def proceed_to_experiment(experiment, run_uuid):
    """Redirect to webcam test or experiment run based on the recording option."""
    # skip webcam/microphone test if experiment not configured to record video/audio.
    if experiment.recording_option == "NON" or experiment.recording_option == "EYE":
        return HttpResponseRedirect(
            reverse("experiments:experimentRun", args=(run_uuid,))
        )
    else:  # capture audio/video
        return HttpResponseRedirect(reverse("experiments:webcamTest", args=(run_uuid,)))


@login_required(next_url="/admin/experiments/experiment")
def experiment_report(request, experiment_id):
    """Generate a zip of participant results and webcam/audio data for an experiment."""
    experiment = get_object_or_404(Experiment, pk=experiment_id)

    r = Reporter(experiment)
    filename = r.create_report()
    logger.info(f"Successfully created report with name {filename}.")

    fs = FileSystemStorage(
        location=settings.REPORTS_ROOT, base_url=settings.REPORTS_URL
    )

    return redirect(fs.url(os.path.basename(filename)))


def experiment_export(request, experiment_id):
    """Export an experiment to a JSON file."""
    json_data = ExperimentAdmin.export_to_json(experiment_id)
    response = HttpResponse(json.dumps(json_data), content_type="application/json")
    response["Content-Disposition"] = (
        'attachment; filename="'
        + Experiment.objects.get(id=experiment_id).exp_name
        + '.json"'
    )
    return response


def experiment_import(request):
    """Render the import page or the experiments list after import."""
    if request.method == "POST":
        form = ImportForm(request.POST, request.FILES)
        if form.is_valid():
            json_data = request.FILES["import_file"].read()
            ExperimentAdmin.import_from_json(request, json_data)
            return redirect("/admin/experiments/experiment")
    form = ImportForm()
    return render(request, "admin/experiments/import_form.html", {"form": form})


def information_page(request, experiment_id):
    """Generate the information/welcome page for an experiment."""
    experiment = get_object_or_404(Experiment, pk=experiment_id)
    return _render_tpl(
        request, experiment.information_page_tpl, {"experiment": experiment}
    )


def browser_check(request, experiment_id):
    """Generate the browser check page for an experiment.

    Only Firefox and Chrome are supported.
    """
    experiment = get_object_or_404(Experiment, pk=experiment_id)
    return _render_tpl(
        request, experiment.browser_check_page_tpl, {"experiment": experiment}
    )


def consent_form(request, experiment_id):
    """Generate the consent form of an experiment."""
    experiment = get_object_or_404(Experiment, pk=experiment_id)
    form = ConsentForm(experiment=experiment)
    return _render_tpl(
        request,
        experiment.introduction_page_tpl,
        {"consent_form": form, "experiment": experiment},
    )


def consent_form_submit(request, experiment_id):
    """Validate the consent form of an experiment."""
    experiment = get_object_or_404(Experiment, pk=experiment_id)
    form = ConsentForm(request.POST, experiment=experiment)
    # on submit, require all answers to be yeses to proceed,
    # else render consent fail page
    if form.is_valid():
        for key, value in request.POST.items():
            if key.startswith("question_") and value.lower() == "no":
                return _render_tpl(
                    request,
                    experiment.consent_fail_page_tpl,
                    {"experiment": experiment},
                )
        return HttpResponseRedirect(
            reverse("experiments:subjectForm", args=(experiment_id,))
        )
    return _render_tpl(
        request,
        experiment.introduction_page_tpl,
        {"consent_form": form, "experiment": experiment},
    )


def subject_form(request, experiment_id):
    """Generate the demographic/participant data form of an experiment."""
    experiment = get_object_or_404(Experiment, pk=experiment_id)
    form = SubjectDataForm(experiment=experiment)
    return _render_tpl(
        request,
        experiment.demographic_data_page_tpl,
        {
            "subject_data_form": form,
            "experiment": experiment,
            "recaptcha_site_key": settings.GOOGLE_RECAPTCHA_SITE_KEY,
        },
    )


def subject_form_submit(request, experiment_id):
    """Validate the demographic/participant data form."""
    experiment = get_object_or_404(Experiment, pk=experiment_id)
    form = SubjectDataForm(request.POST, experiment=experiment)

    if form.is_valid():
        # validate reCAPTCHA
        recaptcha_response = request.POST.get("g-recaptcha-response")
        data = {
            "secret": settings.GOOGLE_RECAPTCHA_SECRET_KEY,
            "response": recaptcha_response,
        }
        r = requests.post("https://www.google.com/recaptcha/api/siteverify", data=data)
        result = r.json()

        if not result["success"]:
            logger.info("Invalid reCAPTCHA: " + str(result))
            return _render_tpl(
                request,
                experiment.demographic_data_page_tpl,
                {
                    "subject_data_form": form,
                    "experiment": experiment,
                    "error_message": "Invalid reCAPTCHA. Please try again.",
                    "recaptcha_site_key": settings.GOOGLE_RECAPTCHA_SITE_KEY,
                },
            )
        response = form.save()

        if experiment.instrument:  # administer CDI if instrument is defined
            return HttpResponseRedirect(
                reverse("experiments:vocabChecklist", args=(str(response.id),))
            )
        else:
            return proceed_to_experiment(experiment, str(response.id))

    return _render_tpl(
        request,
        experiment.demographic_data_page_tpl,
        {
            "subject_data_form": form,
            "experiment": experiment,
            "recaptcha_site_key": settings.GOOGLE_RECAPTCHA_SITE_KEY,
        },
    )


def create_trial_dict(trial, block, trial_number):
    """Return a dictionary containing the details of a trial."""
    trial_type = ""

    if trial.visual_file:
        visual_file = trial.visual_file.url
        _video_exts = {".mp4", ".ogg", ".webm"}
        if (
            Path(trial.visual_file.original_filename or "").suffix.lower()
            in _video_exts
        ):
            trial_type = "video"
        else:
            trial_type = "image"
    else:
        visual_file = ""

    audio_file = trial.audio_file.url if trial.audio_file else ""

    if not trial.response_keys:
        trial.response_keys = ""

    trial_dict = {
        "trial_id": trial.id,
        "trial_number": trial_number,
        "background_colour": block.background_colour,
        "label": trial.label,
        "visual_onset": trial.visual_onset,
        "audio_onset": trial.audio_onset,
        "audio_file": audio_file,
        "visual_file": visual_file,
        "max_duration": trial.max_duration,
        "response_keys": trial.response_keys.lower().replace(" ", "").split(","),
        "require_user_input": trial.user_input,  #'NO', 'YES'
        "trial_type": trial_type,
        "record_media": trial.record_media,
        "record_gaze": trial.record_gaze,
        "is_calibration": trial.is_calibration,
        "calibration_points": trial.calibration_points if trial.is_calibration else [],
    }
    return trial_dict


@ensure_csrf_cookie
def experiment_run(request, run_uuid):
    """Generate the (main) experimental task of an experiment."""
    subject_data = get_object_or_404(SubjectData, pk=run_uuid)
    experiment = get_object_or_404(Experiment, pk=subject_data.experiment.pk)
    trials = []
    completed_trials = []
    block_items = []
    loading_image = experiment.loading_image if experiment.loading_image else ""
    trial_number = 1

    try:
        # retrieve a certain list
        if subject_data.listitem is None:
            list_item = experiment.get_list_item()
            subject_data.listitem = list_item
            subject_data.save()
        list_item = subject_data.listitem

        # QuerySet of all outer block items of the list
        outer_block_items = list_item.outerblockitem_set.all().order_by("position")

        # search for existing trial results
        all_trial_results = TrialResult.objects.filter(subject__id=run_uuid)
        trial_number += all_trial_results.count()

        # exclude pause trials
        trial_results = all_trial_results.exclude(key_pressed="PAUSE")
        if trial_results.exists():
            # construct list of completed trials
            for tr in list(trial_results):
                completed_trials.append(
                    get_object_or_404(TrialItem, pk=tr.trialitem.id)
                )

        # retrieve all block items from all outer blocks
        for ob in outer_block_items:
            inner_blocks = list(ob.blockitem_set.all().order_by("position"))

            if ob.randomise_inner_blocks:
                shuffle(inner_blocks)

            block_items += inner_blocks

        # retrieve all trial items from all block items
        for b in block_items:
            trial_items = list(b.trialitem_set.all().order_by("position"))

            if b.randomise_trials:
                shuffle(trial_items)

            # subtract completed trials from trial list
            trial_items = [x for x in trial_items if x not in completed_trials]

            for t in trial_items:
                trials.append(create_trial_dict(t, b, trial_number))
                trial_number += 1

    except (
        KeyError,
        AttributeError,
        OuterBlockItem.DoesNotExist,
        BlockItem.DoesNotExist,
        TrialItem.DoesNotExist,
    ) as e:
        logger.exception("Failed to run experiment: " + str(e))
        return HttpResponseRedirect(
            reverse("experiments:experimentError", args=(run_uuid,))
        )
    else:
        return _render_tpl(
            request,
            experiment.experiment_page_tpl,
            {
                "subject_data": subject_data,
                "loading_image": loading_image,
                "general_onset": experiment.general_onset,
                "global_timeout": list_item.global_timeout,
                "include_pause_page": experiment.include_pause_page,
                "recording_option": experiment.recording_option,
                "show_gaze_estimations": experiment.show_gaze_estimations,
                "trials": json.dumps(trials),
            },
        )


@require_POST
def store_result(request, run_uuid):
    """Store the results of a trial to a TrialResult object."""
    trialresult = TrialResult.objects.create(
        subject=get_object_or_404(SubjectData, pk=run_uuid),
        trialitem=get_object_or_404(TrialItem, pk=int(request.POST.get("trialitem"))),
        start_time=request.POST.get("start_time"),
        end_time=request.POST.get("end_time"),
        key_pressed=request.POST.get("key_pressed"),
        trial_number=int(request.POST.get("trial_number")),
        resolution_w=int(request.POST.get("resolution_w")),
        resolution_h=int(request.POST.get("resolution_h")),
        webgazer_data=json.loads(request.POST.get("webgazer_data")),
    )
    return JsonResponse({"resultId": trialresult.pk})


def experiment_pause(request, run_uuid):
    """Generate the pause page of an experiment."""
    trial_id = None
    subject_data = get_object_or_404(SubjectData, pk=run_uuid)
    experiment = get_object_or_404(Experiment, pk=subject_data.experiment.pk)

    if request.method == "POST":
        trial_id = int(request.POST.get("trialitem"))

    # retrieve completed trials
    all_trial_results = TrialResult.objects.filter(subject=subject_data)
    # retrieve the last trial result as a TrialItem is required
    # for the creation of a TrialResult.
    last_trial_result = (
        all_trial_results.exclude(key_pressed="PAUSE").order_by("-id").first()
    )

    if last_trial_result:  # only store pause as trial result when not the first trial
        TrialResult.objects.create(
            subject=subject_data,
            trialitem=last_trial_result.trialitem,
            key_pressed="PAUSE",
            trial_number=all_trial_results.count() + 1,
        )

    return _render_tpl(
        request,
        experiment.pause_page_tpl,
        {"subject_id": run_uuid, "trial_id": trial_id, "experiment": experiment},
    )


def experiment_error(request, run_uuid):
    """Generate the error page of an experiment."""
    subject_data = get_object_or_404(SubjectData, pk=run_uuid)
    experiment = get_object_or_404(Experiment, pk=subject_data.experiment.pk)
    return _render_tpl(request, experiment.error_page_tpl)


def experiment_end(request, run_uuid):
    """Generate the thank you/end page of an experiment."""
    subject_data = get_object_or_404(SubjectData, pk=run_uuid)
    experiment = get_object_or_404(Experiment, pk=subject_data.experiment.pk)
    tpl = experiment.thank_you_page_tpl

    if subject_data.listitem:
        get_object_or_404(ListItem, pk=subject_data.listitem.pk)
        # count number of trials in the listitem
        # get list of outer block id's
        outer_blocks_all = OuterBlockItem.objects.filter(
            listitem=subject_data.listitem.pk
        ).values_list("id", flat=True)
        # get all inner blocks of the listitem
        blocks_all = BlockItem.objects.filter(outerblockitem__pk__in=outer_blocks_all)

        tr_count = 0

        for bl in blocks_all:
            tr_count += TrialItem.objects.filter(blockitem=bl.pk).count()

        # count participant's number of trial results
        completed_count = (
            TrialResult.objects.filter(subject=run_uuid)
            .exclude(key_pressed="PAUSE")
            .count()
        )

        # if experiment incomplete, render end page after discontinuation
        if completed_count < tr_count:
            tpl = experiment.thank_you_abort_page_tpl

    return _render_tpl(
        request, tpl, {"experiment": experiment, "subject_id": run_uuid}
    )


@require_POST
def delete_subject(request, run_uuid):
    """Delete a participant's results at the end of the experiment."""
    subject_data = get_object_or_404(SubjectData, pk=run_uuid)
    subject_data.delete()
    logger.info(f"Successfully deleted participant {run_uuid}.")
    return HttpResponse(status=204)


def index(request):
    """Generate the homepage."""
    return render(request, "experiments/index.html")
