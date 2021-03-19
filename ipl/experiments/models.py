from django.utils import timezone
from django.db import models
from django.db.models import Max
from django.contrib.auth.models import User
from django.dispatch import receiver
from django.conf import settings
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError

from colorfield.fields import ColorField
from filebrowser.fields import FileBrowseField
from tinymce import models as tinymce_models

from .template_defaults import *

import datetime
import uuid
import os
import random


def experiment_folder(instance, filename):
    return '/'.join(['uploads', 'experiments', instance.exp_name, filename])

instrument_folder = 'instruments'

class Instrument(models.Model):
    instr_name = models.CharField('instrument name', max_length=200)
    words_list = FileBrowseField(max_length=250, directory=instrument_folder, extensions=['.csv'], help_text='Only .csv files are supported.')
    irt_params = FileBrowseField('IRT parameters', max_length=250, directory=instrument_folder, extensions=['.csv'], help_text='Only .csv files are supported.')
    f_lm_np_mean = FileBrowseField('NP: M (female)', max_length=250, directory=instrument_folder, extensions=['.csv'], help_text='Only .csv files are supported.')
    f_lm_np_sd = FileBrowseField('NP: SD (female)', max_length=250, directory=instrument_folder, extensions=['.csv'], help_text='Only .csv files are supported.')
    f_lm_p_mean = FileBrowseField('P: M (female)', max_length=250, directory=instrument_folder, extensions=['.csv'], help_text='Only .csv files are supported.')
    f_lm_p_sd = FileBrowseField('P: SD (female)', max_length=250, directory=instrument_folder, extensions=['.csv'], help_text='Only .csv files are supported.')
    f_bmin = FileBrowseField('BMin (female)', max_length=250, directory=instrument_folder, extensions=['.csv'], help_text='Only .csv files are supported.')
    f_slope = FileBrowseField('Slope (female)', max_length=250, directory=instrument_folder, extensions=['.csv'], help_text='Only .csv files are supported.')
    m_lm_np_mean = FileBrowseField('NP: M (male)', max_length=250, directory=instrument_folder, extensions=['.csv'], help_text='Only .csv files are supported.')
    m_lm_np_sd = FileBrowseField('NP: SD (male)', max_length=250, directory=instrument_folder, extensions=['.csv'], help_text='Only .csv files are supported.')
    m_lm_p_mean = FileBrowseField('P: M (male)', max_length=250, directory=instrument_folder, extensions=['.csv'], help_text='Only .csv files are supported.')
    m_lm_p_sd = FileBrowseField('P: SD (male)', max_length=250, directory=instrument_folder, extensions=['.csv'], help_text='Only .csv files are supported.')
    m_bmin = FileBrowseField('BMin (male)', max_length=250, directory=instrument_folder, extensions=['.csv'], help_text='Only .csv files are supported.')
    m_slope = FileBrowseField('Slope (male)', max_length=250, directory=instrument_folder, extensions=['.csv'], help_text='Only .csv files are supported.')

    def __str__(self):
        return self.instr_name


class Experiment(models.Model):
    """
    The first and outermost layer of an experiment where the general settings are defined.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    exp_name = models.CharField('experiment name', max_length=200)
    created_on = models.DateTimeField('date created')
    PRIVATE = 'OWN'
    MEMBERSONLY = 'GRP'
    PUBLIC = 'PUB'

    SHARING_OPTIONS = (
     (PRIVATE,'Only me'),
     (MEMBERSONLY,'Group members only'),
     (PUBLIC,'Everyone'),
    )
    sharing_option = models.CharField('sharing options', max_length=3, choices=SHARING_OPTIONS, default=PRIVATE)
    sharing_groups = models.ManyToManyField(Group, blank=True)
    LEASTPLAYED = 'LPF'
    SEQUENTIAL = 'SEQ'
    RANDOM = 'RAN'

    LIST_SELECTION_STRATEGIES = (
     (LEASTPLAYED,'Least played'),
     (SEQUENTIAL,'Sequential'),
     (RANDOM,'Random'),
    )
    list_selection_strategy = models.CharField('list selection strategy', max_length=3, choices=LIST_SELECTION_STRATEGIES, default=LEASTPLAYED)
    include_pause_page = models.BooleanField(default=True, help_text='When global timeout is encountered / exit button is pressed, go to pause page instead of ending experiment immediately.')
    loading_image = FileBrowseField(max_length=200, directory=experiment_folder, extensions=['.jpg','.jpeg','.gif','.png'], blank=True, help_text='Shown at the end of the experiment, if media recordings are still being uploaded.')
    VIDEO = 'VID'
    AUDIO = 'AUD'
    NONE = 'NON'

    RECORDING_OPTIONS = (
     (VIDEO,'Video'),
     (AUDIO,'Audio only'),
     (NONE,'Key/Click responses only'),
    )
    recording_option = models.CharField(max_length=3, choices=RECORDING_OPTIONS, default=VIDEO)
    general_onset = models.IntegerField('wait to enable key/click response (ms)', default=0)
    
    # Templates
    information_page_tpl = tinymce_models.HTMLField('welcome page template', default=information_page_content)
    browser_check_page_tpl = tinymce_models.HTMLField('browser check page template', default=browser_check_page_content)
    introduction_page_tpl = tinymce_models.HTMLField('consent form template', default=introduction_page_content)
    consent_fail_page_tpl = tinymce_models.HTMLField('consent failed page template', default=consent_fail_page_content)
    demographic_data_page_tpl = tinymce_models.HTMLField('demographic data page template', default=demographic_data_page_content)
    cdi_page_tpl = tinymce_models.HTMLField('CDI page template', default=cdi_page_content)
    webcam_check_page_tpl = tinymce_models.HTMLField('webcam check page template (ignore if not applicable)', default=webcam_check_page_content)
    microphone_check_page_tpl = tinymce_models.HTMLField('microphone check page template (ignore if not applicable)', default=microphone_check_page_content)
    experiment_page_tpl = tinymce_models.HTMLField('experiment page template', default=experiment_page_content)
    pause_page_tpl = tinymce_models.HTMLField('pause page template', default=pause_page_content)
    thank_you_page_tpl = tinymce_models.HTMLField('standard end page template', default=thank_you_page_content)
    thank_you_abort_page_tpl = tinymce_models.HTMLField('end page after discontinuation template', default=thank_you_abort_page_content)
    error_page_tpl = tinymce_models.HTMLField('error page template', default=error_page_content)

    # CDI
    instrument = models.ForeignKey(Instrument, on_delete=models.CASCADE, null=True, blank=True)
    COMP = 'COMP'
    PROD = 'PROD'
    
    ASSESSMENT_TYPES = (
     (COMP,'Comprehension'),
     (PROD,'Production'),
    )
    assess_type = models.CharField('assessment type', max_length=4, choices=ASSESSMENT_TYPES, default=COMP)
    num_words = models.IntegerField('vocabulary checklist length', default=25)
    typical_dev = models.BooleanField('for typically-developing children', default=True, help_text='Uncheck this box if experiment involves non-typically developing children.')
    
    def __str__(self):
        return self.exp_name

    def subject_questions(self):
        """
        Returns a Queryset of all questions added to the participant/demographic data form.
        """
        if self.pk:
            return Question.objects.filter(experiment=self.pk).order_by('position')
        else:
            return None

    def consent_questions(self):
        """
        Returns a Queryset of all questions added to the consent form.
        """
        if self.pk:
            return ConsentQuestion.objects.filter(experiment=self.pk).order_by('position')
        else:
            return None

    def get_list_item(self):
        """
        Selects a ListItem based on the list selection strategy (least played first / sequential / random) of an experiment.
        """
        if self.pk:
            li_all = ListItem.objects.filter(experiment=self.pk).filter(exclude_list=False)

            if not li_all.exists():
                return None

            # get a flattened list of all ListItem ID's
            li_all_id = list(li_all.order_by('id').values_list('id',flat=True))

            if (self.list_selection_strategy == 'LPF'): # least played list
                li_count = {}
                # for each list item, count subject data
                for li in li_all:
                    li_count[li.pk] = SubjectData.objects.filter(listitem=li.pk).count()
                lowest_li = min(li_count, key=li_count.get)
                return ListItem.objects.get(pk=lowest_li) # returns listitem with lowest count
            elif (self.list_selection_strategy == 'SEQ'): # select list in a sequential order
                # get newest subject with non-null list item
                subject = SubjectData.objects.filter(experiment=self.pk).exclude(listitem__isnull=True).order_by('-participant_id').first()
                if subject:
                    index = li_all_id.index(subject.listitem.id) + 1
                    if index < len(li_all_id):
                        return ListItem.objects.get(pk=li_all_id[index]) # get subsequent list
                return li_all.order_by('id').first()  # return list with lowest id
            else: # randomly select listitem
                return ListItem.objects.get(pk=random.choice(li_all_id))
        else:
            return None


class ListItem(models.Model):
    """
    The second layer of an experiment that allows for variations of an experiment.

    An experiment is made up of at least one list. 
    """
    experiment = models.ForeignKey(Experiment, on_delete=models.CASCADE)
    list_name = models.CharField(max_length=20)
    global_timeout = models.IntegerField('global timeout (ms)', default=300000)
    exclude_list = models.BooleanField('do not include this list', default=False)

    def __str__(self):
        return self.list_name


class OuterBlockItem(models.Model):
    """
    The third layer of an experiment.

    The outer block has a fixed order and will hence be presented according to the position number.
    Each list is made up of at least one outer block. 
    """
    listitem = models.ForeignKey(ListItem, on_delete=models.CASCADE)
    outer_block_name = models.CharField(max_length=20)
    position = models.PositiveSmallIntegerField("Position", null=True)
    randomise_inner_blocks = models.BooleanField(default=False)

    class Meta:
        ordering = ['position']

    def __str__(self):
        return self.outer_block_name


class BlockItem(models.Model):
    """
    The fourth layer of an experiment and can be seen as the inner block.

    The order of (inner) blocks can either be fixed or randomised, depending on the outer block settings.
    Each (inner) block is made up of at least one trial. 
    """
    outerblockitem = models.ForeignKey(OuterBlockItem, on_delete=models.CASCADE)
    label = models.CharField(max_length=20)
    comment = models.TextField(blank=True, null=True)
    background_colour = ColorField(default='#FFFFFF')
    randomise_trials = models.BooleanField(default=False)
    position = models.PositiveSmallIntegerField("Position", null=True)

    class Meta:
        ordering = ['position']

    def __str__(self):
        return self.label


def visual_folder(instance, filename):
    return '/'.join(['uploads', instance.blockitem.listitem.experiment.exp_name,
          instance.blockitem.listitem.list_name, 'visual', filename])


def audio_folder(instance, filename):
    return '/'.join(['uploads', instance.blockitem.listitem.experiment.exp_name,
          instance.blockitem.listitem.list_name, 'audio', filename])


class TrialItem(models.Model):
    """
    The fifth and innermost layer of an experiment.

    The order of trials can either be fixed or randomised, depending on the (inner) block settings.
    """
    NO = 'NO'
    YES = 'YES'

    USER_INPUT_OPTIONS = (
     (NO,'Do not require user input'),
     (YES,'Require user input'),
    )

    blockitem = models.ForeignKey(BlockItem, on_delete=models.CASCADE)
    label = models.CharField(max_length=20)
    code = models.CharField(max_length=20)
    visual_onset = models.IntegerField('visual onset (ms)', default=0)
    audio_onset = models.IntegerField('audio onset (ms)', default=0)
    audio_file = FileBrowseField(max_length=200, directory=experiment_folder, extensions= ['.mp3','.wav'], blank=True)
    visual_file = FileBrowseField(max_length=200, directory=experiment_folder, extensions=['.jpg','.jpeg','.gif','.png', '.mp4', '.ogg', '.webm'])
    user_input = models.CharField(max_length=3, choices=USER_INPUT_OPTIONS, default=NO)
    response_keys = models.CharField('response key(s)', max_length=200, blank=True, null=True, help_text='Provide a comma-separated list if multiple response keys are allowed (e.g., click, up, down, left, right, a, b)')
    max_duration = models.IntegerField('maximum duration (ms)', help_text='This value will be ignored for video trials which do not require user input.')
    record_media = models.BooleanField(default=True, help_text='This value will be ignored if the experiment is set to record key/click responses only.')
    grid_row = models.IntegerField('rows', default = 1)
    grid_col = models.IntegerField('columns', default = 1)
    position = models.PositiveSmallIntegerField("Position", null=True)

    class Meta:
        ordering = ['position']

    def __str__(self):
        return self.label


class SubjectData(models.Model):
    """
    A SubjectData is the participant data and is linked to trial results (TrialResult) 
    and answers given in the participant data form (AnswerBase). 
    """
    #id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    id = models.CharField('Unique ID', primary_key=True, max_length=36)
    participant_id = models.IntegerField('Participant Number', blank=True, null=True)
    cdi_estimate = models.FloatField(null=True, blank=True, default=None)
    experiment = models.ForeignKey(Experiment, on_delete=models.PROTECT)
    listitem = models.ForeignKey(ListItem, on_delete=models.PROTECT, blank=True, null=True)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    resolution_w = models.IntegerField('Resolution Width', default=0)
    resolution_h = models.IntegerField('Resolution Height', default=0)

    class Meta:
        verbose_name = "Participant data"
        verbose_name_plural = "Participant data"
    def __str__(self):
        return "%s" % (self.id)


class TrialResult(models.Model):
    """
    A TrialResult is the data collected for a trial.
    """
    subject = models.ForeignKey(SubjectData, on_delete=models.CASCADE)
    trialitem = models.ForeignKey(TrialItem, on_delete=models.PROTECT)
    date = models.DateField(auto_now_add=True)
    start_time = models.DateTimeField(blank=True, null=True)
    end_time = models.DateTimeField(blank=True, null=True)
    key_pressed = models.CharField(blank=True, null=True, max_length=255)
    webcam_file = models.FileField(upload_to=visual_folder, blank=True, null=True)
    trial_number = models.IntegerField(default=0)
    resolution_w = models.IntegerField('Resolution width', default=0)
    resolution_h = models.IntegerField('Resolution height', default=0)

    @property
    def filename(self):
        """
        Returns webcam/audio file name
        """
        return os.path.basename(self.webcam_file.name)


def _delete_file(path):
   """ 
   Deletes file from filesystem. 
   """
   if os.path.isfile(path):
       os.remove(path)

@receiver(models.signals.post_delete, sender=TrialResult, dispatch_uid='webcamfile_delete_signal')
def delete_file(sender, instance, *args, **kwargs):
    """ 
    Deletes webcam file on `post_delete` 
    """
    if instance.webcam_file.name:
        _delete_file(os.path.join(settings.WEBCAM_ROOT, instance.webcam_file.name))

def validate_list(value):
    """
    Takes a text value and verifies that there is at least 1 comma.
    """
    # split by comma and remove empty strings
    values = list(filter(None, [x.strip() for x in value.split(',')]))
    if len(values) < 2:
        raise ValidationError({'choices':('The selected question type requires an associated list of choices. Choices must contain more than one item.')})

def validate_range(value):
    """
    Takes a text value and verifies that the min and max values are valid.
    """
    try: 
        # split by comma and remove empty strings
        values = list(filter(None, [x.strip() for x in value.split(',')]))
        if len(values) != 2:
            raise ValidationError({'choices':('The selected question type requires a minimum and a maximum value.')})
        
        # convert list to integers
        min_max = list(map(int, values))
        if min_max[0] >= min_max[1]:
            raise ValidationError({'choices':('The minimum value must be greater than the maximum value.')})
    except ValueError:
        raise ValidationError({'choices':('The values can only be integers.')})

class Question(models.Model):
    """
    Used in the demographic/participant data form.

    This can be 1 of 8 different types.
    """
    TEXT = 'text'
    RADIO = 'radio'
    SELECT = 'select'
    SELECT_MULTIPLE = 'select-multiple'
    INTEGER = 'integer'
    NUM_RANGE = 'number-range'
    AGE = 'age'
    SEX = 'sex'

    QUESTION_TYPES =(
     (TEXT, 'text'),
     (RADIO, 'radio'),
     (SELECT, 'select'),
     (SELECT_MULTIPLE, 'select multiple'),
     (INTEGER, 'integer'),
     (NUM_RANGE, 'integer range'),
     (AGE, 'age'),
     (SEX, 'sex'),
    )

    text = models.TextField()
    required = models.BooleanField()
    experiment = models.ForeignKey(Experiment, on_delete=models.CASCADE)
    question_type = models.CharField(max_length=200, choices=QUESTION_TYPES, default=TEXT)
    choices = models.TextField(blank=True, null=True, help_text='For types "radio", "select", and "select multiple", provide a comma-separated list of options (e.g., a, b, c). For types "integer range" and "age", provide the min and max integers (e.g., 1, 10). For type "sex", provide the female followed by the male display text (e.g., female, male).')
    position = models.PositiveSmallIntegerField("Position", null=True)

    class Meta:
        ordering = ['position']

    def clean(self):
        if (self.question_type == Question.RADIO or self.question_type == Question.SELECT or self.question_type == Question.SELECT_MULTIPLE or self.question_type == Question.SEX):
            validate_list(self.choices)
        if self.question_type == Question.NUM_RANGE or self.question_type == Question.AGE:
            validate_range(self.choices)

    def get_choices(self):
        """
        Parse the choices field and return a tuple formatted appropriately for the 'choices' argument of a form widget.
        """
        choices = self.choices.split(',')
        choices_list = []
        for c in choices:
            c = c.strip()
            if c != "":
                choices_list.append((c,c))
        choices_tuple = tuple(choices_list)
        return choices_tuple

    def __str__(self):
        return self.text


class AnswerBase(models.Model):
    """
    The base class for the different answer types used in the demographic/participant data form.

    As with the Question model, an Answer can be 1 of 5 different types.
    """
    question = models.ForeignKey(Question, on_delete=models.PROTECT)
    subject_data = models.ForeignKey(SubjectData, on_delete=models.CASCADE)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)


# these type-specific answer models use a text field to allow for flexible
# field sizes, depending on the question the answer corresponds to.
# any "required" attribute will be enforced by the form.
class AnswerText(AnswerBase):
    """
    Answer for text-type Question.
    """
    body = models.TextField(blank=True, null=True)


class AnswerRadio(AnswerBase):
    """
    Answer for radio-type Question.
    """
    body = models.TextField(blank=True, null=True)


class AnswerSelect(AnswerBase):
    """
    Answer for select-type Question.
    """
    body = models.TextField(blank=True, null=True)


class AnswerSelectMultiple(AnswerBase):
    """
    Answer for multiselect-type Question.
    """
    body = models.TextField(blank=True, null=True)


class AnswerInteger(AnswerBase):
    """
    Answer for integer-type Question.
    """
    body = models.IntegerField(blank=True, null=True)


class ConsentQuestion(models.Model):
    """
    This has no answer models as it is a Y/N question in the consent form.
    """
    text = models.TextField()
    experiment = models.ForeignKey(Experiment, on_delete=models.CASCADE)
    position = models.PositiveSmallIntegerField('Position', null=True)
    response_yes = models.CharField('yes', max_length=50, default='Ja')
    response_no = models.CharField('no', max_length=50, default='Nein')

    class Meta:
        ordering = ['position']

    def __str__(self):
        return self.text


class CdiResult(models.Model):
    """
    A CdiResult is the response for a CDI item.
    """
    subject = models.ForeignKey(SubjectData, on_delete=models.CASCADE)
    given_label = models.CharField('item', blank=True, null=True, max_length=255)
    response = models.BooleanField(blank=True, null=True)
