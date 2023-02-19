from django.conf import settings
from django.utils.text import get_valid_filename
from django.core.exceptions import ObjectDoesNotExist
from .models import SubjectData, OuterBlockItem, BlockItem, TrialResult, AnswerBase, AnswerText, AnswerInteger, \
                    Question, AnswerRadio, AnswerSelect, AnswerSelectMultiple, ConsentQuestion, CdiResult

import datetime
import uuid
import os
import zipfile
import xlsxwriter
import shutil
import re
import logging
import pandas as pd
import simplejson as json

# Create a logger for this file
logger = logging.getLogger(__name__)

class Reporter:
    """
    Utility for generating results as a zip file to be downloaded.
    """

    # Trial columns
    trial_columns = [
        'Outer Block',
        'Inner Block',
        'Randomized',
        'Trial Number',
        'Trial Label',
        'Trial Code',
        'Visual Onset (ms)',
        'Audio Onset (ms)',
        'Visual Presented',
        'Audio Presented',
        'Max Duration (ms)',
        'User Input',
        'Response Keys',
        'Nrows',
        'Ncols',
        'Area Clicked (row,col)',
        'Response Time (ms)',
        'Record Media',
        'Webcam File',
        'Screen Width',
        'Screen Height',
        'Record Gaze',
    ]

    def __init__(self, experiment):
        self.experiment = experiment

        # Define report folders
        self.output_file = get_valid_filename(experiment.exp_name + '.zip')
        self.output_folder = settings.REPORTS_ROOT

        # Create random folder
        self.tmp_folder = str(uuid.uuid4())
        os.makedirs(os.path.join(self.output_folder, self.tmp_folder))

        # Create zip file, delete if already exists
        try:
            os.remove(os.path.join(self.output_folder, self.output_file))
        except OSError:
            pass
        self.zip_file = zipfile.ZipFile(os.path.join(self.output_folder, self.output_file),
                                        "w", zipfile.ZIP_DEFLATED)

        # Create webcam directory if it doesn't exist
        if not os.path.exists('webcam'):
            os.makedirs('webcam')


    def calc_trial_duration(self, t1, t2):
        """
        Calculates trial duration based on the start and end times.
        """
        if t1 and t2:
            return str(t2 - t1)
        return ''


    def calc_roi_response(self, result, coords):
        """
        Determines row and col responded to (click/gaze) based on grid size defined for the trial. 
        """
        width = result.resolution_w
        height = result.resolution_h
        boundaries_r = list(range(0, height, int(height/result.trialitem.grid_row)))
        boundaries_r.append(height)
        boundaries_c = list(range(0, width, int(width/result.trialitem.grid_col)))
        boundaries_c.append(width)

        if len(coords) == 2:
            if coords[0] > max(boundaries_c):
                col_num = len(boundaries_c) - 1
            else:
                col_num = next(i for i,c in enumerate(boundaries_c) if c >= coords[0])
            if coords[1] > max(boundaries_r):
                row_num = len(boundaries_r) - 1
            else:
                row_num = next(i for i,r in enumerate(boundaries_r) if r >= coords[1])
            return '({row_num},{col_num})'.format(row_num=row_num, col_num=col_num)
        return ''

    
    def gcd(self, a, b):
        if b == 0:
            return a
        return self.gcd(b, a % b)


    def create_subject_worksheet(self, subject):
        """
        Creates a dataframe for each participant containing the data 
        obtained from the consent form and the demographic/participant data form.
        """
        gcd = self.gcd(subject.resolution_w, subject.resolution_h)
        if gcd == 0:
            gcd = 1
        try:
            subject_data = {
                'Report Date': datetime.datetime.now().strftime("%d.%m.%Y %H:%M:%S"),
                'Experiment Name': subject.experiment.exp_name,
                'Global Timeout': subject.listitem.global_timeout if subject.listitem else '',
                'List': subject.listitem.list_name if subject.listitem else '',
                'Participant Number': subject.participant_id,
                'Participant UUID': subject.id,
                'Participation Date': subject.created.strftime("%d.%m.%Y %H:%M:%S"),
                'Aspect Ratio': '{}:{}'.format(int(subject.resolution_h / gcd),
                                           int(subject.resolution_w / gcd)),
                'Resolution': '{}x{}'.format(subject.resolution_w, subject.resolution_h),
                'Consent Questions': '',
            }
        
            consent_questions = ConsentQuestion.objects.filter(experiment_id=subject.experiment.id)
            for consent_question in consent_questions:
                subject_data[consent_question.text] = 'Y'

            answer_bases = AnswerBase.objects.filter(subject_data_id=subject.id)
            subject_data['Participant Form Responses'] = ''
            for answer_base in answer_bases:
                value = ''
                if answer_base.question.question_type == Question.TEXT:
                    value = str(AnswerText.objects.get(pk=answer_base.pk).body)
                elif answer_base.question.question_type == Question.AGE:
                    if AnswerText.objects.filter(pk=answer_base.pk).first():
                        value = str(AnswerText.objects.get(pk=answer_base.pk).body)
                        dob = datetime.date.fromisoformat(value)
                        value += ' (' + str(round(((subject.created.date() - dob).days)/(365/12))) + ' mo.)'
                    else:
                        value = str(AnswerInteger.objects.get(pk=answer_base.pk).body)
                elif answer_base.question.question_type == Question.INTEGER or answer_base.question.question_type == Question.NUM_RANGE:
                    value = str(AnswerInteger.objects.get(pk=answer_base.pk).body)
                elif answer_base.question.question_type == Question.RADIO or answer_base.question.question_type == Question.SEX:
                    value = str(AnswerRadio.objects.get(pk=answer_base.pk).body)
                elif answer_base.question.question_type == Question.SELECT:
                    value = str(AnswerSelect.objects.get(pk=answer_base.pk).body)
                elif answer_base.question.question_type == Question.SELECT_MULTIPLE:
                    value = str(AnswerSelectMultiple.objects.get(pk=answer_base.pk).body)
                subject_data[answer_base.question.text] = value

            cdi_results = CdiResult.objects.filter(subject=subject.id)
            subject_data['CDI estimate'] = subject.cdi_estimate
            subject_data['CDI instrument'] = subject.experiment.instrument.instr_name if subject.experiment.instrument else ''
            for cdi_result in cdi_results:
                subject_data[cdi_result.given_label] = cdi_result.response
        except ObjectDoesNotExist as e:
            logger.exception('Object does not exist: ' + str(e))
        finally:
            return pd.DataFrame.from_dict(subject_data, orient='index')


    def create_trial_worksheet(self, subject):
        """
        Creates a dataframe per participant containing the trial results
        and adds the corresponding webcam/audio files to the final zip file.
        """
        trial_data = []
        outer_blocks_pk = list(OuterBlockItem.objects.filter(listitem__pk=subject.listitem.pk).values_list('id',flat=True))
        blocks = BlockItem.objects.filter(outerblockitem__pk__in=outer_blocks_pk)
        
        for block in blocks:
            trial_results = TrialResult.objects.filter(trialitem__blockitem__pk=block.pk, subject_id=subject.id).order_by('trial_number', 'pk')
            for result in trial_results:
                audio_file = result.trialitem.audio_file
                coords = list(map(int, re.findall(r'\d+', result.key_pressed)))
                trial_data.append([
                    block.outerblockitem.outer_block_name,
                    block.label,
                    block.randomise_trials,
                    result.trial_number,
                    result.trialitem.label,
                    result.trialitem.code,
                    result.trialitem.visual_onset,
                    result.trialitem.audio_onset,
                    result.trialitem.visual_file.filename,
                    (audio_file.filename if audio_file else ''),
                    result.trialitem.max_duration,
                    result.trialitem.user_input,
                    result.key_pressed,
                    result.trialitem.grid_row,
                    result.trialitem.grid_col,
                    (self.calc_roi_response(result, coords) if 'mouse' in result.key_pressed and (result.trialitem.grid_row != 1 or result.trialitem.grid_col != 1) else ''),
                    self.calc_trial_duration(result.start_time, result.end_time),
                    (block.outerblockitem.listitem.experiment.recording_option in ['AUD', 'VID'] and result.trialitem.record_media),
                    result.webcam_file.name,
                    result.resolution_w,
                    result.resolution_h,
                    (block.outerblockitem.listitem.experiment.recording_option in ['EYE', 'ALL'] and result.trialitem.record_gaze),
                ])
                    
                # Add webcam file to zip
                self.zip_file.write(os.path.join("webcam", result.webcam_file.name),
                                    result.webcam_file.name)
        return pd.DataFrame(trial_data, columns=self.trial_columns)


    def create_webgazer_worksheet(self, subject):
        """
        Creates a worksheet per participant containing the eye-tracking results.
        """
        
        outer_blocks_pk = list(OuterBlockItem.objects.filter(listitem__pk=subject.listitem.pk).values_list('id',flat=True))
        blocks = BlockItem.objects.filter(outerblockitem__pk__in=outer_blocks_pk)
        validation_data = pd.DataFrame()
        webgazer_data = pd.DataFrame()
        
        for block in blocks:
            trial_results = TrialResult.objects.filter(trialitem__blockitem__pk=block.pk, subject_id=subject.id).order_by('trial_number', 'pk')
            for result in trial_results:
                # skip trials where gaze is not recorded
                if not result.trialitem.record_gaze or not result.webgazer_data:
                    continue
                
                if result.trialitem.is_calibration:
                    curr_webgazer_data = pd.read_json(json.dumps(result.webgazer_data[1:]))
                    curr_validation_data = pd.read_json(json.dumps(result.webgazer_data[0])).drop(columns=['trial_type'])
                    curr_validation_data.insert(0, 'trial number', result.trial_number)
                    curr_validation_data.insert(1, 'trial label', result.trialitem.label)
                    validation_data = pd.concat([
                        validation_data, 
                        curr_validation_data,
                    ])
                else:
                    curr_webgazer_data = pd.read_json(json.dumps(result.webgazer_data))
                
                curr_webgazer_data.insert(0, 'trial number', result.trial_number)
                curr_webgazer_data.insert(1, 'trial label', result.trialitem.label)
                curr_webgazer_data['nrows'] = result.trialitem.grid_row
                curr_webgazer_data['ncols'] = result.trialitem.grid_col
                if (result.trialitem.grid_row != 1 or result.trialitem.grid_col != 1):
                    curr_webgazer_data['gaze area'] = curr_webgazer_data.apply(lambda x: self.calc_roi_response(result, [x.x , x.y]), axis=1)
                else:
                    curr_webgazer_data['gaze area'] = ''
                webgazer_data = pd.concat([
                    webgazer_data, 
                    curr_webgazer_data,
                ])
    
        return [webgazer_data, validation_data]


    def create_report(self):
        """
        Creates a zip file containing all participants' results and webcam/audio files for an experiment.
        """
        # For each subject
        subjects = SubjectData.objects.filter(experiment__pk=self.experiment.pk)
        for subject in subjects:

            # Create excel report
            workbook_file = str(subject.participant_id) + '_' + \
                self.experiment.exp_name + '_' + subject.created.strftime('%Y%m%d') + \
                    '_' + subject.id + '.xlsx'
            workbook_file = get_valid_filename(workbook_file)

            # Create Pandas Excel writer using XlsxWriter as the engine
            writer = pd.ExcelWriter(os.path.join(self.output_folder,
                                                 self.tmp_folder, workbook_file),
                                    engine='xlsxwriter')
            
            # Create subject data worksheet
            self.create_subject_worksheet(subject).to_excel(writer, sheet_name='Participant', header=False)

            if subject.listitem:
                # Create trial data worksheet
                self.create_trial_worksheet(subject).to_excel(writer, sheet_name='Trials', index=False)
                if self.experiment.recording_option in ['EYE', 'ALL']:
                    # Create webgazer worksheet
                    webgazer_worksheets = self.create_webgazer_worksheet(subject)
                    webgazer_worksheets[0].to_excel(writer, sheet_name='EyeTrackingData', index=False)
                    webgazer_worksheets[1].to_excel(writer, sheet_name='EyeTrackingValidation', index=False)
            
            # Close the Pandas Excel writer and store excel report
            writer.save()
            self.zip_file.write(os.path.join(self.output_folder,
                                             self.tmp_folder, workbook_file),
                                workbook_file)

        # Close zip
        self.zip_file.close()

        # Remove tmp folder
        shutil.rmtree(os.path.join(self.output_folder, self.tmp_folder))

        return os.path.join(self.output_folder, self.output_file)