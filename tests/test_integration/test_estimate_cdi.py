"""Integration tests for estimate_cdi using real Norwegian WS production data.

Expected scores are derived from participant xlsx files in tests/data/:
  5_* — all False  → -3.448113
  6_* — all True   → 799.962264
  7_* — partial    → 206.886792

All participants: female, DOB 2024-06-12, participation date 2026-06-12 (24 mo).
"""

import datetime

import pytest

from experiments.cdi import estimate_cdi
from experiments.models import (
    AnswerRadio,
    AnswerText,
    CdiResult,
    Experiment,
    Question,
    SubjectData,
)

# ── Shared helpers ────────────────────────────────────────────────────────────

DOB = "2024-06-12"
PARTICIPATION_DATE = datetime.datetime(2026, 6, 12, 12, 0, 0, tzinfo=datetime.UTC)
SEX_CHOICES = "female, male"
SEX_VALUE = "female"


def _make_cdi_setup(db, user, real_instrument, responses):
    """Create the full DB state needed by estimate_cdi and return the SubjectData."""
    experiment = Experiment.objects.create(
        user=user,
        exp_name="test-cdi",
        instrument=real_instrument,
    )
    listitem = experiment.listitem_set.create(list_name="L1")
    subject_data = SubjectData.objects.create(
        experiment=experiment,
        listitem=listitem,
        participant_id=1,
    )
    # Fix created timestamp so age calculation is stable
    SubjectData.objects.filter(pk=subject_data.pk).update(created=PARTICIPATION_DATE)
    subject_data.refresh_from_db()

    age_question = Question.objects.create(
        experiment=experiment,
        text="Date of birth",
        question_type=Question.AGE,
        required=True,
        position=1,
    )
    sex_question = Question.objects.create(
        experiment=experiment,
        text="Sex",
        question_type=Question.SEX,
        choices=SEX_CHOICES,
        required=True,
        position=2,
    )
    AnswerText.objects.create(
        question=age_question,
        subject_data=subject_data,
        body=DOB,
    )
    AnswerRadio.objects.create(
        question=sex_question,
        subject_data=subject_data,
        body=SEX_VALUE,
    )
    for word, response in responses:
        CdiResult.objects.create(
            subject=subject_data,
            given_label=word,
            response=response,
        )

    return subject_data


# ── Tests ─────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
def test_estimate_cdi_all_false(user, real_instrument):
    """Five-word all-False response yields the expected CDI estimate."""
    responses = [
        ("skap", False),
        ("nei", False),
        ("mamma/mor", False),
        ("hei", False),
        ("pappa/far", False),
    ]
    sd = _make_cdi_setup(None, user, real_instrument, responses)

    result = estimate_cdi(sd.pk)

    assert isinstance(result, (int, float))
    assert result == pytest.approx(-3.448113, abs=0.001)
    sd.refresh_from_db()
    assert sd.cdi_estimate == pytest.approx(-3.448113, abs=0.001)


@pytest.mark.django_db
def test_estimate_cdi_all_true(user, real_instrument):
    """Five-word all-True response yields the expected CDI estimate."""
    responses = [
        ("skap", True),
        ("mage", True),
        ("lang", True),
        ("hvis", True),
        ("hvert", True),
    ]
    sd = _make_cdi_setup(None, user, real_instrument, responses)

    result = estimate_cdi(sd.pk)

    assert isinstance(result, (int, float))
    assert result == pytest.approx(799.962264, abs=0.001)
    sd.refresh_from_db()
    assert sd.cdi_estimate == pytest.approx(799.962264, abs=0.001)


@pytest.mark.django_db
def test_estimate_cdi_partial(user, real_instrument):
    """Five-word mixed response (F/T/F/T/F) yields the expected CDI estimate."""
    responses = [
        ("skap", False),
        ("nei", True),
        ("seng", False),
        ("bok", True),
        ("mage", False),
    ]
    sd = _make_cdi_setup(None, user, real_instrument, responses)

    result = estimate_cdi(sd.pk)

    assert isinstance(result, (int, float))
    assert result == pytest.approx(206.886792, abs=0.001)
    sd.refresh_from_db()
    assert sd.cdi_estimate == pytest.approx(206.886792, abs=0.001)
