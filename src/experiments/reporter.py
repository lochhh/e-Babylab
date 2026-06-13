"""Result export utilities for generating subject data downloads."""

import contextlib
import datetime
import json
import logging
import math
import os
import re
import shutil
import uuid
import zipfile
from io import StringIO
from typing import NamedTuple

import pandas as pd
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.utils.text import get_valid_filename

from .models import (
    ANSWER_TYPE_MODEL,
    AnswerBase,
    AnswerInteger,
    AnswerText,
    BlockItem,
    CdiResult,
    ConsentQuestion,
    OuterBlockItem,
    Question,
    SubjectData,
    TrialResult,
)

# Create a logger for this file
logger = logging.getLogger(__name__)


class WebgazerSheets(NamedTuple):
    """Pair of DataFrames produced by create_webgazer_worksheet."""

    gaze: "pd.DataFrame"
    validation: "pd.DataFrame"


class Reporter:
    """Utility for generating results as a zip file to be downloaded."""

    def __init__(self, experiment):
        """Initialise the reporter with the experiment to export."""
        self.experiment = experiment

        # Trial columns
        self.trial_columns = [
            "Outer Block",
            "Inner Block",
            "Randomized",
            "Trial Number",
            "Trial Label",
            "Trial Code",
            "Visual Onset (ms)",
            "Audio Onset (ms)",
            "Visual Presented",
            "Audio Presented",
            "Max Duration (ms)",
            "User Input",
            "Response Keys",
            "Nrows",
            "Ncols",
            "Area Clicked (row,col)",
            "Response Time (ms)",
            "Record Media",
            "Webcam File",
            "Screen Width",
            "Screen Height",
            "Record Gaze",
        ]

        # Define report folders
        self.output_file = get_valid_filename(experiment.exp_name + ".zip")
        self.output_folder = settings.REPORTS_ROOT

        # Create random folder
        self.tmp_folder = str(uuid.uuid4())
        os.makedirs(os.path.join(self.output_folder, self.tmp_folder))

        # Create zip file, delete if already exists
        with contextlib.suppress(OSError):
            os.remove(os.path.join(self.output_folder, self.output_file))
        self.zip_file = zipfile.ZipFile(
            os.path.join(self.output_folder, self.output_file),
            "w",
            zipfile.ZIP_DEFLATED,
        )

        # Create webcam directory if it doesn't exist
        if not os.path.exists("webcam"):
            os.makedirs("webcam")

    def calc_trial_duration(self, t1, t2):
        """Calculate trial duration based on the start and end times."""
        if t1 and t2:
            return str(t2 - t1)
        return ""

    def calc_roi_response(self, result, coords):
        """Determine the row and column of a click or gaze within the trial's grid."""
        width = result.resolution_w
        height = result.resolution_h
        boundaries_r = list(range(0, height, int(height / result.trialitem.grid_row)))
        boundaries_r.append(height)
        boundaries_c = list(range(0, width, int(width / result.trialitem.grid_col)))
        boundaries_c.append(width)

        if len(coords) == 2:
            if coords[0] > max(boundaries_c):
                col_num = len(boundaries_c) - 1
            else:
                col_num = next(i for i, c in enumerate(boundaries_c) if c >= coords[0])
            if coords[1] > max(boundaries_r):
                row_num = len(boundaries_r) - 1
            else:
                row_num = next(i for i, r in enumerate(boundaries_r) if r >= coords[1])
            return f"({row_num},{col_num})"
        return ""

    @staticmethod
    def _resolve_answer_value(answer_base, participation_date):
        qt = answer_base.question.question_type
        if qt == Question.AGE:
            answer_text = AnswerText.objects.filter(pk=answer_base.pk).first()
            if answer_text and answer_text.body:
                dob = datetime.date.fromisoformat(answer_text.body)
                age_months = round((participation_date - dob).days / (365 / 12))
                return f"{answer_text.body} ({age_months} mo.)"
            if answer_text:
                return ""
            # Legacy fallback to read age provided in months
            return str(AnswerInteger.objects.get(pk=answer_base.pk).body)
        model = ANSWER_TYPE_MODEL.get(qt)
        return str(model.objects.get(pk=answer_base.pk).body) if model else ""

    def create_subject_worksheet(self, subject):
        """Create a dataframe per subject containing consent and subject form data."""
        gcd = math.gcd(subject.resolution_w, subject.resolution_h) or 1
        aspect = f"{int(subject.resolution_h / gcd)}:{int(subject.resolution_w / gcd)}"
        try:
            subject_data = {
                "Report Date": datetime.datetime.now().strftime("%d.%m.%Y %H:%M:%S"),
                "Experiment Name": subject.experiment.exp_name,
                "Global Timeout": subject.listitem.global_timeout
                if subject.listitem
                else "",
                "List": subject.listitem.list_name if subject.listitem else "",
                "Participant Number": subject.participant_id,
                "Participant UUID": subject.id,
                "Participation Date": subject.created.strftime("%d.%m.%Y %H:%M:%S"),
                "Aspect Ratio": aspect,
                "Resolution": f"{subject.resolution_w}x{subject.resolution_h}",
                "Consent Questions": "",
            }

            consent_qs = ConsentQuestion.objects.filter(
                experiment_id=subject.experiment.id
            )
            for q in consent_qs:
                subject_data[f"{q.position + 1}. {q.text}"] = "Y"

            subject_data["Participant Form Responses"] = ""
            for answer_base in AnswerBase.objects.filter(subject_data_id=subject.id):
                q = answer_base.question
                key = f"{q.position + 1}. {q.text}"
                subject_data[key] = self._resolve_answer_value(
                    answer_base, subject.created.date()
                )

            subject_data["CDI estimate"] = subject.cdi_estimate
            subject_data["CDI instrument"] = (
                subject.experiment.instrument.instr_name
                if subject.experiment.instrument
                else ""
            )
            for cdi_result in CdiResult.objects.filter(subject=subject.id):
                subject_data[cdi_result.given_label] = cdi_result.response
        except ObjectDoesNotExist as e:
            logger.exception("Object does not exist: " + str(e))
            raise
        return pd.DataFrame.from_dict(subject_data, orient="index")

    def _get_trial_results(self, subject):
        """Return (queryset, unique_trial_number) for a subject's trial results.

        unique_trial_number is False when trial_number values repeat, in which
        case callers must derive an ordinal position from the queryset order.
        """
        outer_pks = list(
            OuterBlockItem.objects.filter(
                listitem__pk=subject.listitem.pk
            ).values_list("pk", flat=True)
        )
        block_pks = list(
            BlockItem.objects.filter(
                outerblockitem__pk__in=outer_pks
            ).values_list("pk", flat=True)
        )
        qs = TrialResult.objects.filter(
            trialitem__blockitem__pk__in=block_pks, subject_id=subject.id
        ).order_by("pk", "trial_number")
        trial_numbers = qs.values_list("trial_number", flat=True)
        unique = len(trial_numbers) == len(set(trial_numbers))
        return qs, unique

    def create_trial_worksheet(self, subject):
        """Create a dataframe per subject containing the trial results.

        Also adds the corresponding webcam/audio files to the final zip file.
        """
        trial_data = []
        trial_results, unique_trial_number = self._get_trial_results(subject)
        for result in trial_results:
            audio_file = result.trialitem.audio_file
            coords = list(map(int, re.findall(r"\d+", result.key_pressed)))
            block = result.trialitem.blockitem
            trial_data.append(
                [
                    block.outerblockitem.outer_block_name,
                    block.label,
                    block.randomise_trials,
                    (
                        result.trial_number
                        if unique_trial_number
                        else (trial_results.filter(pk__lt=result.pk).count() + 1)
                    ),
                    result.trialitem.label,
                    result.trialitem.code,
                    result.trialitem.visual_onset,
                    result.trialitem.audio_onset,
                    (
                        result.trialitem.visual_file.original_filename
                        if result.trialitem.visual_file
                        else ""
                    ),
                    (audio_file.original_filename if audio_file else ""),
                    result.trialitem.max_duration,
                    result.trialitem.user_input,
                    result.key_pressed,
                    result.trialitem.grid_row,
                    result.trialitem.grid_col,
                    (
                        self.calc_roi_response(result, coords)
                        if "mouse" in result.key_pressed
                        and (
                            result.trialitem.grid_row != 1
                            or result.trialitem.grid_col != 1
                        )
                        else ""
                    ),
                    self.calc_trial_duration(result.start_time, result.end_time),
                    (
                        block.outerblockitem.listitem.experiment.recording_option
                        in ["AUD", "VID"]
                        and result.trialitem.record_media
                    ),
                    result.webcam_file.name,
                    result.resolution_w,
                    result.resolution_h,
                    (
                        block.outerblockitem.listitem.experiment.recording_option
                        in ["EYE", "ALL"]
                        and result.trialitem.record_gaze
                    ),
                ]
            )

            # Add webcam file to zip
            self.zip_file.write(
                os.path.join("webcam", result.webcam_file.name), result.webcam_file.name
            )

        return pd.DataFrame(trial_data, columns=self.trial_columns)

    def create_webgazer_worksheet(self, subject):
        """Create a worksheet per subject containing the eye-tracking results."""
        trial_results, unique_trial_number = self._get_trial_results(subject)
        validation_frames = []
        webgazer_frames = []
        logger.info(trial_results)
        for result in trial_results:
            # skip trials where gaze is not recorded
            if (not result.trialitem.record_gaze) or (not result.webgazer_data):
                continue
            trial_number = (
                result.trial_number
                if unique_trial_number
                else (trial_results.filter(pk__lt=result.pk).count() + 1)
            )
            if result.trialitem.is_calibration:
                curr_webgazer_data = pd.read_json(
                    StringIO(json.dumps(result.webgazer_data[1:]))
                )
                curr_validation_data = pd.read_json(
                    StringIO(json.dumps(result.webgazer_data[0]))
                ).drop(columns=["trial_type"])
                curr_validation_data.insert(0, "Trial Number", trial_number)
                curr_validation_data.insert(1, "Trial Label", result.trialitem.label)
                curr_validation_data.insert(2, "Trial Code", result.trialitem.code)
                validation_frames.append(curr_validation_data)
            else:
                curr_webgazer_data = pd.read_json(
                    StringIO(json.dumps(result.webgazer_data))
                )
            curr_webgazer_data.insert(0, "Trial Number", trial_number)
            curr_webgazer_data.insert(1, "Trial Label", result.trialitem.label)
            curr_webgazer_data.insert(2, "Trial Code", result.trialitem.code)
            curr_webgazer_data["Nrows"] = result.trialitem.grid_row
            curr_webgazer_data["Ncols"] = result.trialitem.grid_col
            if result.trialitem.grid_row != 1 or result.trialitem.grid_col != 1:
                curr_webgazer_data["Gaze Area (row,col)"] = curr_webgazer_data.apply(
                    lambda x, result=result: self.calc_roi_response(
                        result, [x["x"], x["y"]]
                    ),
                    axis=1,
                )
            else:
                curr_webgazer_data["Gaze Area (row,col)"] = ""
            webgazer_frames.append(curr_webgazer_data)

        gaze = (
            pd.concat(webgazer_frames, ignore_index=True)
            if webgazer_frames
            else pd.DataFrame()
        )
        validation = (
            pd.concat(validation_frames, ignore_index=True)
            if validation_frames
            else pd.DataFrame()
        )
        return WebgazerSheets(gaze=gaze, validation=validation)

    def create_report(self):
        """Create a zip file containing all subjects' results and recordings.

        The .zip file contains an .xlsx report for each subject with their trial results
        and responses to consent and demographic questions, as well as their
        corresponding webcam/audio files for an experiment.
        """
        # For each subject
        subjects = SubjectData.objects.filter(experiment__pk=self.experiment.pk)
        for subject in subjects:
            # Create excel report
            workbook_file = get_valid_filename(
                f"{subject.participant_id}_{self.experiment.exp_name}"
                f"_{subject.created:%Y%m%d}_{subject.id}.xlsx"
            )

            # Create Pandas Excel writer using XlsxWriter as the engine
            writer = pd.ExcelWriter(
                os.path.join(self.output_folder, self.tmp_folder, workbook_file),
                engine="xlsxwriter",
            )

            # Create subject data worksheet
            self.create_subject_worksheet(subject).to_excel(
                writer, sheet_name="Participant", header=False
            )

            if subject.listitem:
                # Create trial data worksheet
                self.create_trial_worksheet(subject).to_excel(
                    writer, sheet_name="Trials", index=False
                )
                if self.experiment.recording_option in ["EYE", "ALL"]:
                    # Create webgazer worksheet
                    sheets = self.create_webgazer_worksheet(subject)
                    sheets.gaze.to_excel(
                        writer, sheet_name="EyeTrackingData", index=False
                    )
                    sheets.validation.to_excel(
                        writer, sheet_name="EyeTrackingValidation", index=False
                    )

            # Close the Pandas Excel writer and store excel report
            writer.close()
            self.zip_file.write(
                os.path.join(self.output_folder, self.tmp_folder, workbook_file),
                workbook_file,
            )

        # Close zip
        self.zip_file.close()

        # Remove tmp folder
        shutil.rmtree(os.path.join(self.output_folder, self.tmp_folder))

        return os.path.join(self.output_folder, self.output_file)
