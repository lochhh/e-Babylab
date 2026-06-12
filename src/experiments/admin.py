"""Admin configuration for the experiments application."""

import json

from django.conf import settings
from django.contrib import admin
from django.core import serializers
from django.db import models
from django.db.models import Q
from django.forms import Textarea
from django.urls import reverse
from django.utils import timezone
from django.utils.html import format_html

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

"""
Custom Help Text
"""
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
        "<p>Note:",
        "<p><em>Rows</em> and <em>Columns</em> are for defining a grid layout"
        " (nrow * ncol), for establishing areas of interest (applicable to"
        " click responses and/or eye-tracking). <br />",
        "For instance, setting rows = 1 and cols = 2 would allow one to"
        " determine whether a click and/or gaze was on the left (1,1) or"
        " right side (1,2) of the visual stimulus. <br />",
        "A 2*2 grid would allow for identifying top-left (1,1), top-right (1,2),"
        " bottom-left (2,1), and bottom-right (2,2) clicks and/or gazes. <br />",
        "<em>Calibration points</em> for eye-tracking are defined"
        " in percentages. <br />",
        "For instance, specifying [10,50] places the visual stimulus at 10%"
        " of the width of the screen from the left edge and 50% of the"
        " height of the screen from the top edge. <br />",
    ]
)

INSTRUMENT_HELP_TEXT = format_html(
    "<p>To generate the required .csv files, download and run this"
    ' <a href="{url_rscript}">R script</a>.',
    url_rscript="/media/uploads/instruments/generateInstrumentFiles.r",
)


class TrialItemInline(admin.StackedInline):
    """Inline admin for editing trial items within a block item."""

    model = TrialItem
    extra = 0
    verbose_name = "Trial"
    verbose_name_plural = "Trials"
    inline_classes = ["grp-collapse grp-open"]
    sortable_field_name = "position"
    fieldsets = (
        (
            None,
            {
                "fields": (
                    "label",
                    "code",
                    "visual_onset",
                    "visual_file",
                    "audio_onset",
                    "audio_file",
                    "user_input",
                    "response_keys",
                    "max_duration",
                    "record_media",
                    "record_gaze",
                    "is_calibration",
                    "calibration_points",
                    ("grid_row", "grid_col"),
                    "position",
                ),
                "description": f'<div class="help">{GRID_LAYOUT_HELP_TEXT}</div>',
            },
        ),
    )


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


class AnswerTextInline(AnswerBaseInline):
    """Inline for displaying free-text answers."""

    model = AnswerText


class AnswerRadioInline(AnswerBaseInline):
    """Inline for displaying radio-button answers."""

    model = AnswerRadio


class AnswerSelectInline(AnswerBaseInline):
    """Inline for displaying single-select dropdown answers."""

    model = AnswerSelect


class AnswerSelectMultipleInline(AnswerBaseInline):
    """Inline for displaying multi-select answers."""

    model = AnswerSelectMultiple


class AnswerIntegerInline(AnswerBaseInline):
    """Inline for displaying integer answers."""

    model = AnswerInteger


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

    def trial_blockitem(self, obj):
        """Return the block item associated with the trial result."""
        return obj.trialitem.blockitem

    trial_blockitem.short_description = "Block item"

    def trial_audio(self, obj):
        """Return the audio filename for the trial item, or empty string if none."""
        f = obj.trialitem.audio_file
        return f.original_filename if f else ""

    trial_audio.short_description = "Audio file"

    def trial_visual(self, obj):
        """Return the visual filename for the trial item, or empty string if none."""
        f = obj.trialitem.visual_file
        return f.original_filename if f else ""

    trial_visual.short_description = "Visual file"

    def trial_input(self, obj):
        """Return the user input setting for the trial item."""
        return obj.trialitem.user_input

    trial_input.short_description = "User input"

    def trial_maxduration(self, obj):
        """Return the maximum duration setting for the trial item."""
        return obj.trialitem.max_duration

    trial_maxduration.short_description = "Max duration"

    def response_time(self, obj):
        """Return the elapsed response time as a string."""
        if obj.start_time and obj.end_time:
            return str(obj.end_time - obj.start_time)
        return ""

    response_time.short_description = "Response time"

    def webcam_file_link(self, obj):
        """Return the webcam filename, or a dash if none was recorded."""
        if obj.webcam_file:
            return obj.webcam_file.name
        else:
            return "-"

    webcam_file_link.allow_tags = True
    webcam_file_link.short_description = "Webcam file"

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


class ExperimentAdmin(admin.ModelAdmin):
    """Admin for experiments, scoped to experiments the requesting user can access."""

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
    list_display = ("exp_name", "created_on", "experiment_buttons")
    list_filter = ["created_on"]
    search_fields = ["exp_name"]
    change_list_filter_template = "admin/filter_listing.html"

    def save_model(self, request, obj, form, change):
        """Assign the current user as owner when creating a new experiment."""
        if getattr(obj, "user", None) is None:
            obj.user = request.user
        obj.save()

    def get_queryset(self, request):
        """Return a QuerySet of experiments the requesting user can access."""
        qs = super().get_queryset(request)
        user_groups = request.user.groups.values_list("id", flat=True)
        user_owned = Q(user=request.user)
        shared_to_group = Q(sharing_option="GRP")
        shared_to_user_groups = Q(sharing_groups__in=user_groups)
        shared_to_everyone = Q(sharing_option="PUB")

        if request.user.is_superuser:
            return qs
        elif request.user.groups.exists():  # user belongs to group(s)
            return qs.filter(
                user_owned
                | shared_to_everyone
                | shared_to_group & shared_to_user_groups
            )
        else:
            return qs.filter(user_owned | shared_to_everyone)

    def has_change_permission(self, request, obj=None):
        """Check whether the requesting user has permission to change an experiment."""
        user_groups = request.user.groups.values_list("id")
        if not obj or (
            obj.sharing_option == "PUB"
            or (
                obj.sharing_option == "GRP"
                and user_groups.intersection(obj.sharing_groups.values_list("id"))
            )
        ):
            return True
        else:
            return obj.user == request.user or request.user.is_superuser

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

    experiment_buttons.allow_tags = True
    experiment_buttons.short_description = "Actions"

    @staticmethod
    def exportToJSON(experiment_id):
        """Create a JSON object of the experiment to be exported."""
        # Get all data
        experiment = Experiment.objects.filter(pk=experiment_id)
        lists = ListItem.objects.filter(experiment=experiment_id)
        outerblocks = OuterBlockItem.objects.filter(listitem__experiment=experiment_id)
        innerblocks = BlockItem.objects.filter(
            outerblockitem__listitem__experiment=experiment_id
        )
        trials = TrialItem.objects.filter(
            blockitem__outerblockitem__listitem__experiment=experiment_id
        )
        questions = Question.objects.filter(experiment=experiment_id)
        consentquestions = ConsentQuestion.objects.filter(experiment=experiment_id)

        # Serialize into JSON object
        json_data = {}
        json_data["experiment"] = json.loads(serializers.serialize("json", experiment))
        json_data["lists"] = json.loads(serializers.serialize("json", lists))
        json_data["outerblocks"] = json.loads(
            serializers.serialize("json", outerblocks)
        )
        json_data["innerblocks"] = json.loads(
            serializers.serialize("json", innerblocks)
        )
        json_data["trials"] = json.loads(serializers.serialize("json", trials))
        json_data["questions"] = json.loads(serializers.serialize("json", questions))
        json_data["consentquestions"] = json.loads(
            serializers.serialize("json", consentquestions)
        )

        return json_data

    @staticmethod
    def importFromJSON(request, data):
        """Import an experiment from JSON file data."""
        json_data = data.decode("utf-8")

        # Import experiment
        for experiment in serializers.deserialize(
            "json", json.dumps(json.loads(json_data)["experiment"])
        ):
            old_primary_key = str(experiment.object.id)

            experiment.object.created_on = timezone.now()
            experiment.object.user = request.user
            experiment.object.id = None

            # Save as new experiment
            experiment.save()
            new_primary_key = str(experiment.object.id)

            # Replace all experiment ids
            json_data = json_data.replace(old_primary_key, new_primary_key)

        # Import lists
        for listItem in serializers.deserialize(
            "json", json.dumps(json.loads(json_data)["lists"])
        ):
            old_primary_key = str(listItem.object.id)

            listItem.object.id = None

            # Save as new list
            listItem.save()
            new_primary_key = str(listItem.object.id)

            # Replace all list ids
            json_data = json_data.replace(
                f'"listitem": {old_primary_key},', f'"listitem": {new_primary_key},'
            )

        # Import outer blocks
        for outerBlockItem in serializers.deserialize(
            "json", json.dumps(json.loads(json_data)["outerblocks"])
        ):
            old_primary_key = str(outerBlockItem.object.id)

            outerBlockItem.object.id = None

            # Save as new outer block
            outerBlockItem.save()
            new_primary_key = str(outerBlockItem.object.id)

            # Replace all outer block ids
            json_data = json_data.replace(
                f'"outerblockitem": {old_primary_key},',
                f'"outerblockitem": {new_primary_key},',
            )

        # Import inner blocks
        for innerBlockItem in serializers.deserialize(
            "json", json.dumps(json.loads(json_data)["innerblocks"])
        ):
            old_primary_key = str(innerBlockItem.object.id)

            innerBlockItem.object.id = None

            # Save as new inner block
            innerBlockItem.save()
            new_primary_key = str(innerBlockItem.object.id)

            # Replace all inner block ids
            json_data = json_data.replace(
                f'"blockitem": {old_primary_key},', f'"blockitem": {new_primary_key},'
            )

        # Import trials
        for trialItem in serializers.deserialize(
            "json", json.dumps(json.loads(json_data)["trials"])
        ):
            old_primary_key = str(trialItem.object.id)

            trialItem.object.id = None

            # Save as new trial
            trialItem.save()
            new_primary_key = str(trialItem.object.id)

        # Import questions
        for question in serializers.deserialize(
            "json", json.dumps(json.loads(json_data)["questions"])
        ):
            old_primary_key = str(question.object.id)

            question.object.id = None

            # Save as new question
            question.save()
            new_primary_key = str(question.object.id)

        # Import consent questions
        for consentQuestion in serializers.deserialize(
            "json", json.dumps(json.loads(json_data)["consentquestions"])
        ):
            old_primary_key = str(consentQuestion.object.id)

            consentQuestion.object.id = None

            # Save as new consent question
            consentQuestion.save()
            new_primary_key = str(consentQuestion.object.id)


class ListItemAdmin(admin.ModelAdmin):
    """Admin for list items.

    These are hidden from the index and scoped to accessible experiments.
    """

    inlines = [OuterBlockItemInline]
    classes = ["grp-collapse grp-open"]
    list_display = (
        "list_name",
        "experiment",
    )

    def get_model_perms(self, request):
        """Return empty perms dict thus hiding the model from admin index."""
        return {}

    def get_queryset(self, request):
        """Return a QuerySet of list items the requesting user can access."""
        qs = super().get_queryset(request)
        user_groups = request.user.groups.values_list("id", flat=True)
        user_owned = Q(experiment__user=request.user)
        shared_to_group = Q(experiment__sharing_option="GRP")
        shared_to_user_groups = Q(experiment__sharing_groups__in=user_groups)
        shared_to_everyone = Q(experiment__sharing_option="PUB")

        if request.user.is_superuser:
            return qs
        elif request.user.groups.exists():  # user belongs to group(s)
            return qs.filter(
                user_owned
                | shared_to_everyone
                | shared_to_group & shared_to_user_groups
            )
        else:
            return qs.filter(user_owned | shared_to_everyone)


class OuterBlockItemAdmin(admin.ModelAdmin):
    """Admin for outer block items.

    These are hidden from the index and scoped to accessible experiments.
    """

    inlines = [BlockItemInline]
    classes = ["grp-collapse grp-open"]
    list_display = ("outer_block_name", "listitem", "get_experiment")

    def get_experiment(self, obj):
        """Return the experiment this outer block item belongs to."""
        return obj.listitem.experiment

    get_experiment.admin_order_field = "listitem"  # allow column order sorting
    get_experiment.short_description = "Experiment"  # rename column head

    def get_model_perms(self, request):
        """Return empty perms dict thus hiding the model from admin index."""
        return {}

    def get_queryset(self, request):
        """Return a QuerySet of outer block items the requesting user can access."""
        qs = super().get_queryset(request)
        user_groups = request.user.groups.values_list("id", flat=True)
        user_owned = Q(listitem__experiment__user=request.user)
        shared_to_group = Q(listitem__experiment__sharing_option="GRP")
        shared_to_user_groups = Q(listitem__experiment__sharing_groups__in=user_groups)
        shared_to_everyone = Q(listitem__experiment__sharing_option="PUB")

        if request.user.is_superuser:
            return qs
        elif request.user.groups.exists():  # user belongs to group(s)
            return qs.filter(
                user_owned
                | shared_to_group & shared_to_user_groups
                | shared_to_everyone
            )
        else:
            return qs.filter(user_owned | shared_to_everyone)


class BlockItemAdmin(admin.ModelAdmin):
    """Admin for inner block items.

    These are hidden from the index and scoped to accessible experiments.
    """

    inlines = [TrialItemInline]
    list_display = ("label", "outerblockitem", "get_listitem", "get_experiment")

    def get_listitem(self, obj):
        """Return the list item associated with the block item."""
        return obj.outerblockitem.listitem

    get_listitem.admin_order_field = "outerblockitem"  # allow column order sorting
    get_listitem.short_description = "List item"  # rename column head

    def get_experiment(self, obj):
        """Return the experiment associated with the block item."""
        return obj.outerblockitem.listitem.experiment

    get_experiment.admin_order_field = (
        "outerblockitem__listitem"  # allow column order sorting
    )
    get_experiment.short_description = "Experiment"  # rename column head

    def get_model_perms(self, request):
        """Return empty perms dict thus hiding the model from admin index."""
        return {}

    def get_queryset(self, request):
        """Return a QuerySet of inner block items the requesting user can access."""
        qs = super().get_queryset(request)
        user_groups = request.user.groups.values_list("id", flat=True)
        user_owned = Q(outerblockitem__listitem__experiment__user=request.user)
        shared_to_group = Q(outerblockitem__listitem__experiment__sharing_option="GRP")
        shared_to_user_groups = Q(
            outerblockitem__listitem__experiment__sharing_groups__in=user_groups
        )
        shared_to_everyone = Q(
            outerblockitem__listitem__experiment__sharing_option="PUB"
        )

        if request.user.is_superuser:
            return qs
        elif request.user.groups.exists():  # user belongs to group(s)
            return qs.filter(
                user_owned
                | shared_to_group & shared_to_user_groups
                | shared_to_everyone
            )
        else:
            return qs.filter(user_owned | shared_to_everyone)


class SubjectDataAdmin(admin.ModelAdmin):
    """Admin for participant records, with all response and trial result inlines."""

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

    def get_queryset(self, request):
        """Return a QuerySet of SubjectData the requesting user can access."""
        qs = super().get_queryset(request)
        user_groups = request.user.groups.values_list("id", flat=True)
        user_owned = Q(experiment__user=request.user)
        shared_to_group = Q(experiment__sharing_option="GRP")
        shared_to_user_groups = Q(experiment__sharing_groups__in=user_groups)
        shared_to_everyone = Q(experiment__sharing_option="PUB")

        if request.user.is_superuser:
            return qs
        elif request.user.groups.exists():  # user belongs to group(s)
            return qs.filter(
                user_owned
                | shared_to_group & shared_to_user_groups
                | shared_to_everyone
            )
        else:
            return qs.filter(user_owned | shared_to_everyone)

    def has_change_permission(self, request, obj=None):
        """Check whether the requesting user has permission to change subject data."""
        user_groups = request.user.groups.values_list("id")
        if not obj or (
            obj.experiment.sharing_option == "PUB"
            or (
                obj.experiment.sharing_option == "GRP"
                and user_groups.intersection(
                    obj.experiment.sharing_groups.values_list("id")
                )
            )
        ):
            return True
        else:
            return obj.experiment.user == request.user or request.user.is_superuser

    def has_add_permission(self, request, obj=None):
        """Disable adding SubjectData.

        These should only be created during an experiment.
        """
        return False


class TrialResultAdmin(admin.ModelAdmin):
    """Admin view for TrialResult (currently unused; kept for reference)."""

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

    webcam_file_link.allow_tags = True
    webcam_file_link.short_description = "Webcam file"

    def get_queryset(self, request):
        """Return trial results scoped to experiments the requesting user can access."""
        qs = super().get_queryset(request)
        user_groups = request.user.groups.values_list("id", flat=True)
        user_owned = Q(subject__experiment__user=request.user)
        shared_to_group = Q(subject__experiment__sharing_option="GRP")
        shared_to_user_groups = Q(subject__experiment__sharing_groups__in=user_groups)
        shared_to_everyone = Q(subject__experiment__sharing_option="PUB")

        if request.user.is_superuser:
            return qs
        elif request.user.groups.exists():  # user belongs to group(s)
            return qs.filter(
                user_owned
                | shared_to_group & shared_to_user_groups
                | shared_to_everyone
            )
        else:
            return qs.filter(user_owned | shared_to_everyone)

    def get_model_perms(self, request):
        """Return empty perms dict thus hiding the model from admin index."""
        return {}

    def has_change_permission(self, request, obj=None):
        """Allow changes only to TrialResults of experiments the user can access."""
        user_groups = request.user.groups.values_list("id")
        if not obj or (
            obj.subject.experiment.sharing_option == "PUB"
            or (
                obj.subject.experiment.sharing_option == "GRP"
                and user_groups.intersection(
                    obj.subject.experiment.sharing_groups.values_list("id")
                )
            )
        ):
            return True
        else:
            return (
                obj.subject.experiment.user == request.user or request.user.is_superuser
            )

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
