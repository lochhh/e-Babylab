"""Forms for participant data, consent, CDI, and experiment management."""

import datetime
import logging
import uuid

from django import forms
from django.contrib.admin.widgets import FilteredSelectMultiple
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.db.models import Max
from django.forms import models
from django.forms.widgets import DateInput

from .models import (
    ANSWER_TYPE_MODEL,
    Experiment,
    Question,
    SubjectData,
)

# Create a logger for this file
logger = logging.getLogger(__name__)


class ConsentForm(forms.Form):
    """Generates list of Y/N questions for the consent form."""

    def __init__(self, *args, **kwargs):
        """Build consent fields from the experiment's consent questions."""
        experiment = kwargs.pop("experiment")
        super().__init__(*args, **kwargs)

        for q in experiment.consent_questions():
            self.fields[f"question_{q.pk}"] = forms.ChoiceField(
                label=q.text,
                widget=forms.RadioSelect,
                choices=(
                    [
                        ("yes", q.response_yes),
                        ("no", q.response_no),
                    ]
                ),
            )
            self.fields[f"question_{q.pk}"].widget.attrs["class"] = (
                "required list-unstyled"
            )


class SubjectDataForm(models.ModelForm):
    """Generates the questions and answer fields for the participant data form."""

    class Meta:
        """Configure model and hidden resolution fields."""

        model = SubjectData
        fields = ("resolution_w", "resolution_h")
        widgets = {
            "resolution_w": forms.HiddenInput(),
            "resolution_h": forms.HiddenInput(),
        }

    def __init__(self, *args, **kwargs):
        """Build participant data fields from the experiment's subject questions."""
        experiment = kwargs.pop("experiment")
        self.experiment = experiment
        super().__init__(*args, **kwargs)
        self.uuid = uuid.uuid4().hex

        data = kwargs.get("data")
        self._question_fields: dict[str, Question] = {}
        for q in experiment.subject_questions():
            field_name = f"question_{q.pk}"
            self._question_fields[field_name] = q
            self.fields[field_name] = self._build_question_field(q)
            self.fields[field_name].required = q.required
            self.fields[field_name].widget.attrs["class"] = (
                "required list-unstyled" if q.required else "list-unstyled"
            )
            if data:
                self.fields[field_name].initial = data.get(field_name)

    def _build_question_field(self, q):
        """Return the appropriate form field for a question type."""
        match q.question_type:
            case Question.TEXT:
                return forms.CharField(
                    label=q.text, widget=forms.Textarea(attrs={"rows": 1})
                )
            case Question.RADIO | Question.SEX:
                return forms.ChoiceField(
                    label=q.text, widget=forms.RadioSelect, choices=q.get_choices()
                )
            case Question.SELECT:
                return forms.ChoiceField(
                    label=q.text,
                    widget=forms.Select,
                    choices=(("", "-------------"), *q.get_choices()),
                )
            case Question.SELECT_MULTIPLE:
                return forms.MultipleChoiceField(
                    label=q.text,
                    widget=forms.CheckboxSelectMultiple,
                    choices=q.get_choices(),
                )
            case Question.INTEGER:
                return forms.IntegerField(label=q.text, localize=True)
            case Question.NUM_RANGE:
                lo, hi = q.get_choices()
                field = forms.IntegerField(
                    label=q.text,
                    min_value=int(lo[0]),
                    max_value=int(hi[0]),
                    localize=True,
                )
                field.widget.attrs["step"] = "1"
                return field
            case Question.AGE:
                return forms.DateField(
                    label=q.text,
                    initial=datetime.date.today,
                    widget=DateInput(format="%Y-%m-%d", attrs={"type": "date"}),
                )

    def clean(self):
        """Validate responses and compute participant age from any date fields."""
        cleaned_data = super().clean()

        age_question = next(
            (
                q
                for q in self._question_fields.values()
                if q.question_type == Question.AGE
            ),
            None,
        )
        if not age_question:
            return cleaned_data

        field_name = f"question_{age_question.pk}"
        dob = cleaned_data.get(field_name)
        if not isinstance(dob, datetime.date):
            return cleaned_data

        age_mo = (datetime.date.today() - dob).days / (365 / 12)
        age_range = age_question.get_choices()
        min_age, max_age = int(age_range[0][0]), int(age_range[1][0])
        if age_mo < min_age:
            self.add_error(field_name, f"Min: {min_age} mo.")
        if age_mo > max_age:
            self.add_error(field_name, f"Max: {max_age} mo.")
        logger.info(f"Age in months: {round(age_mo)}")
        return cleaned_data

    def save(self, commit=True):
        """Save the SubjectData object."""
        subject_data = super().save(commit=False)
        subject_data.experiment = self.experiment
        subject_data.id = self.uuid
        max_id = SubjectData.objects.filter(
            experiment=self.experiment.pk
        ).aggregate(Max("participant_id"))["participant_id__max"]
        subject_data.participant_id = (max_id or 0) + 1
        subject_data.save()

        for field_name, q in self._question_fields.items():
            field_value = self.cleaned_data[field_name]
            a = ANSWER_TYPE_MODEL[q.question_type](question=q)
            a.body = field_value
            logger.info(
                f'Creating answer to "{q.text}" '
                f"(question {q.pk}) of type "
                f"{q.question_type}: {field_value}"
            )
            a.subject_data = subject_data
            a.save()
        return subject_data


class QuestionInlineFormSet(models.BaseInlineFormSet):
    """Formset for demographic questions that pre-populates default fields."""

    def __init__(self, *args, **kwargs):
        """Pre-populate age/sex fields when no questions exist yet."""
        experiment = kwargs.get("instance")
        if (
            experiment
            and not Question.objects.filter(experiment=experiment.pk).exists()
        ):
            kwargs.update(
                {
                    "initial": [
                        {
                            "text": "Date of birth",
                            "question_type": "age",
                            "required": True,
                        },
                        {
                            "text": "Sex",
                            "question_type": "sex",
                            "choices": "Female, Male",
                            "required": True,
                        },
                    ]
                }
            )
        super().__init__(*args, **kwargs)


class ExperimentForm(forms.ModelForm):
    """Provides the multi-select fields containing a list of all existing groups."""

    class Meta:
        """Configure model and include all fields."""

        model = Experiment
        fields = "__all__"

    sharing_groups = forms.ModelMultipleChoiceField(
        queryset=Group.objects.all(),
        required=False,
        widget=FilteredSelectMultiple("groups", is_stacked=False),
    )

    def clean_sharing_groups(self):
        """Validate sharing_groups is consistent with sharing_option."""
        sharing_option = self.cleaned_data.get("sharing_option")
        groups = self.cleaned_data.get("sharing_groups")

        if sharing_option == "GRP" and not groups:
            raise ValidationError("Please select at least one group.")
        if groups and sharing_option != "GRP":
            raise ValidationError(
                'Groups are selected but sharing is not set to "Group members only".'
                " Either choose that option or clear the groups."
            )
        return groups


class VocabularyChecklistForm(forms.Form):
    """Generates the vocabulary checklist form."""

    def __init__(self, *args, **kwargs):
        """Build a single checkbox field for the given CDI word."""
        word = kwargs.pop("word", None)
        super().__init__(*args, **kwargs)

        if word:
            field_name = f"word_{word}"
            self.fields[field_name] = forms.BooleanField(
                label=word,
                required=False,
                widget=forms.CheckboxInput(attrs={"class": "list-unstyled"}),
            )


class ImportForm(forms.Form):
    """Provides the form for ZIP file upload when an experiment is to be imported."""

    import_file = forms.FileField(label="ZIP File")
