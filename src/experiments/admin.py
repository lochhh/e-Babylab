"""Admin configuration for the experiments application."""

from django.conf import settings
from django.contrib import admin
from django.core.exceptions import NON_FIELD_ERRORS, ValidationError
from django.db import models
from django.db.models import Q
from django.forms import BaseInlineFormSet, ModelForm, Script, Textarea
from django.urls import reverse
from django.utils.html import format_html

from .flowchart import list_flowchart
from .forms import ExperimentForm, QuestionInlineFormSet
from .models import (
    AnswerInteger,
    AnswerRadio,
    AnswerSelect,
    AnswerSelectMultiple,
    AnswerText,
    BlockItem,
    CdiResult,
    ConsentQuestion,
    Experiment,
    Instrument,
    ListItem,
    OuterBlockItem,
    Question,
    SubjectData,
    TrialItem,
    TrialResult,
)

# Custom Help Text
TEMPLATES_HELP_TEXT = " ".join(
    [
        "<p><strong>Note:</strong>",
        "<p>- Do not remove elements enclosed in curly braces, "
        "i.e., {{ ... }}, {% ... %}. <br />",
        "- Do not remove script elements, "
        "i.e., &lt;script&gt; ... &lt;/script&gt;. <br />",
        '- To edit the source code directly, click on the "<>"'
        " icon on the toolbar. <br />",
        "- Some elements (e.g., error messages, success messages) are not"
        " visible in the editor. ",
        "To change the text of these elements, use the source code view. <br />",
        "- To change button text, use the source code view. <br />",
    ]
)

CDI_HELP_TEXT = " ".join(
    [
        "<p><strong>Note:</strong>",
        "<p>- To administer CDIs, make sure to obtain information on"
        " the child's age and sex in the participant form"
        ' (configured in the "Demographic information" section). <br />',
        '- Use the "age" type to define the allowed age range (in months).'
        " This will appear on the participant form as a Date field with an"
        " automatic check that ensures the participant falls within the"
        " age range of the instrument. <br />",
        '- Use the "sex" type for the sex field. The first option must'
        ' represent "female" and the second option must represent "male". <br />',
    ]
)

GRID_LAYOUT_HELP_TEXT = " ".join(
    [
        "<p><em>Rows</em> and <em>Columns</em> are for defining a grid layout"
        " (nrow * ncol), for establishing areas of interest (applicable to"
        " click responses and/or eye-tracking). <br />",
        "For instance, setting rows = 1 and cols = 2 would allow one to"
        " determine whether a click and/or gaze was on the left (1,1) or"
        " right side (1,2) of the visual stimulus. <br />",
        "A 2*2 grid would allow for identifying top-left (1,1), top-right (1,2),"
        " bottom-left (2,1), and bottom-right (2,2) clicks and/or gazes. <br />",
    ]
)

CALIBRATION_HELP_TEXT = " ".join(
    [
        "Calibration points for eye-tracking are defined in percentages. <br />",
        "For instance, specifying [10,50] places the visual stimulus at 10%"
        " of the width of the screen from the left edge and 50% of the"
        " height of the screen from the top edge. <br />",
    ]
)

INSTRUMENT_HELP_TEXT = format_html(
    "<p>To generate the required .csv files, download and run this"
    ' <a href="{url_rscript}">R script</a>.',
    url_rscript="/static/experiments/generateInstrumentFiles.r",
)


# ---------------------------------------------------------------------------
# Mixins
# ---------------------------------------------------------------------------


class HiddenFromIndexMixin:
    """Hides a ModelAdmin from the Django admin index page."""

    def get_model_perms(self, request):
        """Return empty perms dict thus hiding the model from admin index."""
        return {}


class ExperimentScopedQuerysetMixin:
    """Scopes get_queryset to experiments visible to the requesting user.

    Subclasses must set experiment_lookup_prefix to the double-underscore ORM
    path from their model to the Experiment fields, e.g. "experiment__" or
    "listitem__experiment__". Use "" when the model IS the Experiment.
    """

    experiment_lookup_prefix = ""

    def get_queryset(self, request):
        """Return a queryset scoped to experiments visible to the requesting user."""
        qs = super().get_queryset(request)
        p = self.experiment_lookup_prefix
        user_groups = request.user.groups.values_list("id", flat=True)
        if request.user.is_superuser:
            return qs
        user_owned = Q(**{f"{p}user": request.user})
        shared_grp = Q(**{f"{p}sharing_option": "GRP"})
        shared_user_grps = Q(**{f"{p}sharing_groups__in": user_groups})
        shared_pub = Q(**{f"{p}sharing_option": "PUB"})
        if request.user.groups.exists():
            # distinct: the sharing_groups M2M join yields one row per shared group
            return qs.filter(
                user_owned | shared_pub | shared_grp & shared_user_grps
            ).distinct()
        return qs.filter(user_owned | shared_pub)


class ExperimentScopedPermissionMixin:
    """Implements has_change_permission based on experiment sharing rules.

    Subclasses must set experiment_obj_path to the dot-separated attribute path
    from the admin object to its Experiment, e.g. "" (obj is the experiment),
    "experiment", or "subject.experiment".
    """

    experiment_obj_path = ""

    def _get_experiment(self, obj):
        exp = obj
        for attr in self.experiment_obj_path.split("."):
            if attr:
                exp = getattr(exp, attr)
        return exp

    def has_change_permission(self, request, obj=None):
        """Allow changes only when the user owns, shares, or is a superuser."""
        user_groups = request.user.groups.values_list("id")
        if not obj:
            return True
        exp = self._get_experiment(obj)
        if exp.sharing_option == "PUB" or (
            exp.sharing_option == "GRP"
            and user_groups.intersection(exp.sharing_groups.values_list("id"))
        ):
            return True
        return exp.user == request.user or request.user.is_superuser


# ---------------------------------------------------------------------------
# Inlines
# ---------------------------------------------------------------------------


class TrialItemInlineFormSet(BaseInlineFormSet):
    """Cross-row checks that per-form validation can't see within a single save."""

    def clean(self):
        """Reject pointing at an attention getter being unflagged or deleted now."""
        super().clean()
        live = [f for f in self.forms if getattr(f, "cleaned_data", None)]
        removed = {
            f.instance.pk
            for f in live
            if f.instance.pk
            and (
                f.cleaned_data.get("DELETE")
                or f.cleaned_data.get("trial_type") != TrialItem.ATTENTION_GETTER
            )
        }
        for form in live:
            ag = form.cleaned_data.get("attention_getter")
            if (
                ag is not None
                and not form.cleaned_data.get("DELETE")
                and ag.pk in removed
            ):
                form.add_error(
                    "attention_getter",
                    f"'{ag.label}' is being changed from an attention getter or"
                    " deleted in this save.",
                )


class TrialItemForm(ModelForm):
    """Trial form without label colons (Django 6 renders file/FK labels as legends)."""

    def __init__(self, *args, **kwargs):
        """Default the label suffix to empty."""
        kwargs.setdefault("label_suffix", "")
        super().__init__(*args, **kwargs)

    HIDDEN_FIELD_PREFIXES = {
        "trial_type": "Trial type",
        "record_gaze": "Enable eye-tracking",
    }

    def clean(self):
        """Clear dwell-check values when the trial is not a regular trial."""
        cleaned = super().clean()
        if cleaned.get("trial_type", TrialItem.REGULAR) != TrialItem.REGULAR:
            cleared = {
                "attention_getter": None,
                "min_dwell_time": None,
                "dwell_target_type": TrialItem.ANY,
                "dwell_target_row": None,
                "dwell_target_col": None,
            }
            cleaned.update({k: v for k, v in cleared.items() if k in self.fields})
        return cleaned

    def _update_errors(self, errors):
        """Show errors on fields hidden from this form as non-field errors."""
        error_dict = getattr(errors, "error_dict", {})
        hidden = error_dict.keys() - self.fields.keys() - {NON_FIELD_ERRORS}
        moved = []
        for name in hidden:
            prefix = self.HIDDEN_FIELD_PREFIXES.get(name, "Gaze dwell time check")
            moved += [
                ValidationError(
                    "%(prefix)s: %(msg)s To edit these settings, set the"
                    " experiment's Recording option (General Settings) to include"
                    " eye-tracking.",
                    params={"prefix": prefix, "msg": " ".join(err.messages)},
                )
                for err in error_dict.pop(name)
            ]
        if moved:
            error_dict.setdefault(NON_FIELD_ERRORS, []).extend(moved)
        super()._update_errors(errors)


class TrialItemInline(admin.StackedInline):
    """Inline admin for editing trial items within a block item."""

    model = TrialItem
    extra = 0
    verbose_name = "Trial"
    verbose_name_plural = "Trials"
    inline_classes = ["grp-collapse grp-open"]
    sortable_field_name = "position"
    form = TrialItemForm
    formset = TrialItemInlineFormSet
    fieldsets = (
        (None, {"fields": ("label", "code", "position", "trial_type")}),
        (
            "Stimulus",
            {
                "fields": (
                    "visual_onset",
                    "visual_file",
                    "audio_onset",
                    "audio_file",
                    "max_duration",
                )
            },
        ),
        ("Response", {"fields": ("user_input", "response_keys")}),
        ("Recording", {"fields": ("record_media", "record_gaze")}),
        (
            "Grid",
            {
                "fields": (("grid_row", "grid_col"),),
                "description": f'<div class="help">{GRID_LAYOUT_HELP_TEXT}</div>',
            },
        ),
        (
            "Eye-tracking calibration",
            {
                "classes": ("eye-calibration",),
                "fields": ("calibration_points",),
                "description": f'<div class="help">{CALIBRATION_HELP_TEXT}</div>',
            },
        ),
        (
            "Gaze dwell time check",
            {
                "classes": ("dwell-check",),
                "fields": (
                    "attention_getter",
                    "min_dwell_time",
                    "dwell_target_type",
                    ("dwell_target_row", "dwell_target_col"),
                ),
                "description": (
                    '<div class="help">Launch an attention getter trial immediately'
                    " after this trial if the participant's dwell time on the dwell"
                    " target falls below the minimum dwell time. Requires"
                    " <em>Enable eye-tracking</em> (Recording).</div>"
                ),
            },
        ),
    )

    def get_fieldsets(self, request, obj=None):
        """Drop eye-tracking fields unless the parent block's experiment records gaze.

        Args:
            request: The current request.
            obj: The parent ``BlockItem``, or None on the add page (show all).

        Returns:
            The fieldsets to render. Omitted fields keep their saved values.

        """
        fieldsets = super().get_fieldsets(request, obj)
        if obj is None:
            return fieldsets
        experiment = obj.outerblockitem.listitem.experiment
        if experiment.recording_option in (Experiment.EYE, Experiment.ALL):
            return fieldsets
        eye_only = {"trial_type", "record_gaze"}
        kept = []
        for name, opts in fieldsets:
            if set(opts.get("classes", ())) & {"eye-calibration", "dwell-check"}:
                continue
            fields = [f for f in opts["fields"] if f not in eye_only]
            kept.append((name, {**opts, "fields": fields}))
        return kept

    class Media:
        """Show the eye-tracking sections that apply to the trial type."""

        js = (Script("experiments/js/admin/trial-type-toggle.js", type="module"),)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        """Offer only attention getters from the same list as the edited block."""
        if db_field.name == "attention_getter":
            match = getattr(request, "resolver_match", None)
            object_id = match.kwargs.get("object_id") if match else None
            listitem_id = (
                BlockItem.objects.filter(pk=object_id)
                .values_list("outerblockitem__listitem", flat=True)
                .first()
                if object_id
                else None
            )
            kwargs["queryset"] = TrialItem.objects.filter(
                trial_type=TrialItem.ATTENTION_GETTER,
                blockitem__outerblockitem__listitem=listitem_id,
            ).select_related("blockitem__outerblockitem")
        field = super().formfield_for_foreignkey(db_field, request, **kwargs)
        if db_field.name == "attention_getter":
            field.help_text = (
                f"{field.help_text} Lists every trial marked as an attention"
                " getter in this list, from any block."
            ).strip()
            field.label_from_instance = lambda t: (
                f"{t.label} — {t.blockitem.outerblockitem.outer_block_name}"
                f" › {t.blockitem.label}"  # noqa: RUF001
            )
        return field


class BlockItemInline(admin.StackedInline):
    """Inline admin for editing inner block items within an outer block item."""

    model = BlockItem
    extra = 0
    show_change_link = True
    verbose_name = "Inner block"
    verbose_name_plural = "Inner blocks"
    inline_classes = ["grp-collapse grp-open"]
    sortable_field_name = "position"


class OuterBlockItemInline(admin.StackedInline):
    """Inline admin for editing outer block items within a list item."""

    model = OuterBlockItem
    extra = 0
    show_change_link = True
    verbose_name = "Outer block"
    verbose_name_plural = "Outer blocks"
    inline_classes = ["grp-collapse grp-open"]
    sortable_field_name = "position"


class ListItemInline(admin.StackedInline):
    """Inline admin for editing list items within an experiment."""

    model = ListItem
    extra = 0
    show_change_link = True
    verbose_name = "List"
    verbose_name_plural = "Lists"
    inline_classes = ["grp-collapse grp-open"]


class QuestionInline(admin.StackedInline):
    """Inline admin for demographic information questions within an experiment."""

    model = Question
    extra = 2
    verbose_name = "Field"
    verbose_name_plural = "Demographic information"
    classes = ["grp-collapse grp-closed"]
    inline_classes = ["grp-collapse grp-open"]
    sortable_field_name = "position"
    formfield_overrides = {
        models.TextField: {"widget": Textarea(attrs={"rows": 3, "cols": 85})},
    }
    formset = QuestionInlineFormSet

    def get_formset(self, request, obj=None, **kwargs):
        """Return the formset.

        Suppress extra empty forms when questions already exist.
        """
        if obj is None:
            return super().get_formset(request, obj, **kwargs)
        kwargs["extra"] = 2
        if Question.objects.filter(experiment=obj).count():
            kwargs["extra"] = 0
        return super().get_formset(request, obj, **kwargs)


class AnswerBaseInline(admin.StackedInline):
    """Base read-only inline for displaying participant answers on a subject data."""

    fields = ("question", "body")
    readonly_fields = ("question", "body")
    extra = 0
    inline_classes = ["grp-collapse grp-open"]

    def has_add_permission(self, request, obj=None):
        """Disable adding Answers.

        Answers should only be created during an experiment.
        """
        return False

    def has_delete_permission(self, request, obj=None):
        """Disallow deleting of an Answer."""
        return False


def _answer_inline(answer_model):
    """Return a read-only StackedInline subclass for the given answer model."""
    return type(
        f"{answer_model.__name__}Inline", (AnswerBaseInline,), {"model": answer_model}
    )


AnswerTextInline = _answer_inline(AnswerText)
AnswerRadioInline = _answer_inline(AnswerRadio)
AnswerSelectInline = _answer_inline(AnswerSelect)
AnswerSelectMultipleInline = _answer_inline(AnswerSelectMultiple)
AnswerIntegerInline = _answer_inline(AnswerInteger)


class CdiResultInline(admin.TabularInline):
    """Inline for displaying CDI responses on a subject data record."""

    model = CdiResult
    extra = 0
    readonly_fields = ("given_label", "response")
    ordering = ("id",)

    def has_add_permission(self, request, obj=None):
        """Disable adding CDI results; they are created during experiment runs."""
        return False


class TrialResultInline(admin.TabularInline):
    """Inline for displaying per-trial results on a subject data record."""

    model = TrialResult
    extra = 0
    exclude = ("webcam_file", "start_time", "end_time")
    readonly_fields = (
        "trial_number",
        "trialitem",
        "trial_blockitem",
        "trial_audio",
        "trial_visual",
        "trial_input",
        "trial_maxduration",
        "response_time",
        "key_pressed",
        "webcam_file_link",
        "resolution_w",
        "resolution_h",
        "webgazer_data",
    )
    ordering = ("id",)

    @admin.display(description="Block item")
    def trial_blockitem(self, obj):
        """Return the block item associated with the trial result."""
        return obj.trialitem.blockitem

    @admin.display(description="Audio file")
    def trial_audio(self, obj):
        """Return the audio filename for the trial item, or empty string if none."""
        f = obj.trialitem.audio_file
        return f.original_filename if f else ""

    @admin.display(description="Visual file")
    def trial_visual(self, obj):
        """Return the visual filename for the trial item, or empty string if none."""
        f = obj.trialitem.visual_file
        return f.original_filename if f else ""

    @admin.display(description="User input")
    def trial_input(self, obj):
        """Return the user input setting for the trial item."""
        return obj.trialitem.user_input

    @admin.display(description="Max duration")
    def trial_maxduration(self, obj):
        """Return the maximum duration setting for the trial item."""
        return obj.trialitem.max_duration

    @admin.display(description="Response time")
    def response_time(self, obj):
        """Return the elapsed response time as a string."""
        if obj.start_time and obj.end_time:
            return str(obj.end_time - obj.start_time)
        return ""

    @admin.display(description="Webcam file")
    def webcam_file_link(self, obj):
        """Return the webcam filename, or a dash if none was recorded."""
        if obj.webcam_file:
            return obj.webcam_file.name
        else:
            return "-"

    def has_add_permission(self, request, obj=None):
        """Disable adding trial results; they are created during experiment runs."""
        return False


class ConsentQuestionInline(admin.StackedInline):
    """Inline admin for editing consent questions within an experiment."""

    model = ConsentQuestion
    extra = 0
    classes = ["grp-collapse grp-closed"]
    inline_classes = ["grp-collapse grp-open"]
    sortable_field_name = "position"
    formfield_overrides = {
        models.TextField: {"widget": Textarea(attrs={"rows": 3, "cols": 85})},
    }
    fields = (
        "text",
        "position",
        ("response_yes", "response_no"),
    )


# ---------------------------------------------------------------------------
# ModelAdmin classes
# ---------------------------------------------------------------------------


class InstrumentAdmin(admin.ModelAdmin):
    """Admin for CDI instrument definitions."""

    def render_change_form(self, request, context, *args, **kwargs):
        """Inject instrument help text into the change form context."""
        self.change_form_template = "admin/experiments/change_form_help_text.html"
        extra = {
            "help_text": INSTRUMENT_HELP_TEXT,
        }
        context.update(extra)
        return super().render_change_form(request, context, *args, **kwargs)


class ExperimentAdmin(
    ExperimentScopedQuerysetMixin,
    ExperimentScopedPermissionMixin,
    admin.ModelAdmin,
):
    """Admin for experiments, scoped to experiments the requesting user can access."""

    experiment_lookup_prefix = ""
    experiment_obj_path = ""

    form = ExperimentForm
    fieldsets = [
        (
            None,
            {
                "fields": (
                    "exp_name",
                    "sharing_option",
                    "sharing_groups",
                    "list_selection_strategy",
                    "general_onset",
                    "recording_option",
                    "loading_image",
                    "include_pause_page",
                    "show_gaze_estimations",
                )
            },
        ),
        (
            "Templates",
            {
                "classes": ("grp-collapse grp-closed",),
                "fields": (
                    "information_page_tpl",
                    "browser_check_page_tpl",
                    "introduction_page_tpl",
                    "consent_fail_page_tpl",
                    "demographic_data_page_tpl",
                    "cdi_page_tpl",
                    "webcam_check_page_tpl",
                    "microphone_check_page_tpl",
                    "experiment_page_tpl",
                    "pause_page_tpl",
                    "thank_you_page_tpl",
                    "thank_you_abort_page_tpl",
                    "error_page_tpl",
                ),
                "description": f'<div class="help">{TEMPLATES_HELP_TEXT}</div>',
            },
        ),
        (
            "CDI administration",
            {
                "classes": ("grp-collapse grp-closed",),
                "fields": (
                    "instrument",
                    "assess_type",
                    "num_words",
                    "typical_dev",
                ),
                "description": f'<div class="help">{CDI_HELP_TEXT}</div>',
            },
        ),
    ]
    inlines = [ConsentQuestionInline, QuestionInline, ListItemInline]
    list_display = ("exp_name", "created_on", "user", "experiment_buttons")
    list_filter = ["created_on"]
    search_fields = ["exp_name"]
    change_list_filter_template = "admin/filter_listing.html"

    def save_model(self, request, obj, form, change):
        """Assign the current user as owner when creating a new experiment."""
        if getattr(obj, "user", None) is None:
            obj.user = request.user
        obj.save()

    @admin.display(description="Actions")
    def experiment_buttons(self, obj):
        """Display action buttons for the Experiment admin interface."""
        return format_html(
            '<a class="grp-button" href="{url_exp}">Go to Experiment</a>&nbsp;'
            + '<a class="grp-button" href="{url_report}">Download Results</a>&nbsp;'
            + '<a class="grp-button" href="{url_export}">Export Experiment</a>',
            url_exp=reverse("experiments:informationPage", args=[obj.id]),
            url_report=reverse("experiments:experimentReport", args=[obj.id]),
            url_export=reverse("experiments:experimentExport", args=[obj.id]),
        )


class ListItemAdmin(
    HiddenFromIndexMixin,
    ExperimentScopedQuerysetMixin,
    admin.ModelAdmin,
):
    """Admin for list items.

    These are hidden from the index and scoped to accessible experiments.
    """

    experiment_lookup_prefix = "experiment__"

    inlines = [OuterBlockItemInline]
    classes = ["grp-collapse grp-open"]
    list_display = (
        "list_name",
        "experiment",
    )

    def change_view(self, request, object_id, form_url="", extra_context=None):
        """Add the list's Mermaid flowchart to the change page."""
        extra_context = extra_context or {}
        obj = self.get_object(request, object_id)
        if obj is not None:
            extra_context["flowchart"] = list_flowchart(obj)
        return super().change_view(request, object_id, form_url, extra_context)


class OuterBlockItemAdmin(
    HiddenFromIndexMixin,
    ExperimentScopedQuerysetMixin,
    admin.ModelAdmin,
):
    """Admin for outer block items.

    These are hidden from the index and scoped to accessible experiments.
    """

    experiment_lookup_prefix = "listitem__experiment__"

    inlines = [BlockItemInline]
    classes = ["grp-collapse grp-open"]
    list_display = ("outer_block_name", "listitem", "get_experiment")

    @admin.display(description="Experiment", ordering="listitem")
    def get_experiment(self, obj):
        """Return the experiment this outer block item belongs to."""
        return obj.listitem.experiment


class BlockItemAdmin(
    HiddenFromIndexMixin,
    ExperimentScopedQuerysetMixin,
    admin.ModelAdmin,
):
    """Admin for inner block items.

    These are hidden from the index and scoped to accessible experiments.
    """

    experiment_lookup_prefix = "outerblockitem__listitem__experiment__"

    inlines = [TrialItemInline]
    list_display = ("label", "outerblockitem", "get_listitem", "get_experiment")

    @admin.display(description="List item", ordering="outerblockitem")
    def get_listitem(self, obj):
        """Return the list item associated with the block item."""
        return obj.outerblockitem.listitem

    @admin.display(description="Experiment", ordering="outerblockitem__listitem")
    def get_experiment(self, obj):
        """Return the experiment associated with the block item."""
        return obj.outerblockitem.listitem.experiment


class SubjectDataAdmin(
    ExperimentScopedQuerysetMixin,
    ExperimentScopedPermissionMixin,
    admin.ModelAdmin,
):
    """Admin for participant records, with all response and trial result inlines."""

    experiment_lookup_prefix = "experiment__"
    experiment_obj_path = "experiment"

    list_display = ("participant_id", "experiment", "listitem", "created")
    list_filter = ["experiment"]
    inlines = [
        AnswerTextInline,
        AnswerRadioInline,
        AnswerSelectInline,
        AnswerSelectMultipleInline,
        AnswerIntegerInline,
        CdiResultInline,
        TrialResultInline,
    ]
    # specifies the order as well as which fields to act on
    readonly_fields = (
        "id",
        "participant_id",
        "experiment",
        "listitem",
        "created",
        "updated",
        "resolution_w",
        "resolution_h",
        "cdi_estimate",
    )
    ordering = (
        "experiment",
        "participant_id",
    )

    def has_add_permission(self, request, obj=None):
        """Disable adding SubjectData.

        These should only be created during an experiment.
        """
        return False


class TrialResultAdmin(
    HiddenFromIndexMixin,
    ExperimentScopedQuerysetMixin,
    ExperimentScopedPermissionMixin,
    admin.ModelAdmin,
):
    """Admin view for TrialResult (currently unused; kept for reference)."""

    experiment_lookup_prefix = "subject__experiment__"
    experiment_obj_path = "subject.experiment"

    list_display = (
        "subject",
        "date",
        "trialitem",
    )
    readonly_fields = (
        "subject",
        "trialitem",
        "date",
        "start_time",
        "end_time",
        "key_pressed",
        "webcam_file_link",
    )

    @admin.display(description="Webcam file")
    def webcam_file_link(self, obj):
        """Return a URL to the webcam recording, or a dash if none exists."""
        if obj.webcam_file:
            webcam_url = settings.WEBCAM_URL
            return webcam_url + obj.filename
        else:
            return "-"

    def get_form(self, request, obj=None, **kwargs):
        """Exclude the raw webcam_file field; the link column is shown instead."""
        self.exclude = ("webcam_file",)
        form = super().get_form(request, obj, **kwargs)
        return form

    def has_add_permission(self, request, obj=None):
        """Disable adding trial results; they are created during experiment runs."""
        return False


# Register your models here.
admin.site.register(Instrument, InstrumentAdmin)
admin.site.register(Experiment, ExperimentAdmin)
admin.site.register(ListItem, ListItemAdmin)
admin.site.register(OuterBlockItem, OuterBlockItemAdmin)
admin.site.register(BlockItem, BlockItemAdmin)
admin.site.register(SubjectData, SubjectDataAdmin)
