from django.shortcuts import get_object_or_404, render, redirect
from django.http import HttpResponseRedirect, Http404, JsonResponse, HttpResponse
from django.urls import reverse
from django.views import generic
from django.utils import timezone
from django.conf import settings
from random import shuffle
from django.core.files.storage import FileSystemStorage

from datetime import datetime, date

import dateutil.parser
import simplejson as json
import os.path

from .models import Question, Experiment, SubjectData, ListItem, OuterBlockItem, BlockItem, TrialItem, TrialResult, ConsentQuestion
from .forms import SubjectDataForm, ConsentForm, ImportForm
from .reporter import Reporter
from .admin import ExperimentAdmin
from .decorators import login_required

from django.db.utils import DEFAULT_DB_ALIAS
from django.contrib.admin.utils import NestedObjects


@login_required(next='/admin/experiments/experiment')
def experimentReport(request, experiment_id):
    """ 
    Generates the zip file containing the participants' results and webcam/audio data for an experiment. 
    """
    experiment = get_object_or_404(Experiment, pk=experiment_id)

    r = Reporter(experiment)
    filename = r.create_report()
    print(filename)

    fs = FileSystemStorage(location=settings.REPORTS_ROOT, base_url=settings.REPORTS_URL)

    return redirect(fs.url(os.path.basename(filename)))

def experimentExport(request, experiment_id):
    """
    Exports an experiment to a JSON file
    """
    json_data = ExperimentAdmin.exportToJSON(experiment_id)
    response = HttpResponse(json.dumps(json_data), content_type="application/json")
    response['Content-Disposition'] = 'attachment; filename=\"' + Experiment.objects.get(id=experiment_id).exp_name + '.json\"'
    return response

def experimentImport(request):
    """
    Renders the import page or the experiments list after import.
    """
    if request.method == 'POST':
        form = ImportForm(request.POST, request.FILES)
        if form.is_valid():
            json_data = request.FILES['import_file'].read()
            ExperimentAdmin.importFromJSON(request, json_data)
            return redirect('/admin/experiments/experiment')
    form = ImportForm()
    return render(request, 'admin/experiments/import_form.html', {'form': form})

def informationPage(request, experiment_id):
    """ 
    Generates the first page, the welcome page of an experiment.
    """
    experiment = get_object_or_404(Experiment, pk=experiment_id)

    return render(request, experiment.information_page_tpl.path, {'experiment':experiment})

def browserCheck(request, experiment_id):
    """ 
    Generates the second page, the browser check page of an experiment.
    Only Firefox and Chrome are supported. 
    """
    experiment = get_object_or_404(Experiment, pk=experiment_id)
    return render(request, experiment.browser_check_page_tpl.path, {'experiment':experiment})

def consentForm(request, experiment_id):
    """ 
    Generates the third page, the consent form of an experiment. 
    """
    experiment = get_object_or_404(Experiment, pk=experiment_id)
    form = ConsentForm(experiment=experiment)
    return render(request, experiment.introduction_page_tpl.path, {'consent_form': form, 'experiment': experiment})

def consentFormSubmit(request, experiment_id):
    """ 
    Validates the consent form of an experiment. 
    """
    experiment = get_object_or_404(Experiment, pk=experiment_id)
    form = ConsentForm(request.POST, experiment=experiment)
    # on submit, require all answers to be yeses to proceed, else render consent fail page
    if form.is_valid():
        for key, value in request.POST.items():
            if key.startswith('question_'):
                if value.lower() == 'no':
                    return render(request, experiment.consent_fail_page_tpl.path, {'experiment':experiment})

        return HttpResponseRedirect(reverse('experiments:subjectForm', args=(experiment_id,)))
    return render(request, experiment.introduction_page_tpl.path, {'consent_form': form, 'experiment': experiment})

def subjectForm(request, experiment_id):
    """ 
    Generates the fourth page, the demographic/participant data form of an experiment. 
    """
    experiment = get_object_or_404(Experiment, pk=experiment_id)
    form = SubjectDataForm(experiment=experiment)
    return render(request, experiment.demographic_data_page_tpl.path, {'subject_data_form': form, 'experiment': experiment})

def subjectFormSubmit(request, experiment_id):
    """ 
    Validates the demographic/participant data form. 
    """
    experiment = get_object_or_404(Experiment, pk=experiment_id)
    form = SubjectDataForm(request.POST, experiment=experiment)

    if form.is_valid():
        response = form.save()
        if experiment.recording_option == 'NON': # capture key/click responses only, skip webcam/microphone test.
            return HttpResponseRedirect(reverse('experiments:experimentRun', args = (str(response.id),)))
        else: # capture audio/video
            return HttpResponseRedirect(reverse('experiments:webcamTest', args = (str(response.id),)))

    return render(request, experiment.demographic_data_page_tpl.path, {'subject_data_form': form, 'experiment': experiment})

def createTrialDict(trial, block):
    """ 
    Returns a dictionary containing the details of a trial. 
    """
    trial_type = ''

    if trial.visual_file:
        visual_file = trial.visual_file.url
        vftype = trial.visual_file.filetype
        if 'video' in vftype.lower():
            trial_type = 'video'
        else:
            trial_type = 'image'
    else:
        visual_file = ''

    if trial.audio_file:
        audio_file = trial.audio_file.url
    else:
        audio_file = ''

    if not trial.response_keys:
        trial.response_keys = ''

    trial_dict = {
        'trial_id': trial.id,
        'background_colour': block.background_colour,
        'label': trial.label,
        'visual_onset': trial.visual_onset,
        'audio_onset': trial.audio_onset,
        'audio_file': audio_file,
        'visual_file': visual_file,
        'max_duration': trial.max_duration,
        'response_keys': trial.response_keys.lower().replace(' ', '').split(','),
        'require_user_input': trial.user_input, #'NO', 'YES'
        'trial_type': trial_type
    }
    return trial_dict

def experimentRun(request, run_uuid):
    """ 
    Generates the fifth page, which is the main part of an experiment. 
    """
    subject_data = get_object_or_404(SubjectData, pk=run_uuid)
    experiment = get_object_or_404(Experiment, pk=subject_data.experiment.pk)
    trials = []
    completed_trials = []
    block_items = []
    loading_image = experiment.loading_image if experiment.loading_image else ''

    try:
        # retrieve a certain list
        if subject_data.listitem is None:
            list_item = experiment.get_list_item()
            subject_data.listitem = list_item
            subject_data.save()
        list_item = subject_data.listitem

        # QuerySet of all outer block items of the list
        outer_block_items = list_item.outerblockitem_set.all().order_by('position')

        # search for existing trial results
        trial_results = TrialResult.objects.filter(subject__id=run_uuid).exclude(key_pressed='PAUSE')
        if trial_results.exists():
            # construct list of completed trials
            for tr in list(trial_results):
                completed_trials.append(get_object_or_404(TrialItem, pk=tr.trialitem.id))

        # retrieve all block items from all outer blocks
        for ob in outer_block_items:
            inner_blocks = list(ob.blockitem_set.all().order_by('position'))

            if ob.randomise_inner_blocks:
                shuffle(inner_blocks)
            
            block_items += inner_blocks

        # retrieve all trial items from all block items
        for b in block_items:
            trial_items = list(b.trialitem_set.all().order_by('position'))

            if b.randomise_trials:
                shuffle(trial_items)

            # subtract completed trials from trial list
            trial_items = [x for x in trial_items if x not in completed_trials]

            for t in trial_items:
                trials.append(createTrialDict(t, b))

    except (KeyError, OuterBlockItem.DoesNotExist, BlockItem.DoesNotExist, TrialItem.DoesNotExist):
        return HttpResponseRedirect(reverse('experiments:index'))
    else:
        return render(request, experiment.experiment_page_tpl.path, {
            'subject_data': subject_data,
            'loading_image': loading_image,
            'global_timeout': list_item.global_timeout,
            'include_pause_page': experiment.include_pause_page,
            'recording_option': experiment.recording_option,
            'trials': json.dumps(trials),
            })

def storeResult(request, run_uuid):
    """ 
    Stores the results of a trial to a TrialResult object. 
    """
    if request.method == 'POST':
        trialresult = TrialResult()
        trialresult.subject = get_object_or_404(SubjectData, pk=run_uuid)
        trialresult.trialitem = get_object_or_404(TrialItem, pk=int(request.POST.get('trialitem')))
        trialresult.start_time = dateutil.parser.parse(request.POST.get('start_time'))
        trialresult.end_time = dateutil.parser.parse(request.POST.get('end_time'))
        trialresult.key_pressed = request.POST.get('key_pressed')
        #trialresult.webcam_file = request.POST.get('webcam_file')
        trialresult.trial_number = int(request.POST.get('trial_number'))
        trialresult.resolution_w = int(request.POST.get('resolution_w'))
        trialresult.resolution_h = int(request.POST.get('resolution_h'))
        trialresult.save()
        return JsonResponse({'resultId': trialresult.pk})
    raise Http404("Page not found.")

def experimentPause(request, run_uuid):
    """ 
    Generates the pause page of an experiment.
    """
    trial_id = None
    subject_data = get_object_or_404(SubjectData, pk=run_uuid)
    experiment = get_object_or_404(Experiment, pk=subject_data.experiment.pk)

    if request.method == 'POST':
        trial_id = int(request.POST.get('trialitem'))

    # retrieve TrialItem from the last trial result as a TrialItem is required for the creation of a TrialResult.
    last_trial_result = TrialResult.objects.filter(subject=subject_data).exclude(key_pressed='PAUSE').order_by('-id').first()

    if last_trial_result: # only store pause as trial result when not the first trial
        trialresult = TrialResult()
        trialresult.subject = subject_data
        trialresult.trialitem = last_trial_result.trialitem
        trialresult.key_pressed = 'PAUSE'
        trialresult.save()

    return render(request, experiment.pause_page_tpl.path, {
        'subject_id': run_uuid,
        'trial_id': trial_id,
        'experiment': experiment,
        })

def experimentError(request, run_uuid):
    """ 
    Generates the error page of an experiment. 
    """
    subject_data = get_object_or_404(SubjectData, pk=run_uuid)
    experiment = get_object_or_404(Experiment, pk=subject_data.experiment.pk)

    return render(request, experiment.error_page_tpl.path, {})

def experimentEnd(request, run_uuid):
    """ 
    Generates the thank you / end page of an experiment. 
    """
    subject_data = get_object_or_404(SubjectData, pk=run_uuid)
    experiment = get_object_or_404(Experiment, pk=subject_data.experiment.pk)

    if subject_data.listitem:
        listitem = get_object_or_404(ListItem, pk=subject_data.listitem.pk)
        # count number of trials in the listitem
        # get list of outer block id's
        outer_blocks_all = OuterBlockItem.objects.filter(listitem=subject_data.listitem.pk).values_list('id', flat=True)
        # get all inner blocks of the listitem
        blocks_all = BlockItem.objects.filter(outerblockitem__pk__in=outer_blocks_all)

        tr_count = 0

        for bl in blocks_all:
            tr_count += TrialItem.objects.filter(blockitem=bl.pk).count()

        # count participant's number of trial results
        completed_count = TrialResult.objects.filter(subject=run_uuid).exclude(key_pressed='PAUSE').count()

        # if experiment incomplete, render end page after discontinuation
        if completed_count < tr_count:
            return render(request, experiment.thank_you_abort_page_tpl.path, {
                'experiment':experiment,
                'subject_id': run_uuid})
        return render(request, experiment.thank_you_page_tpl.path, {
            'experiment':experiment,
            'subject_id': run_uuid})
    return render(request, experiment.thank_you_abort_page_tpl.path, {
        'experiment':experiment,
        'subject_id': run_uuid})

def deleteSubject(request, run_uuid):
    """
    Deletes a participant's results at the end of the experiment.
    """

    if request.method == 'POST':
        subject_data = get_object_or_404(SubjectData, pk=run_uuid)
        subject_data.delete()
        # Return success status with no content
        return HttpResponse(status=204)
    else:
        raise Http404("Page not found.")

def index(request):
    """ 
    Generates the homepage, i.e., www.kinderstudien.uni-goettingen.de. 
    """
    return render(request, settings.MEDIA_ROOT + '/uploads/templates/index.html')
