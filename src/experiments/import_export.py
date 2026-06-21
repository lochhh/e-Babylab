"""Export and import experiments as ZIP archives bundling all media files."""

import io
import json
import zipfile
from typing import Any

from django.core import serializers
from django.core.files.base import ContentFile
from django.db.models import Q
from django.http import HttpRequest
from django.utils import timezone
from filer.models import Folder
from filer.models.filemodels import File as FilerFile
from filer.models.imagemodels import Image as FilerImage

from .models import (
    BlockItem,
    ConsentQuestion,
    Experiment,
    Instrument,
    ListItem,
    OuterBlockItem,
    Question,
    TrialItem,
)

# Filer fields on TrialItem and Experiment that are bundled in the ZIP.
_TRIAL_FILE_FIELDS = ("audio_file", "visual_file")

def export_to_zip(experiment_id: Any) -> bytes:
    """Bundle an experiment's full hierarchy and all referenced media files into a ZIP.

    The returned archive contains:
    - ``experiment.json``: serialized experiment hierarchy plus a ``media_files``
      metadata dict mapping filer PKs to file metadata.
    - ``media/<pk>_<filename>``: raw bytes of every referenced filer file (audio,
      visual, loading image, and CDI instrument CSV files).

    Args:
        experiment_id: Primary key of the :class:`~experiments.models.Experiment`
            to export.

    Returns:
        ZIP archive as raw bytes.

    """
    experiment = Experiment.objects.get(pk=experiment_id)
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

    json_data = {
        "experiment": json.loads(serializers.serialize("json", [experiment])),
        "lists": json.loads(serializers.serialize("json", lists)),
        "outerblocks": json.loads(serializers.serialize("json", outerblocks)),
        "innerblocks": json.loads(serializers.serialize("json", innerblocks)),
        "trials": json.loads(serializers.serialize("json", trials)),
        "questions": json.loads(serializers.serialize("json", questions)),
        "consentquestions": json.loads(serializers.serialize("json", consentquestions)),
    }

    instrument = None
    if experiment.instrument_id is not None:
        instrument = experiment.instrument
        json_data["instrument"] = json.loads(
            serializers.serialize("json", [instrument])
        )

    # Collect unique filer objects referenced by this experiment.
    # Each entry is (filer_obj, source) where source is "experiment" or "instrument".
    filer_objects: dict[str, tuple[FilerFile, str]] = {}

    def _collect(filer_obj: FilerFile | None, source: str = "experiment") -> None:
        if filer_obj is not None:
            filer_objects[str(filer_obj.pk)] = (filer_obj, source)

    _collect(experiment.loading_image)
    for trial in trials:
        _collect(trial.audio_file)
        _collect(trial.visual_file)
    if instrument is not None:
        for field_name in Instrument._CSV_FILE_FIELDS:
            _collect(getattr(instrument, field_name), source="instrument")

    media_files = {
        pk: {
            "original_filename": obj.original_filename,
            "zip_path": f"media/{pk}_{obj.original_filename}",
            "is_image": isinstance(obj, FilerImage),
            "source": source,
        }
        for pk, (obj, source) in filer_objects.items()
    }
    json_data["media_files"] = media_files

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("experiment.json", json.dumps(json_data))
        for pk, (obj, _) in filer_objects.items():
            obj.file.open("rb")
            try:
                zf.writestr(media_files[pk]["zip_path"], obj.file.read())
            finally:
                obj.file.close()

    return buf.getvalue()


def _remap_fk(obj: Any, field_name: str, pk_map: dict) -> None:
    """Set obj.<field_name>_id to pk_map[old_value], handling type mismatches."""
    fk_attr = f"{field_name}_id"
    old_val = getattr(obj, fk_attr)
    if old_val is None:
        return
    new_val = pk_map.get(old_val)
    if new_val is None:
        new_val = pk_map.get(str(old_val))
    if new_val is not None:
        setattr(obj, fk_attr, new_val)


def _resolve_media(
    files_meta: dict,
    search_root: Folder,
    target_name: str,
    zip_file: zipfile.ZipFile,
    owner: Any,
) -> dict[str, str]:
    """Return ``{old_pk: new_pk}`` — reuse all existing files or create all fresh.

    Uses an all-or-nothing strategy: if every file in *files_meta* already
    exists under *search_root* (or a direct subfolder), all are reused.  If
    any single file is absent, every file is (re)created fresh under
    ``<search_root>/<target_name>/``.
    """
    if not files_meta:
        return {}
    found: dict[str, FilerFile] = {}
    for old_pk, meta in files_meta.items():
        obj = (
            FilerFile.objects.filter(original_filename=meta["original_filename"])
            .filter(Q(folder=search_root) | Q(folder__parent=search_root))
            .first()
        )
        if obj is None:
            break
        found[old_pk] = obj
    else:
        return {pk: str(obj.pk) for pk, obj in found.items()}

    folder, _ = Folder.objects.get_or_create(
        name=target_name,
        parent=search_root,
        defaults={"owner": owner},
    )
    pk_map: dict[str, str] = {}
    for old_pk, meta in files_meta.items():
        filename = meta["original_filename"]
        file_bytes = zip_file.read(meta["zip_path"])
        filer_obj = (
            FilerImage(
                original_filename=filename,
                folder=folder,
                owner=owner,
            )
            if meta["is_image"]
            else FilerFile(
                original_filename=filename,
                folder=folder,
                owner=owner,
            )
        )
        filer_obj.file.save(filename, ContentFile(file_bytes), save=True)
        pk_map[old_pk] = str(filer_obj.pk)
    return pk_map


def import_from_zip(request: HttpRequest, zip_bytes: bytes) -> None:
    """Recreate an experiment from a ZIP produced by :func:`export_to_zip`.

    On import:

    - Experiment media files (audio, visual, loading image) are checked
      against the ``experiments/`` root folder and all its direct subfolders.
      If **all** files are found, they are reused as-is.  If **any** file is
      missing, every file is (re)created fresh under ``experiments/<exp_name>/``.
    - The same all-or-nothing rule applies to CDI instrument CSV files checked
      against the ``instruments/`` hierarchy, creating under
      ``instruments/<instr_name>/`` when needed.
    - CDI instruments are matched by ``instr_name``; an existing instrument is
      reused, otherwise a new one is created.
    - If an experiment with the same name already exists on this instance, the
      imported experiment is renamed with a ``copy`` suffix
      (e.g. ``My Experiment copy``, ``My Experiment copy 1``, …).
    - The imported experiment is assigned to ``request.user``.

    Args:
        request: The current HTTP request; ``request.user`` becomes the owner of
            the imported experiment.
        zip_bytes: Raw bytes of a ZIP archive previously produced by
            :func:`export_to_zip`.

    """
    buf = io.BytesIO(zip_bytes)
    try:
        zip_file = zipfile.ZipFile(buf, "r")
    except zipfile.BadZipFile as exc:
        raise ValueError("The uploaded file is not a valid ZIP archive.") from exc

    with zip_file:
        try:
            raw = json.loads(zip_file.read("experiment.json").decode("utf-8"))
        except KeyError as exc:
            raise ValueError(
                "Invalid experiment archive: experiment.json not found in the ZIP."
            ) from exc

        exp_name = raw["experiment"][0]["fields"]["exp_name"]
        media_files = raw.get("media_files", {})

        # Step 1: Reconstruct filer media files using an all-or-nothing strategy.
        experiments_root = Folder.objects.get(name="experiments", parent=None)
        instruments_root, _ = Folder.objects.get_or_create(
            name="instruments", parent=None, defaults={"owner": request.user}
        )

        instr_name = (
            raw["instrument"][0]["fields"]["instr_name"]
            if "instrument" in raw
            else None
        )

        exp_media = {
            pk: meta
            for pk, meta in media_files.items()
            if meta.get("source") != "instrument"
        }
        instr_media = {
            pk: meta
            for pk, meta in media_files.items()
            if meta.get("source") == "instrument"
        }

        media_pk_map = {
            **_resolve_media(
                exp_media, experiments_root, exp_name, zip_file, request.user
            ),
            **(
                _resolve_media(
                    instr_media, instruments_root, instr_name,
                    zip_file, request.user,
                )
                if instr_name
                else {}
            ),
        }

    # Step 2: Handle CDI instrument — reuse by name or create fresh.
    new_instr_pk = None
    if "instrument" in raw:
        instr_name = raw["instrument"][0]["fields"]["instr_name"]
        existing_instr = Instrument.objects.filter(instr_name=instr_name).first()
        if existing_instr is not None:
            new_instr_pk = existing_instr.pk
        else:
            for instr in serializers.deserialize(
                "json", json.dumps(raw["instrument"])
            ):
                instr.object.id = None
                for field_name in Instrument._CSV_FILE_FIELDS:
                    _remap_fk(instr.object, field_name, media_pk_map)
                instr.save()
                new_instr_pk = instr.object.pk

    # Step 3: Ensure the imported experiment gets a unique name.
    candidate_name = exp_name
    if Experiment.objects.filter(exp_name=candidate_name).exists():
        candidate_name = f"{exp_name} copy"
        n = 1
        while Experiment.objects.filter(exp_name=candidate_name).exists():
            candidate_name = f"{exp_name} copy {n}"
            n += 1

    # Step 4: Import the experiment hierarchy with direct FK remapping.
    exp_pk_map: dict = {}
    for exp_obj in serializers.deserialize(
        "json", json.dumps(raw["experiment"])
    ):
        old_pk = exp_obj.object.pk
        exp_obj.object.id = None
        exp_obj.object.created_on = timezone.now()
        exp_obj.object.user = request.user
        exp_obj.object.exp_name = candidate_name
        _remap_fk(exp_obj.object, "loading_image", media_pk_map)
        if new_instr_pk is not None:
            exp_obj.object.instrument_id = new_instr_pk
        exp_obj.save()
        exp_pk_map[old_pk] = exp_obj.object.pk

    list_pk_map: dict = {}
    for list_item in serializers.deserialize(
        "json", json.dumps(raw["lists"])
    ):
        old_pk = list_item.object.pk
        list_item.object.id = None
        _remap_fk(list_item.object, "experiment", exp_pk_map)
        list_item.save()
        list_pk_map[old_pk] = list_item.object.pk

    outerblock_pk_map: dict = {}
    for outer in serializers.deserialize(
        "json", json.dumps(raw["outerblocks"])
    ):
        old_pk = outer.object.pk
        outer.object.id = None
        _remap_fk(outer.object, "listitem", list_pk_map)
        outer.save()
        outerblock_pk_map[old_pk] = outer.object.pk

    block_pk_map: dict = {}
    for inner in serializers.deserialize(
        "json", json.dumps(raw["innerblocks"])
    ):
        old_pk = inner.object.pk
        inner.object.id = None
        _remap_fk(inner.object, "outerblockitem", outerblock_pk_map)
        inner.save()
        block_pk_map[old_pk] = inner.object.pk

    for trial in serializers.deserialize("json", json.dumps(raw["trials"])):
        trial.object.id = None
        _remap_fk(trial.object, "blockitem", block_pk_map)
        for field_name in _TRIAL_FILE_FIELDS:
            _remap_fk(trial.object, field_name, media_pk_map)
        trial.save()

    for question in serializers.deserialize(
        "json", json.dumps(raw["questions"])
    ):
        question.object.id = None
        _remap_fk(question.object, "experiment", exp_pk_map)
        question.save()

    for cq in serializers.deserialize(
        "json", json.dumps(raw["consentquestions"])
    ):
        cq.object.id = None
        _remap_fk(cq.object, "experiment", exp_pk_map)
        cq.save()
