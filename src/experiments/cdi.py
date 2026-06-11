"""Adaptive short CDI-IRT administration."""

import csv
import datetime
import json
import logging
from io import StringIO

import numpy as np
import pandas as pd
from catsim import ItemBank
from catsim.estimation import NumericalSearchEstimator
from catsim.initialization import FixedPointInitializer
from catsim.irt import inf_hpc, max_info_hpc
from catsim.selection import MaxInfoSelector
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.template import RequestContext, Template
from django.urls import reverse
from scipy.stats import norm

from .forms import VocabularyChecklistForm
from .models import (
    AnswerRadio,
    AnswerText,
    CdiResult,
    Experiment,
    Instrument,
    ListItem,
    Question,
    SubjectData,
)
from .views import proceedToExperiment

# Create a logger for this file
logger = logging.getLogger(__name__)


def sort_items(item_params):
    """Return ndarray of indices of items sorted by maximum item information."""
    return (-inf_hpc(max_info_hpc(item_params), item_params)).argsort()


def estimateCDI(run_uuid):
    """Compute CDI estimates based on Mayor and Mani (2019)."""
    subject_data = get_object_or_404(SubjectData, pk=run_uuid)
    experiment = get_object_or_404(Experiment, pk=subject_data.experiment.pk)
    instrument = get_object_or_404(Instrument, pk=experiment.instrument.pk)

    estimate = 0
    # get the latest response for duplicate (i.e., modified) responses
    cdi_results = (
        CdiResult.objects.filter(subject=run_uuid)
        .order_by("given_label", "-id")
        .distinct("given_label")
    )

    try:
        # parse instrument word list
        all_words_reader = csv.DictReader(
            open(
                instrument.words_list.file.path,
                encoding="utf-8-sig",
            ),
            delimiter=",",
        )

        all_words = {}
        for row in all_words_reader:
            all_words[row["word"]] = int(row["word_id"])

        # get child's age and sex
        # age = (AnswerInteger.objects.filter(subject_data=subject_data, question__question_type='age').first()).body
        dob = datetime.date.fromisoformat(
            (
                AnswerText.objects.filter(
                    subject_data=subject_data, question__question_type="age"
                ).first()
            ).body
        )
        age = round(((subject_data.created.date() - dob).days) / (365 / 12))
        sex = (
            AnswerRadio.objects.filter(
                subject_data=subject_data, question__question_type="sex"
            ).first()
        ).body
        choices = (
            Question.objects.filter(experiment=experiment, question_type="sex").first()
        ).choices
        choices = list(filter(None, [x.strip() for x in choices.split(",")]))

        # get lookup files for child's sex
        if sex.strip().lower() == choices[0].lower():  # choices0 = female
            lm_np_mean = pd.read_csv(instrument.f_lm_np_mean.file.path)
            lm_np_sd = pd.read_csv(instrument.f_lm_np_sd.file.path)
            lm_p_mean = pd.read_csv(instrument.f_lm_p_mean.file.path)
            lm_p_sd = pd.read_csv(instrument.f_lm_p_sd.file.path)
            bmin = pd.read_csv(instrument.f_bmin.file.path)
            slope = pd.read_csv(instrument.f_slope.file.path)
        else:  # choices1 = male
            lm_np_mean = pd.read_csv(instrument.m_lm_np_mean.file.path)
            lm_np_sd = pd.read_csv(instrument.m_lm_np_sd.file.path)
            lm_p_mean = pd.read_csv(instrument.m_lm_p_mean.file.path)
            lm_p_sd = pd.read_csv(instrument.m_lm_p_sd.file.path)
            bmin = pd.read_csv(instrument.m_bmin.file.path)
            slope = pd.read_csv(instrument.m_slope.file.path)

        instr_num_words = len(lm_np_mean.index)
        basis = np.ones(instr_num_words + 1)
        min_score = np.ones(instr_num_words + 1)
        max_score = np.ones(instr_num_words + 1)
        x_values = np.arange(instr_num_words + 1)

        for cr in cdi_results:
            # retrieve row number via word_id, assuming row numbers are the same across all data files
            word_idx = lm_np_mean[
                lm_np_mean["word_id"] == all_words.get(cr.given_label)
            ].index[0]
            if cr.response:  # if can produce/comprehend word
                basis = basis + np.log(
                    norm.pdf(
                        x_values,
                        loc=lm_p_mean.at[word_idx, str(age)],
                        scale=lm_p_sd.at[word_idx, str(age)],
                    )
                )
            else:  # cannot produce/comprehend word
                basis = basis + np.log(
                    norm.pdf(
                        x_values,
                        loc=lm_np_mean.at[word_idx, str(age)],
                        scale=lm_np_sd.at[word_idx, str(age)],
                    )
                )
            min_score = min_score + np.log(
                norm.pdf(
                    x_values,
                    loc=lm_np_mean.at[word_idx, str(age)],
                    scale=lm_np_sd.at[word_idx, str(age)],
                )
            )
            max_score = max_score + np.log(
                norm.pdf(
                    x_values,
                    loc=lm_p_mean.at[word_idx, str(age)],
                    scale=lm_p_sd.at[word_idx, str(age)],
                )
            )

        # get index of max value in basis
        B = np.where(basis == np.amax(basis))
        B = int(B[0][0]) + 1
        estimate = (B - bmin.at[0, str(age)]) / slope.at[0, str(age)]

        # store CDI estimate in subject_data
        subject_data.cdi_estimate = estimate
        subject_data.save()

    except KeyError as e:
        logger.exception("Failed to estimate CDI score: " + str(e))
        return HttpResponseRedirect(
            reverse("experiments:experimentError", args=(run_uuid,))
        )
    else:
        logger.info("CDI estimate: " + str(estimate))
        return estimate


def cdiRun(request, run_uuid):
    """Administer a CDI-IRT adaptive vocabulary checklist."""
    subject_data = get_object_or_404(SubjectData, pk=run_uuid)
    experiment = get_object_or_404(Experiment, pk=subject_data.experiment.pk)
    instrument = get_object_or_404(Instrument, pk=experiment.instrument.pk)

    try:
        # parse instrument word list
        all_words_reader = csv.DictReader(
            open(
                instrument.words_list.file.path,
                encoding="utf-8-sig",
            ),
            delimiter=",",
        )
        all_words = []
        for row in all_words_reader:
            all_words.append(row["word"])
        request.session["all_words"] = json.dumps(all_words)

        # get IRT parameters
        item_params = pd.read_csv(instrument.irt_params.file.path)
        item_params = item_params.iloc[:, 1:5]
        request.session["item_params"] = item_params.reset_index().to_json(
            orient="records"
        )

        # administer first item
        administered_items = sort_items(item_params.to_numpy())[0:1,].tolist()
        request.session["administered_items"] = administered_items
        irt_run = 0
        request.session["irt_run"] = irt_run
        request.session["est_theta"] = FixedPointInitializer(
            -5
        ).initialize()  # start low, assume all poor learners
        words = []
        words.append(all_words[administered_items[irt_run]])
        request.session["words"] = words
        request.session["responses"] = []

        form = VocabularyChecklistForm(word=words[irt_run])
    except KeyError as e:
        logger.exception("Failed to generate CDI item: " + str(e))
        return HttpResponseRedirect(
            reverse("experiments:experimentError", args=(run_uuid,))
        )
    else:
        t = Template(experiment.cdi_page_tpl)
        c = RequestContext(
            request,
            {
                "subject_data": subject_data,
                "cdi_form": form,
                "experiment": experiment,
            },
        )
        return HttpResponse(t.render(c))


def cdiSubmit(request, run_uuid):
    """Store the submitted item response as a CdiResult."""
    subject_data = get_object_or_404(SubjectData, pk=run_uuid)
    experiment = get_object_or_404(Experiment, pk=subject_data.experiment.pk)
    irt_run = request.session.get("irt_run")
    words = request.session.get("words")
    current_word = words[irt_run]
    form = VocabularyChecklistForm(request.POST, word=current_word)

    # store current response as CdiResult and add to request.responses
    if form.is_valid():
        responses = request.session.get("responses")
        logger.debug(f"form.cleaned_data: {form.cleaned_data}")
        for key, value in form.cleaned_data.items():
            if key.startswith("word_"):
                cdiresult = CdiResult()
                cdiresult.subject = subject_data
                cdiresult.given_label = key[5:]
                cdiresult.response = value
                responses.append(int(value))
                cdiresult.save()
        request.session["responses"] = responses
        request.session.modified = True
        irt_run = request.session.get("irt_run")
        # count unique items
        count_unique = (
            CdiResult.objects.filter(subject=run_uuid)
            .order_by("given_label")
            .distinct("given_label")
            .count()
        )
        logger.info(f"unique count: {count_unique}")
        if count_unique < experiment.num_words:
            request.session["irt_run"] = irt_run + 1
            # generate subsequent item
            return cdiGenerateNextItem(request, run_uuid)
        else:  # proceed to experiment or end page
            estimateCDI(run_uuid)
            if ListItem.objects.filter(experiment=experiment):
                return proceedToExperiment(experiment, run_uuid)
            else:
                return HttpResponseRedirect(
                    reverse("experiments:experimentEnd", args=(run_uuid,))
                )
    t = Template(experiment.cdi_page_tpl)
    c = RequestContext(
        request,
        {
            "subject_data": subject_data,
            "cdi_form": form,
            "experiment": experiment,
        },
    )
    return HttpResponse(t.render(c))


def cdiGenerateNextItem(request, run_uuid):
    """Generate and render the next adaptive CDI test item."""
    subject_data = get_object_or_404(SubjectData, pk=run_uuid)
    experiment = get_object_or_404(Experiment, pk=subject_data.experiment.pk)

    try:
        # estimate and update theta
        irt_run = request.session.get("irt_run")
        item_params = request.session.get("item_params")
        item_params = (
            pd.read_json(StringIO(item_params), orient="records")
            .iloc[:, 1:5]
            .to_numpy()
        )
        administered_items = request.session.get("administered_items")
        responses = request.session.get("responses")
        est_theta = request.session.get("est_theta")
        est_theta = NumericalSearchEstimator(method="bounded").estimate(
            item_bank=ItemBank(item_params),
            administered_items=administered_items,
            response_vector=np.array(responses, dtype=bool),
            est_theta=est_theta,
        )
        request.session["est_theta"] = est_theta
        words = request.session.get("words")
        all_words = json.loads(request.session.get("all_words"))
        logger.info(f"est theta: {est_theta}")

        if np.isinf(est_theta):
            # generate IRT subsequent 'initial' items
            administered_items = sort_items(item_params)[0 : 1 + irt_run,].tolist()
            request.session["administered_items"] = administered_items
        else:
            # generate new items
            item_index = MaxInfoSelector().select(
                item_bank=ItemBank(item_params),
                administered_items=administered_items,
                est_theta=est_theta,
            )
            administered_items.append(item_index.tolist())
            request.session["administered_items"] = administered_items
        words.append(all_words[administered_items[irt_run]])
        request.session["words"] = words
        form = VocabularyChecklistForm(word=words[irt_run])
    except KeyError as e:
        logger.exception("Failed to generate cdi item: " + str(e))
        return HttpResponseRedirect(
            reverse("experiments:experimentError", args=(run_uuid,))
        )
    else:
        t = Template(experiment.cdi_page_tpl)
        c = RequestContext(
            request,
            {
                "subject_data": subject_data,
                "cdi_form": form,
                "experiment": experiment,
            },
        )
        return HttpResponse(t.render(c))
