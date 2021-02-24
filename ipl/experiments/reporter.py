import uuid
import os
import zipfile
import xlsxwriter
import shutil
import datetime

from .models import SubjectData, OuterBlockItem, BlockItem, TrialResult, AnswerBase, AnswerText, AnswerInteger, \
                    Question, AnswerRadio, AnswerSelect, AnswerSelectMultiple, ConsentQuestion
from django.conf import settings
from django.utils.text import get_valid_filename

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
        'Visual Onset (ms)',
        'Audio Onset (ms)',
        'Start Time',
        'End Time',
        'Visual Presented',
        'Audio Presented',
        'Max Duration',
        'User Input',
        'Response Keys',
        'Response Time',
        'Webcam File'
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

    def write_trial_columns(self, worksheet):
        """
        Writes column headers to worksheet.
        """
        for index, column in enumerate(self.trial_columns):
            worksheet.write(0, index, column)

    def calc_trial_duration(self, t1, t2):
        """
        Calculates trial duration based on the start and end times.
        """
        if t1 and t2:
            return str(t2 - t1)
        return ''

    def gcd(self, a, b):
        if b == 0:
            return a
        return self.gcd(b, a % b)

    def create_subject_worksheet(self, worksheet, subject):
        """
        Creates a worksheet for each participant containing the data 
        obtained from the consent form and the demographic/participant data form.
        """
        gcd = self.gcd(subject.resolution_w, subject.resolution_h)
        if gcd == 0:
            gcd = 1

        subject_data = {
            'Report Date': datetime.datetime.now().strftime("%d.%m.%Y %H:%M:%S"),
            'Experiment Name': subject.experiment.exp_name,
            'Global Timeout': subject.listitem.global_timeout,
            'List': subject.listitem.list_name,
            'Aspect Ratio': '{}:{}'.format(int(subject.resolution_h / gcd),
                                           int(subject.resolution_w / gcd)),
            'Resolution': '{}x{}'.format(subject.resolution_w, subject.resolution_h),
            'Subject Date': subject.created.strftime("%d.%m.%Y %H:%M:%S"),
            'Consent Questions': '',
        }

        consent_questions = ConsentQuestion.objects.filter(experiment_id=subject.experiment.id)
        for consent_question in consent_questions:
            subject_data[consent_question.text] = 'Y'

        answer_bases = AnswerBase.objects.filter(subject_data_id=subject.id)
        for answer_base in answer_bases:
            value = ''
            if answer_base.question.question_type == Question.TEXT:
                value = str(AnswerText.objects.get(pk=answer_base.pk).body)
            elif answer_base.question.question_type == Question.INTEGER:
                value = str(AnswerInteger.objects.get(pk=answer_base.pk).body)
            elif answer_base.question.question_type == Question.RADIO:
                value = str(AnswerRadio.objects.get(pk=answer_base.pk).body)
            elif answer_base.question.question_type == Question.SELECT:
                value = str(AnswerSelect.objects.get(pk=answer_base.pk).body)
            elif answer_base.question.question_type == Question.SELECT_MULTIPLE:
                value = str(AnswerSelectMultiple.objects.get(pk=answer_base.pk).body)
            subject_data[answer_base.question.text] = value

        current_row = 0
        for key in subject_data:
            worksheet.write(current_row, 0, key)
            worksheet.write(current_row, 1, subject_data[key])
            current_row += 1

    def create_trial_worksheet(self, worksheet, subject):
        """
        Creates a worksheet per participant containing the trial results
        and adds the corresponding webcam/audio files to the final zip file.
        """
        self.write_trial_columns(worksheet)
        current_row = 1
        
        outer_blocks_pk = list(OuterBlockItem.objects.filter(listitem__pk=subject.listitem.pk).values_list('id',flat=True))
        blocks = BlockItem.objects.filter(outerblockitem__pk__in=outer_blocks_pk)

        for block in blocks:
            trial_results = TrialResult.objects.filter(trialitem__blockitem__pk=block.pk, subject_id=subject.id).order_by('trial_number', 'pk')
            for result in trial_results:
                worksheet.write(current_row, 0, block.outerblockitem.outer_block_name)
                worksheet.write(current_row, 1, block.label)
                worksheet.write(current_row, 2, block.randomise_trials)
                worksheet.write(current_row, 3, result.trial_number)
                worksheet.write(current_row, 4, result.trialitem.label)
                worksheet.write(current_row, 5, result.trialitem.visual_onset)
                worksheet.write(current_row, 6, result.trialitem.audio_onset)
                worksheet.write(current_row, 7, result.start_time.strftime("%H:%M:%S") if result.start_time else '')
                worksheet.write(current_row, 8, result.end_time.strftime("%H:%M:%S") if result.end_time else '')
                worksheet.write(current_row, 9, result.trialitem.visual_file.filename)
                audio_file = result.trialitem.audio_file
                worksheet.write(current_row, 10, audio_file.filename if audio_file else '')
                worksheet.write(current_row, 11, result.trialitem.max_duration)
                worksheet.write(current_row, 12, result.trialitem.user_input)
                worksheet.write(current_row, 13, result.key_pressed)
                worksheet.write(current_row, 14, self.calc_trial_duration(result.start_time, result.end_time))
                worksheet.write(current_row, 15, result.webcam_file.name)

                # Add webcam file to zip
                self.zip_file.write(os.path.join("webcam", result.webcam_file.name),
                                    result.webcam_file.name)
                current_row += 1


    def create_report(self):
        """
        Creates a zip file containing all participants' results and webcam/audio files for an experiment.
        """
        # For each subject
        subjects = SubjectData.objects.filter(experiment__pk=self.experiment.pk)
        for subject in subjects:

            # Skip subject that don't have a list
            if not subject.listitem_id:
                continue

            # Create excel report
            workbook_file = str(subject.participant_id) + '_' + \
                self.experiment.exp_name + '_' + subject.created.strftime('%Y%m%d') + \
                    '_' + subject.id + '.xlsx'
            workbook_file = get_valid_filename(workbook_file)
            workbook = xlsxwriter.Workbook(os.path.join(self.output_folder,
                                                        self.tmp_folder, workbook_file))

            subject_worksheet = workbook.add_worksheet('Participant')
            trials_worksheet = workbook.add_worksheet('Trials')

            # Create subject data worksheet
            self.create_subject_worksheet(subject_worksheet, subject)

            # Create trial data worksheet
            self.create_trial_worksheet(trials_worksheet, subject)

            # Close and store excel report
            workbook.close()
            self.zip_file.write(os.path.join(self.output_folder,
                                             self.tmp_folder, workbook_file),
                                workbook_file)

        # Close zip
        self.zip_file.close()

        # Remove tmp folder
        shutil.rmtree(os.path.join(self.output_folder, self.tmp_folder))

        return os.path.join(self.output_folder, self.output_file)
