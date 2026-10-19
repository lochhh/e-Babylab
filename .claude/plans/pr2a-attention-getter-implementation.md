# PR 2a — Dwell Check + Attention Getters Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** When a trial's gaze dwell in its target area is below `min_dwell_time`, show that trial's attention getter (a flagged `TrialItem`) once, then continue the normal sequence; plus a read-only Mermaid flowchart of each list in the admin.

**Architecture:** Dwell is computed server-side in `nexttrial` from the gaze samples already stored on the latest `TrialResult` (pure helpers in new `gaze.py`, shared with the reporter). Attention getters are ordinary `TrialItem`s with `is_attention_getter=True`, skipped by the sequence and referenced via a self-FK. The admin gets clearer fieldsets, scoped FK choices, formset validation, a tiny JS toggle and a Mermaid diagram rendered from `flowchart.py`.

**Tech Stack:** Django 6.0 + Grappelli admin, PostgreSQL, pytest/pytest-django, Vitest (jsdom), Playwright, Mermaid 11 (jsdelivr CDN).

**Spec:** `.claude/plans/gaze-response-contingent-trial-presentation.md` → "Stage 2 — Live AOI / Dwell Time + Attention Getter Flow".

## Global Constraints

- **Ask the user before every commit.** Show the commit message; commit only on a yes.
- Commit messages: verb-first summary line, optional `- ` bullets explaining *why*; **no** `Co-Authored-By`, **no** `feat:`-style prefixes.
- Branch: `dwell-time` (already checked out).
- All Python commands run in the container: `docker compose -f docker-compose.dev.yml exec web <cmd>` (workdir `/usr/src/app`; tests mounted at `/usr/src/tests`). Focused runs: `docker compose -f docker-compose.dev.yml exec web uv run pytest /usr/src/tests/<path> -q --no-cov`. Full suite: `... uv run pytest /usr/src/tests -q` (wherever a step below says `uv run pytest -q`, add `/usr/src/tests`). From Git Bash prefix `MSYS_NO_PATHCONV=1`.
- JS unit tests: `cd tests && npm run test:unit`. E2E: `cd tests && npm run test:e2e` (dev server must be up).
- Edit frontend JS only in `src/experiments/static/experiments/js/`, never `src/static/`.
- Public functions in `gaze.py` / `flowchart.py`: precise type hints (no bare `dict`/`list`/`Any`) + Google-style docstrings (`Args:` with `name (type): ...`, `Returns:`).
- Django 6: `CheckConstraint(condition=...)` (the old `check=` kwarg is removed).
- Pre-commit runs ruff (auto-fix) and mypy; if a hook modifies files, re-`git add` and re-run the commit.
- Coordinates: 1-based cells; a coordinate `<= 0` or `>= size` on an axis → `0` on that axis ("off-screen", because WebGazer clamps off-screen predictions onto the edge).
- Dwell = Σ `min(Δt, 100 ms)` over consecutive sample pairs whose first sample is inside the target; off-screen samples never count, not even for `ANY`.
- An attention getter never has its own dwell check (no chaining); after it is shown the sequence continues (no repeat).

## Review Focus

1. **Malformed/untrusted `webgazer_data`** (non-list, missing keys, strings, NaN) must never 500 `nexttrial` — `parse_samples` drops bad entries (tests in Task 1).
2. **Resume after pause/reload** between a low-dwell trial and its attention getter must still show the attention getter (`experiment_run` goes through the same `_next_trials`) (test in Task 3).
3. **Import of an experiment with attention getters** must point the copied trials at the *copied* attention getters, not the source experiment's (test in Task 4).
4. **Deleting an attention getter still referenced** must be refused cleanly (PROTECT): `ProtectedError` test in Task 2; admin inline delete checkbox checked in Task 6's manual smoke step (Django's inline delete validation reports protected objects).
5. **Attention getter video shown more than once** must reuse its (iOS-unlocked) element rather than a fresh one that autoplay may block (Vitest in Task 3). Not testable on real iOS here — flag in PR description for manual check.

Also noted, not tested: dwell uses `screen.width/height` (posted resolution) while WebGazer clamps to the viewport; identical in fullscreen, which experiments require.

---

## File Map

| File | Change |
|---|---|
| `src/experiments/gaze.py` | **Create.** `GazeSample`, `Cell`, `MAX_SAMPLE_GAP_MS`, `roi_cell`, `parse_samples`, `dwell_time` |
| `src/experiments/flowchart.py` | **Create.** `list_flowchart(list_item) -> str` |
| `src/experiments/models.py` | `TrialItem`: new fields, constraints, `clean()` rules, `dwell_target` property; grid fields → `PositiveSmallIntegerField` |
| `src/experiments/migrations/0020_*.py` | **Generate** via `makemigrations` |
| `src/experiments/views.py` | Skip flagged trials; attention getter step in `_next_trials`; `experiment_end` count; `videos` incl. attention getters; `is_attention_getter` in trial dict |
| `src/experiments/reporter.py` | `calc_roi_response` → `roi_cell`; numbering ignores attention getter rows; `Dwell (ms)` column |
| `src/experiments/import_export.py` | Remap `attention_getter` self-FK on import |
| `src/experiments/admin.py` | Trial inline fieldsets, FK scoping, formset clean, toggle JS media; `ListItemAdmin.change_view` flowchart context |
| `src/experiments/templates/admin/experiments/listitem/change_form.html` | **Create.** Flowchart panel + Mermaid CDN |
| `src/experiments/static/experiments/js/experiment.js` | Keep attention getter video element (hide + rewind) instead of removing |
| `src/experiments/static/experiments/js/admin/attention-getter-toggle.js` | **Create.** Hide/clear dwell fieldset when flagged |
| `src/experiments/management/commands/{create,delete}_e2e_fixtures.py` | New attention getter e2e experiment |
| Tests | `tests/test_unit/test_gaze.py`, `test_flowchart.py` (new); `test_reporter.py`, `test_models.py`, `test_views.py`, `test_admin.py`, `test_import_export.py`; `tests/test_integration/test_views.py`; `tests/js/experiment.test.js`, `tests/js/attention-getter-toggle.test.js` (new); `tests/e2e/specs/attention-getter.spec.js` (new) |

---

### Task 1: `gaze.py` helpers + reporter delegation

**Files:**
- Create: `src/experiments/gaze.py`
- Modify: `src/experiments/reporter.py:106-125` (`calc_roi_response`)
- Test: `tests/test_unit/test_gaze.py` (new), `tests/test_unit/test_reporter.py:175-199`

**Interfaces:**
- Produces:
  - `class GazeSample(TypedDict): x: float; y: float; t: float`
  - `Cell = tuple[int, int]`
  - `MAX_SAMPLE_GAP_MS: float = 100.0`
  - `roi_cell(x: float, y: float, width: int, height: int, rows: int, cols: int) -> Cell`
  - `parse_samples(raw: object) -> list[GazeSample]`
  - `dwell_time(samples: Sequence[GazeSample], width: int, height: int, rows: int, cols: int, target: Cell | None) -> float`

- [ ] **Step 1: Write the failing tests** — create `tests/test_unit/test_gaze.py`:

```python
"""Unit tests for experiments/gaze.py."""

import pytest

from experiments.gaze import MAX_SAMPLE_GAP_MS, dwell_time, parse_samples, roi_cell


@pytest.mark.parametrize(
    "x,y,expected",
    [
        (10, 10, (1, 1)),
        (99, 99, (2, 2)),
        (50, 50, (1, 1)),  # on a boundary → lower cell, as before
        (51, 10, (1, 2)),
        (0, 50, (1, 0)),  # left edge → off-screen column
        (50, 0, (0, 1)),  # top edge → off-screen row
        (100, 50, (1, 0)),  # right edge (WebGazer clamp) → off-screen column
        (50, 100, (0, 1)),  # bottom edge → off-screen row
        (-5, 150, (0, 0)),  # outside on both axes
    ],
)
def test_roi_cell_2x2(x, y, expected):
    """Cells are 1-based; screen edges and beyond map to 0 on that axis."""
    assert roi_cell(x, y, 100, 100, 2, 2) == expected


def test_roi_cell_non_divisible_size_stays_within_grid():
    """A width not divisible by cols never yields a column beyond the grid."""
    assert roi_cell(100, 10, 101, 100, 1, 2) == (1, 2)


def test_roi_cell_zero_resolution_is_off_screen():
    """Missing resolution (legacy rows default to 0) maps to (0, 0), not an error."""
    assert roi_cell(10, 10, 0, 0, 2, 2) == (0, 0)


@pytest.mark.parametrize(
    "raw,expected",
    [
        (None, []),
        ("junk", []),
        ([{"x": 1, "y": 2, "t": 3}], [{"x": 1.0, "y": 2.0, "t": 3.0}]),
        ([{"x": 1, "y": 2}], []),  # missing t
        ([{"x": "a", "y": 2, "t": 3}], []),  # non-numeric
        ([{"x": "nan", "y": 2, "t": 3}], []),  # non-finite
        ([[1, 2, 3], {"x": 1, "y": 2, "t": 3}], [{"x": 1.0, "y": 2.0, "t": 3.0}]),
    ],
)
def test_parse_samples_drops_malformed_entries(raw, expected):
    """Client-supplied gaze data is filtered to well-formed finite samples."""
    assert parse_samples(raw) == expected


def _s(x, y, t):
    return {"x": x, "y": y, "t": t}


@pytest.mark.parametrize(
    "samples,target,expected",
    [
        ([], None, 0),
        ([_s(10, 10, 0)], None, 0),  # a single sample has no interval
        ([_s(10, 10, 0), _s(10, 10, 34), _s(10, 10, 68)], None, 68),
        ([_s(10, 10, 0), _s(90, 90, 34), _s(90, 90, 68)], (1, 1), 34),
        ([_s(10, 10, 0), _s(90, 90, 34), _s(90, 90, 68)], (2, 2), 34),
        ([_s(0, 10, 0), _s(10, 10, 34), _s(10, 10, 68)], None, 34),  # off-screen
        ([_s(10, 10, 0), _s(10, 10, 1000)], None, MAX_SAMPLE_GAP_MS),  # gap capped
        ([_s(10, 10, 50), _s(10, 10, 20)], None, 0),  # out-of-order never subtracts
    ],
)
def test_dwell_time(samples, target, expected):
    """Dwell sums capped sample intervals whose first sample is in the target."""
    assert dwell_time(samples, 100, 100, 2, 2, target) == expected
```

- [ ] **Step 2: Update the reporter test expectations** in `tests/test_unit/test_reporter.py`, the `test_calc_roi_response` parametrize list: change `([200, 200], "(2,2)"),  # out of positive bounds` to `([200, 200], "(0,0)"),  # beyond screen edge → off-screen` and add `([100, 50], "(1,0)"),  # right edge (WebGazer clamp) → off-screen column`.

- [ ] **Step 3: Run tests to verify they fail**

Run: `docker compose -f docker-compose.dev.yml exec web uv run pytest /usr/src/tests/test_unit/test_gaze.py /usr/src/tests/test_unit/test_reporter.py -q --no-cov`
Expected: `test_gaze.py` errors with `ModuleNotFoundError: No module named 'experiments.gaze'`; the two reporter cases fail.

- [ ] **Step 4: Implement** — create `src/experiments/gaze.py`:

```python
"""Pure gaze helpers: grid cells and dwell time from WebGazer samples.

Shared by the reporter (report time) and ``nexttrial`` (attention getter check).
"""

import math
from collections.abc import Sequence
from itertools import pairwise
from typing import TypedDict

MAX_SAMPLE_GAP_MS = 100.0
"""Longest interval credited to one sample; larger gaps mean the face was lost."""

Cell = tuple[int, int]
"""A 1-based ``(row, col)`` grid cell; 0 on an axis means off-screen."""


class GazeSample(TypedDict):
    """One WebGazer prediction as stored in ``TrialResult.webgazer_data``."""

    x: float
    y: float
    t: float


def _axis_cell(value: float, size: int, count: int) -> int:
    """Return the 1-based cell index of ``value`` along one axis, or 0 if off-screen."""
    if value <= 0 or value >= size:
        return 0
    return min(count, max(1, math.ceil(value * count / size)))


def roi_cell(x: float, y: float, width: int, height: int, rows: int, cols: int) -> Cell:
    """Return the grid cell containing a gaze or click coordinate.

    WebGazer clamps off-screen predictions onto the screen edge, so a coordinate
    on (or beyond) an edge is reported as 0 on that axis rather than as the
    edge cell.

    Args:
        x (float): Horizontal coordinate in pixels.
        y (float): Vertical coordinate in pixels.
        width (int): Screen width in pixels.
        height (int): Screen height in pixels.
        rows (int): Number of grid rows.
        cols (int): Number of grid columns.

    Returns:
        Cell: 1-based ``(row, col)``; an axis is 0 when off-screen.
    """
    return _axis_cell(y, height, rows), _axis_cell(x, width, cols)


def parse_samples(raw: object) -> list[GazeSample]:
    """Return the well-formed gaze samples from client-supplied JSON.

    Entries that are not objects, lack ``x``/``y``/``t``, or hold non-numeric
    or non-finite values are dropped, so malformed data can never raise.

    Args:
        raw (object): Decoded ``webgazer_data`` as stored on a ``TrialResult``.

    Returns:
        list[GazeSample]: Samples with float coordinates, in their original order.
    """
    if not isinstance(raw, list):
        return []
    samples: list[GazeSample] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        try:
            x, y, t = float(item["x"]), float(item["y"]), float(item["t"])
        except (KeyError, TypeError, ValueError):
            continue
        if all(math.isfinite(v) for v in (x, y, t)):
            samples.append(GazeSample(x=x, y=y, t=t))
    return samples


def dwell_time(
    samples: Sequence[GazeSample],
    width: int,
    height: int,
    rows: int,
    cols: int,
    target: Cell | None,
) -> float:
    """Return how long gaze stayed in the target, in milliseconds.

    Each interval between consecutive samples is credited to the first sample
    of the pair, capped at ``MAX_SAMPLE_GAP_MS``. Off-screen samples never count.

    Args:
        samples (Sequence[GazeSample]): Time-ordered gaze samples.
        width (int): Screen width in pixels.
        height (int): Screen height in pixels.
        rows (int): Number of grid rows.
        cols (int): Number of grid columns.
        target (Cell | None): Cell to measure, or ``None`` for any on-screen cell.

    Returns:
        float: Dwell time in milliseconds.
    """
    total = 0.0
    for current, following in pairwise(samples):
        cell = roi_cell(current["x"], current["y"], width, height, rows, cols)
        if 0 in cell or (target is not None and cell != target):
            continue
        total += min(max(following["t"] - current["t"], 0.0), MAX_SAMPLE_GAP_MS)
    return total
```

Then replace the body of `Reporter.calc_roi_response` in `src/experiments/reporter.py` (keep signature and docstring) and add `from .gaze import roi_cell` to the imports:

```python
    def calc_roi_response(self, result, coords):
        """Determine the row and column of a click or gaze within the trial's grid."""
        if len(coords) != 2:
            return ""
        row, col = roi_cell(
            coords[0],
            coords[1],
            result.resolution_w,
            result.resolution_h,
            result.trialitem.grid_row,
            result.trialitem.grid_col,
        )
        return f"({row},{col})"
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `docker compose -f docker-compose.dev.yml exec web uv run pytest /usr/src/tests/test_unit/test_gaze.py /usr/src/tests/test_unit/test_reporter.py -q --no-cov`
Expected: all PASS.

- [ ] **Step 6: Ask the user, then commit**

```bash
git add src/experiments/gaze.py src/experiments/reporter.py tests/test_unit/test_gaze.py tests/test_unit/test_reporter.py
git commit -m "Add gaze helpers for grid cells and dwell time" -m "- Reporter ROI now reports right/bottom screen edges as off-screen (0), matching left/top, since WebGazer clamps off-screen gaze onto the edge
- parse_samples guards against malformed client gaze data before it reaches nexttrial"
```

---

### Task 2: `TrialItem` fields, constraints, validation, migration

**Files:**
- Modify: `src/experiments/models.py:502-620` (`TrialItem`), imports at top
- Create (generated): `src/experiments/migrations/0020_trialitem_attention_getter_dwell.py`
- Test: `tests/test_unit/test_models.py`

**Interfaces:**
- Consumes: `Cell` from `experiments.gaze`.
- Produces:
  - `TrialItem.ANY = "ANY"`, `TrialItem.CELL = "CELL"`
  - fields `is_attention_getter: bool`, `attention_getter: TrialItem | None` (related_name `triggering_trials`, `on_delete=PROTECT`), `min_dwell_time: int | None`, `dwell_target_type: str`, `dwell_target_row: int | None`, `dwell_target_col: int | None`
  - property `TrialItem.dwell_target -> Cell | None` (`None` for `ANY`)

- [ ] **Step 1: Write the failing tests** — append to `tests/test_unit/test_models.py` (add imports `from django.core.exceptions import ValidationError`, `from django.db import IntegrityError, transaction`, `from django.db.models import ProtectedError` if not already present):

```python
# ---------------------------------------------------------------------------
# TrialItem attention getter / dwell check
# ---------------------------------------------------------------------------


@pytest.fixture
def ag_pair(trialitem_factory, blockitem_factory):
    """A normal trial and a flagged attention getter in another block of the same list."""
    trial = trialitem_factory(label="T1")
    ag_block = blockitem_factory(
        outerblock=trial.blockitem.outerblockitem, label="AGs", position=2
    )
    ag = trialitem_factory(blockitem=ag_block, label="AG", code="AG")
    ag.is_attention_getter = True
    ag.save()
    return trial, ag


@pytest.mark.django_db
def test_trialitem_clean_accepts_dwell_check(ag_pair):
    """A trial with an attention getter and a minimum dwell time is valid."""
    trial, ag = ag_pair
    trial.attention_getter = ag
    trial.min_dwell_time = 500
    trial.full_clean()


def _other_list_ag(trial, ag, trialitem_factory):
    other = trialitem_factory(label="AG2", code="AG2")  # new experiment/list
    other.is_attention_getter = True
    other.save()
    trial.attention_getter = other
    trial.min_dwell_time = 500


@pytest.mark.django_db
@pytest.mark.parametrize(
    "mutate,message",
    [
        (lambda t, ag: setattr(t, "attention_getter", ag), "or neither"),
        (lambda t, ag: setattr(t, "min_dwell_time", 500), "or neither"),
        (
            lambda t, ag: (
                setattr(ag, "is_attention_getter", False),
                ag.save(),
                setattr(t, "attention_getter", ag),
                setattr(t, "min_dwell_time", 500),
            ),
            "marked as an attention getter",
        ),
        (
            lambda t, ag: (
                setattr(t, "attention_getter", ag),
                setattr(t, "min_dwell_time", 500),
                setattr(t, "is_calibration", True),
            ),
            "calibration",
        ),
        (lambda t, ag: setattr(t, "dwell_target_type", "CELL"), "target row and column"),
        (
            lambda t, ag: (
                setattr(t, "dwell_target_type", "CELL"),
                setattr(t, "dwell_target_row", 2),
                setattr(t, "dwell_target_col", 1),
            ),
            "only has 1 row",
        ),
        (
            lambda t, ag: (
                setattr(ag, "attention_getter", ag),
                setattr(ag, "min_dwell_time", 500),
            ),
            "cannot have its own dwell check",
        ),
        (lambda t, ag: setattr(t, "grid_row", 0), "greater than or equal to 1"),
    ],
)
def test_trialitem_clean_rejects_invalid_dwell_config(ag_pair, mutate, message):
    """Invalid dwell-check configurations raise a ValidationError naming the problem."""
    trial, ag = ag_pair
    mutate(trial, ag)
    target = ag if ag.attention_getter_id else trial
    with pytest.raises(ValidationError, match=message):
        target.full_clean()


@pytest.mark.django_db
def test_trialitem_clean_rejects_attention_getter_from_other_list(
    ag_pair, trialitem_factory
):
    """The attention getter must belong to the same list as the trial."""
    trial, ag = ag_pair
    _other_list_ag(trial, ag, trialitem_factory)
    with pytest.raises(ValidationError, match="same list"):
        trial.full_clean()


@pytest.mark.django_db
def test_trialitem_clean_rejects_unflagging_referenced_attention_getter(ag_pair):
    """A trial cannot stop being an attention getter while trials still use it."""
    trial, ag = ag_pair
    trial.attention_getter, trial.min_dwell_time = ag, 500
    trial.save()
    ag.is_attention_getter = False
    with pytest.raises(ValidationError, match="T1"):
        ag.full_clean()


@pytest.mark.django_db
def test_trialitem_db_constraint_rejects_half_dwell_check(ag_pair):
    """The database refuses a dwell threshold without an attention getter."""
    trial, _ = ag_pair
    with pytest.raises(IntegrityError), transaction.atomic():
        type(trial).objects.filter(pk=trial.pk).update(min_dwell_time=500)


@pytest.mark.django_db
def test_deleting_referenced_attention_getter_is_protected(ag_pair):
    """An attention getter in use cannot be deleted."""
    trial, ag = ag_pair
    trial.attention_getter, trial.min_dwell_time = ag, 500
    trial.save()
    with pytest.raises(ProtectedError):
        ag.delete()


@pytest.mark.django_db
@pytest.mark.parametrize(
    "target_type,row,col,expected",
    [("ANY", None, None, None), ("CELL", 1, 2, (1, 2))],
)
def test_trialitem_dwell_target(trialitem_factory, target_type, row, col, expected):
    """dwell_target is None for ANY and the (row, col) cell for CELL."""
    trial = trialitem_factory()
    trial.dwell_target_type, trial.dwell_target_row, trial.dwell_target_col = (
        target_type,
        row,
        col,
    )
    assert trial.dwell_target == expected
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `docker compose -f docker-compose.dev.yml exec web uv run pytest /usr/src/tests/test_unit/test_models.py -q --no-cov`
Expected: new tests FAIL (unknown attributes / no ValidationError).

- [ ] **Step 3: Implement** in `src/experiments/models.py`. Add imports `from django.core.validators import MinValueValidator`, `from django.db.models import Q` and `from .gaze import Cell` (check none exist already). In `TrialItem`:

Add constants next to `NO`/`YES`:

```python
    ANY = "ANY"
    CELL = "CELL"

    DWELL_TARGET_OPTIONS = (
        (ANY, "Anywhere on screen"),
        (CELL, "Specific grid cell"),
    )
```

Replace `grid_row`/`grid_col` and add the new fields before `position`:

```python
    grid_row = models.PositiveSmallIntegerField(
        "rows", default=1, validators=[MinValueValidator(1)]
    )
    grid_col = models.PositiveSmallIntegerField(
        "columns", default=1, validators=[MinValueValidator(1)]
    )
    is_attention_getter = models.BooleanField(
        "use as attention getter",
        default=False,
        help_text=(
            "Attention getters are skipped in the normal trial order and only shown"
            " when another trial's dwell check fails. Keeping them in a dedicated"
            " block lets them use that block's background colour."
        ),
    )
    attention_getter = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="triggering_trials",
        limit_choices_to={"is_attention_getter": True},
        help_text=(
            "Shown after this trial if the dwell check fails; the trial order then"
            " continues as normal."
        ),
    )
    min_dwell_time = models.PositiveIntegerField(
        "minimum dwell time (ms)",
        null=True,
        blank=True,
        help_text="Show the attention getter if gaze dwell in the target is below this.",
    )
    dwell_target_type = models.CharField(
        "dwell target",
        max_length=4,
        choices=DWELL_TARGET_OPTIONS,
        default=ANY,
    )
    dwell_target_row = models.PositiveSmallIntegerField(
        "target row", null=True, blank=True, validators=[MinValueValidator(1)]
    )
    dwell_target_col = models.PositiveSmallIntegerField(
        "target column", null=True, blank=True, validators=[MinValueValidator(1)]
    )
```

Replace `class Meta`:

```python
    class Meta:
        """Orders trials by position and guards dwell-check consistency."""

        ordering = ["position"]
        constraints = [
            models.CheckConstraint(
                condition=Q(attention_getter__isnull=True, min_dwell_time__isnull=True)
                | Q(attention_getter__isnull=False, min_dwell_time__isnull=False),
                name="trialitem_dwell_check_complete",
                violation_error_message=(
                    "Set both an attention getter and a minimum dwell time, or neither."
                ),
            ),
            models.CheckConstraint(
                condition=Q(is_attention_getter=False)
                | Q(attention_getter__isnull=True),
                name="trialitem_attention_getter_not_nested",
                violation_error_message=(
                    "An attention getter cannot have its own dwell check."
                ),
            ),
            models.CheckConstraint(
                condition=Q(grid_row__gte=1, grid_col__gte=1),
                name="trialitem_grid_positive",
            ),
            models.CheckConstraint(
                condition=(Q(dwell_target_row__isnull=True) | Q(dwell_target_row__gte=1))
                & (Q(dwell_target_col__isnull=True) | Q(dwell_target_col__gte=1)),
                name="trialitem_dwell_target_positive",
            ),
        ]
```

Replace `clean()` and add the property:

```python
    def clean(self):
        """Validate file extensions and the dwell-check configuration."""
        errors = {}
        _validate_file_extension(
            self.audio_file, self._AUDIO_EXTENSIONS, "audio_file", errors
        )
        _validate_file_extension(
            self.visual_file, self._VISUAL_EXTENSIONS, "visual_file", errors
        )
        self._validate_dwell_check(errors)
        if errors:
            raise ValidationError(errors)

    def _validate_dwell_check(self, errors):
        """Add cross-field and cross-row dwell-check errors to ``errors``."""
        ag = self.attention_getter
        if ag is not None:
            if not ag.is_attention_getter:
                errors["attention_getter"] = (
                    "Choose a trial marked as an attention getter."
                )
            elif self.blockitem_id and (
                ag.blockitem.outerblockitem.listitem_id
                != self.blockitem.outerblockitem.listitem_id
            ):
                errors["attention_getter"] = (
                    "The attention getter must be in the same list as this trial."
                )
        if self.min_dwell_time is not None and self.is_calibration:
            errors["min_dwell_time"] = (
                "Dwell checks are not available on calibration trials."
            )
        if self.dwell_target_type == self.CELL:
            if self.dwell_target_row is None or self.dwell_target_col is None:
                errors["dwell_target_type"] = (
                    "Set a target row and column for a specific grid cell."
                )
            else:
                if self.dwell_target_row > self.grid_row:
                    errors["dwell_target_row"] = (
                        f"The grid only has {self.grid_row} row(s)."
                    )
                if self.dwell_target_col > self.grid_col:
                    errors["dwell_target_col"] = (
                        f"The grid only has {self.grid_col} column(s)."
                    )
        if self.pk and not self.is_attention_getter:
            users = list(
                TrialItem.objects.filter(attention_getter_id=self.pk).values_list(
                    "label", flat=True
                )
            )
            if users:
                errors["is_attention_getter"] = (
                    "Still used as the attention getter of: "
                    f"{', '.join(users)}. Remove those references first."
                )

    @property
    def dwell_target(self) -> Cell | None:
        """Return the dwell-check target cell, or None for anywhere on screen."""
        if self.dwell_target_type == self.CELL:
            return (self.dwell_target_row, self.dwell_target_col)
        return None
```

Note: `full_clean()` also runs `validate_constraints()`, which is where the two "or neither" / "own dwell check" messages come from.

- [ ] **Step 4: Generate the migration**

Run: `docker compose -f docker-compose.dev.yml exec web uv run python manage.py makemigrations experiments -n trialitem_attention_getter_dwell`
Expected: `0020_trialitem_attention_getter_dwell.py` with AlterField grid_row/grid_col, AddField ×6, AddConstraint ×4. Then `docker compose -f docker-compose.dev.yml exec web uv run python manage.py migrate` succeeds.

- [ ] **Step 5: Run tests to verify they pass** — the model tests, then the whole suite (field type change must not break anything):

Run: `docker compose -f docker-compose.dev.yml exec web uv run pytest /usr/src/tests/test_unit/test_models.py -q --no-cov` → PASS
Run: `docker compose -f docker-compose.dev.yml exec web uv run pytest -q` → PASS

- [ ] **Step 6: Ask the user, then commit**

```bash
git add src/experiments/models.py src/experiments/migrations/0020_trialitem_attention_getter_dwell.py tests/test_unit/test_models.py
git commit -m "Add attention getter and dwell check fields to TrialItem" -m "- DB constraints guard same-row rules so import and shell edits can't bypass them; clean() covers cross-row rules
- PROTECT on the attention getter FK so a referenced attention getter can't be deleted and leave a half-configured dwell check
- Grid row/col become positive small ints since 0 or negative grids break ROI maths"
```

---

### Task 3: Runtime — sequence, `nexttrial`, end page, videos, attention getter video reuse

**Files:**
- Modify: `src/experiments/views.py:208-297` (`_trial_sequence`, `_next_trials`, `create_trial_dict`), `:316-323` (`videos`), `:439-458` (`experiment_end`); imports
- Modify: `src/experiments/static/experiments/js/experiment.js:470-482` (`removeTrialVideo`)
- Test: `tests/test_integration/test_views.py`, `tests/test_unit/test_views.py:43-74,208-229`, `tests/js/experiment.test.js`

**Interfaces:**
- Consumes: `parse_samples`, `dwell_time` (Task 1); `TrialItem.is_attention_getter`, `.attention_getter`, `.min_dwell_time`, `.dwell_target` (Task 2).
- Produces: trial dict key `"is_attention_getter": bool`; `_attention_getter_dict(subject_data: SubjectData) -> dict | None`; `nexttrial` returns `{"done": False, "trial": <attention getter dict>, "upcoming": <next pending>}` after a failed dwell check.

- [ ] **Step 1: Write the failing integration tests** — append to `tests/test_integration/test_views.py` before the `experimentEnd` section:

```python
# ---------------------------------------------------------------------------
# Attention getter / dwell check
# ---------------------------------------------------------------------------


@pytest.fixture
def dwell_experiment(experiment_with_trials, blockitem_factory, trialitem_factory):
    """EYE experiment: T1 (dwell check 500 ms → AG), T2, and AG in its own block."""
    exp, listitem, trial = experiment_with_trials
    exp.recording_option = "EYE"
    exp.save()
    second = trialitem_factory(
        blockitem=trial.blockitem, label="Trial2", code="C2", position=2
    )
    ag_block = blockitem_factory(
        outerblock=trial.blockitem.outerblockitem, label="AGs", position=2
    )
    ag = trialitem_factory(blockitem=ag_block, label="AG", code="AG")
    ag.is_attention_getter = True
    ag.save()
    trial.attention_getter, trial.min_dwell_time = ag, 500
    trial.save()
    return exp, listitem, trial, second, ag


def _store(sd, trial, dwell_ms, trial_number=1):
    """Store a result whose on-screen gaze totals dwell_ms (multiple of 25)."""
    samples = [{"x": 10, "y": 10, "t": float(t)} for t in range(0, dwell_ms + 1, 25)]
    return exp_models.TrialResult.objects.create(
        subject=sd,
        trialitem=trial,
        trial_number=trial_number,
        key_pressed="",
        resolution_w=100,
        resolution_h=100,
        webgazer_data=samples,
    )


def _next(client, sd):
    return json.loads(
        client.post(reverse("experiments:nextTrial", args=[sd.pk])).content
    )


class TestAttentionGetter:
    """nexttrial shows a trial's attention getter once when dwell is too low."""

    @pytest.mark.django_db
    def test_low_dwell_returns_attention_getter(
        self, client, subjectdata_factory, dwell_experiment
    ):
        """Dwell below threshold → AG with the trial's number, then T2 upcoming."""
        exp, listitem, trial, second, ag = dwell_experiment
        sd = subjectdata_factory(experiment=exp, listitem=listitem)
        _store(sd, trial, 250)
        data = _next(client, sd)
        assert data["trial"]["trial_id"] == ag.pk
        assert data["trial"]["trial_number"] == 1
        assert data["trial"]["is_attention_getter"] is True
        assert data["upcoming"]["trial_id"] == second.pk

    @pytest.mark.django_db
    @pytest.mark.parametrize("dwell_ms", [500, 750])
    def test_enough_dwell_continues_sequence(
        self, client, subjectdata_factory, dwell_experiment, dwell_ms
    ):
        """Dwell at or above threshold → next trial in sequence."""
        exp, listitem, trial, second, _ = dwell_experiment
        sd = subjectdata_factory(experiment=exp, listitem=listitem)
        _store(sd, trial, dwell_ms)
        assert _next(client, sd)["trial"]["trial_id"] == second.pk

    @pytest.mark.django_db
    def test_no_gaze_samples_counts_as_zero_dwell(
        self, client, subjectdata_factory, dwell_experiment
    ):
        """A trial with no gaze samples at all triggers the attention getter."""
        exp, listitem, trial, _, ag = dwell_experiment
        sd = subjectdata_factory(experiment=exp, listitem=listitem)
        result = _store(sd, trial, 0)
        result.webgazer_data = []
        result.save()
        assert _next(client, sd)["trial"]["trial_id"] == ag.pk

    @pytest.mark.django_db
    def test_malformed_gaze_data_does_not_error(
        self, client, subjectdata_factory, dwell_experiment
    ):
        """Garbage webgazer_data is treated as no samples, never a 500."""
        exp, listitem, trial, _, ag = dwell_experiment
        sd = subjectdata_factory(experiment=exp, listitem=listitem)
        result = _store(sd, trial, 0)
        result.webgazer_data = [{"x": "a"}, 5, None]
        result.save()
        assert _next(client, sd)["trial"]["trial_id"] == ag.pk

    @pytest.mark.django_db
    def test_attention_getter_shown_once_then_sequence_continues(
        self, client, subjectdata_factory, dwell_experiment
    ):
        """After the AG's result is stored, the sequence moves on."""
        exp, listitem, trial, second, ag = dwell_experiment
        sd = subjectdata_factory(experiment=exp, listitem=listitem)
        _store(sd, trial, 0)
        _store(sd, ag, 0)
        assert _next(client, sd)["trial"]["trial_id"] == second.pk

    @pytest.mark.django_db
    def test_attention_getter_after_last_trial_then_done(
        self, client, subjectdata_factory, dwell_experiment
    ):
        """A failed check on the final trial still shows the AG before finishing."""
        exp, listitem, trial, second, ag = dwell_experiment
        second.attention_getter, second.min_dwell_time = ag, 500
        second.save()
        sd = subjectdata_factory(experiment=exp, listitem=listitem)
        _store(sd, trial, 500)
        _store(sd, second, 0, trial_number=2)
        data = _next(client, sd)
        assert data["trial"]["trial_id"] == ag.pk
        assert data["upcoming"] is None
        _store(sd, ag, 0, trial_number=2)
        assert _next(client, sd) == {"done": True}

    @pytest.mark.django_db
    @pytest.mark.parametrize("recording_option", ["NON", "AUD", "VID"])
    def test_no_check_without_eye_tracking(
        self, client, subjectdata_factory, dwell_experiment, recording_option
    ):
        """Dwell is only checked when the experiment records eye-tracking."""
        exp, listitem, trial, second, _ = dwell_experiment
        exp.recording_option = recording_option
        exp.save()
        sd = subjectdata_factory(experiment=exp, listitem=listitem)
        _store(sd, trial, 0)
        assert _next(client, sd)["trial"]["trial_id"] == second.pk

    @pytest.mark.django_db
    def test_no_check_when_trial_does_not_record_gaze(
        self, client, subjectdata_factory, dwell_experiment
    ):
        """Dwell is only checked for trials with eye-tracking enabled."""
        exp, listitem, trial, second, _ = dwell_experiment
        trial.record_gaze = False
        trial.save()
        sd = subjectdata_factory(experiment=exp, listitem=listitem)
        _store(sd, trial, 0)
        assert _next(client, sd)["trial"]["trial_id"] == second.pk

    @pytest.mark.django_db
    def test_pause_between_trial_and_attention_getter_still_shows_it(
        self, client, subjectdata_factory, dwell_experiment
    ):
        """A PAUSE row after the failed trial does not hide the attention getter."""
        exp, listitem, trial, _, ag = dwell_experiment
        sd = subjectdata_factory(experiment=exp, listitem=listitem)
        _store(sd, trial, 0)
        exp_models.TrialResult.objects.create(
            subject=sd, trialitem=trial, key_pressed="PAUSE", trial_number=2
        )
        assert _next(client, sd)["trial"]["trial_id"] == ag.pk

    @pytest.mark.django_db
    def test_attention_getters_skipped_in_sequence(
        self, client, subjectdata_factory, dwell_experiment
    ):
        """Flagged trials never appear as regular trials."""
        exp, listitem, trial, second, _ = dwell_experiment
        sd = subjectdata_factory(experiment=exp, listitem=listitem)
        _store(sd, trial, 500)
        _store(sd, second, 500, trial_number=2)
        assert _next(client, sd) == {"done": True}

    @pytest.mark.django_db
    def test_experiment_run_resumes_with_attention_getter(
        self, client, subjectdata_factory, dwell_experiment
    ):
        """Reloading /run after a failed check starts with the attention getter."""
        exp, listitem, trial, _, ag = dwell_experiment
        exp.experiment_page_tpl = "{% autoescape off %}{{ trials }}{% endautoescape %}"
        exp.save()
        sd = subjectdata_factory(experiment=exp, listitem=listitem)
        _store(sd, trial, 0)
        url = reverse("experiments:experimentRun", args=[sd.pk])
        payload = json.loads(client.get(url).content.decode())
        assert payload["trial"]["trial_id"] == ag.pk

    @pytest.mark.django_db
    def test_experiment_run_videos_include_attention_getters(
        self, client, subjectdata_factory, filer_file_factory, dwell_experiment
    ):
        """AG videos get an element up front so iOS can unlock them."""
        exp, listitem, _, _, ag = dwell_experiment
        ag.visual_file = filer_file_factory("spinner.mp4")
        ag.save()
        exp.experiment_page_tpl = "{% autoescape off %}{{ trials }}{% endautoescape %}"
        exp.save()
        sd = subjectdata_factory(experiment=exp, listitem=listitem)
        url = reverse("experiments:experimentRun", args=[sd.pk])
        payload = json.loads(client.get(url).content.decode())
        assert {"trial_id": ag.pk, "visual_file": ag.visual_file.url} in payload[
            "videos"
        ]

    @pytest.mark.django_db
    @pytest.mark.parametrize(
        "completed,expected",
        [("trials", b"COMPLETE"), ("first_and_ag", b"INCOMPLETE")],
    )
    def test_experiment_end_ignores_attention_getters(
        self, client, subjectdata_factory, dwell_experiment, completed, expected
    ):
        """Completion counts distinct regular trials only; AG results don't count."""
        exp, listitem, trial, second, ag = dwell_experiment
        exp.thank_you_page_tpl, exp.thank_you_abort_page_tpl = "COMPLETE", "INCOMPLETE"
        exp.save()
        sd = subjectdata_factory(experiment=exp, listitem=listitem)
        _store(sd, trial, 500)
        _store(sd, second if completed == "trials" else ag, 500, trial_number=2)
        response = client.get(reverse("experiments:experimentEnd", args=[sd.pk]))
        # equality, not `in`: b"COMPLETE" is a substring of b"INCOMPLETE"
        assert response.content.strip() == expected
```

- [ ] **Step 2: Update the unit test for trial dict keys** in `tests/test_unit/test_views.py`: in `_mock_trial` add parameter `is_attention_getter=False` and line `trial.is_attention_getter = is_attention_getter`; in `test_all_expected_keys_present` add `"is_attention_getter",` to `expected_keys`.

- [ ] **Step 3: Write the failing Vitest test** — append inside `describe('experiment.js — video trial', ...)` in `tests/js/experiment.test.js`:

```js
  it('keeps an attention getter video element (hidden, rewound) for reuse', async () => {
    HTMLVideoElement.prototype.play = vi.fn().mockReturnValue(Promise.resolve())
    makeEnv({
      recordingOption: 'NON',
      trials: [makeTrial({ trial_type: 'video', require_user_input: 'NO', is_attention_getter: true })],
    })
    await flush()
    document.getElementById('fullscreen-button').click()
    await flush()
    const video = document.querySelector('#video-container-1 > video')
    video.dispatchEvent(new Event('canplay'))
    await vi.advanceTimersByTimeAsync(1)
    await flush()
    video.currentTime = 3
    video.dispatchEvent(new Event('ended'))
    await flush()
    const container = document.querySelector('#video-container-1')
    expect(container).not.toBeNull()          // regular trials remove it
    expect(container.style.display).toBe('none')
    expect(video.currentTime).toBe(0)
  })
```

- [ ] **Step 4: Run tests to verify they fail**

Run: `docker compose -f docker-compose.dev.yml exec web uv run pytest /usr/src/tests/test_integration/test_views.py /usr/src/tests/test_unit/test_views.py -q --no-cov`
Expected: new `TestAttentionGetter` tests and the keys test FAIL.
Run: `cd tests && npm run test:unit` → the new video test FAILS (container removed).

- [ ] **Step 5: Implement views** in `src/experiments/views.py`. Add `from itertools import chain` and `from .gaze import dwell_time, parse_samples` to imports.

In `_trial_sequence`, change the trial query line to skip attention getters:

```python
            trial_items = list(
                block.trialitem_set.filter(is_attention_getter=False).order_by(
                    "position"
                )
            )
```

and add to its docstring: "Attention getters are never part of the sequence."

Add above `_next_trials`:

```python
_EYE_TRACKING_OPTIONS = ("EYE", "ALL")


def _attention_getter_dict(subject_data):
    """Return the attention getter trial dict if the last trial failed its dwell check.

    Only the latest non-PAUSE result is checked, so once the attention getter's
    own result is stored the sequence simply continues. It keeps the triggering
    trial's number so report rows pair up.
    """
    last = (
        TrialResult.objects.filter(subject=subject_data)
        .exclude(key_pressed="PAUSE")
        .select_related("trialitem__attention_getter__blockitem")
        .order_by("-pk")
        .first()
    )
    if last is None:
        return None
    trial = last.trialitem
    if (
        trial.attention_getter is None
        or trial.is_calibration
        or not trial.record_gaze
        or subject_data.experiment.recording_option not in _EYE_TRACKING_OPTIONS
    ):
        return None
    dwell = dwell_time(
        parse_samples(last.webgazer_data),
        last.resolution_w,
        last.resolution_h,
        trial.grid_row,
        trial.grid_col,
        trial.dwell_target,
    )
    if dwell >= trial.min_dwell_time:
        return None
    ag = trial.attention_getter
    return create_trial_dict(ag, ag.blockitem, last.trial_number)
```

Replace `_next_trials`:

```python
def _next_trials(subject_data):
    """Return the next trial dict and the one after it, either may be None.

    The next trial is the last trial's attention getter if its dwell check
    failed, otherwise the next pending trial. The second one lets the frontend
    preload its video during the current trial.
    """
    pending = _pending_trials(subject_data)
    first, second = (
        create_trial_dict(*t) if t else None
        for t in (next(pending, None), next(pending, None))
    )
    attention_getter = _attention_getter_dict(subject_data)
    if attention_getter:
        return [attention_getter, first]
    return [first, second]
```

In `create_trial_dict` add to `trial_dict`: `"is_attention_getter": trial.is_attention_getter,`.

In `experiment_run`, replace the `videos` comprehension:

```python
        # Every pending video trial plus every attention getter video, so the page
        # can create and unlock (iOS) a video element for each before the
        # participant's fullscreen tap
        attention_getters = TrialItem.objects.filter(
            blockitem__outerblockitem__listitem=subject_data.listitem,
            is_attention_getter=True,
        ).select_related("blockitem")
        videos = [
            {"trial_id": d["trial_id"], "visual_file": d["visual_file"]}
            for d in chain(
                (create_trial_dict(*t) for t in _pending_trials(subject_data)),
                (create_trial_dict(ag, ag.blockitem, 0) for ag in attention_getters),
            )
            if d["trial_type"] == "video"
        ]
```

In `experiment_end`, replace the two counts:

```python
        tr_count = TrialItem.objects.filter(
            blockitem__outerblockitem__listitem=subject_data.listitem,
            is_attention_getter=False,
        ).count()
        completed_count = (
            TrialResult.objects.filter(
                subject=run_uuid, trialitem__is_attention_getter=False
            )
            .exclude(key_pressed="PAUSE")
            .values("trialitem")
            .distinct()
            .count()
        )
```

- [ ] **Step 6: Implement the JS change** — in `src/experiments/static/experiments/js/experiment.js` replace the last two lines of `removeTrialVideo` (`video.pause();` and the `.remove()` line):

```js
        video.pause();
        const container = document.querySelector(`#video-container-${trialObj.trial_id}`);
        if (trialObj.is_attention_getter) {
            // Attention getters can be shown again; keep the element that was
            // unlocked for autoplay (iOS) rather than creating a fresh one.
            container.style.display = 'none';
            video.currentTime = 0;
        } else {
            container.remove();
        }
```

- [ ] **Step 7: Run tests to verify they pass**

Run: `docker compose -f docker-compose.dev.yml exec web uv run pytest -q` → all PASS
Run: `cd tests && npm run test:unit` → all PASS

- [ ] **Step 8: Ask the user, then commit**

```bash
git add src/experiments/views.py src/experiments/static/experiments/js/experiment.js tests/test_integration/test_views.py tests/test_unit/test_views.py tests/js/experiment.test.js
git commit -m "Show attention getter when a trial's dwell check fails" -m "- nexttrial and experiment_run share _next_trials, so a pause or reload between the trial and its attention getter still shows it
- Completion counts distinct regular trials so attention getter rows can't make an aborted run look complete
- Attention getter video elements are kept and rewound instead of removed, so a repeat showing reuses the element iOS unlocked"
```

---

### Task 4: Import/export remaps the attention getter self-FK

**Files:**
- Modify: `src/experiments/import_export.py` (trial loop in `import_from_zip`, ~line 343)
- Test: `tests/test_unit/test_import_export.py` (`TestImportFromZip`)

**Interfaces:**
- Consumes: `TrialItem.is_attention_getter`, `.attention_getter` (Task 2); existing `_remap_fk(obj, field_name, pk_map)`.

- [ ] **Step 1: Write the failing test** — add to `TestImportFromZip`:

```python
    @pytest.mark.django_db
    def test_import_remaps_attention_getter_to_copied_trial(
        self,
        experiment_factory,
        listitem_factory,
        outerblock_factory,
        blockitem_factory,
        trialitem_factory,
        mock_request,
    ):
        """Imported trials point at the imported attention getter, not the source."""
        exp = experiment_factory(exp_name="AGExp")
        outer = outerblock_factory(listitem=listitem_factory(experiment=exp))
        # Trial saved before its AG in pk order, so a naive loop would miss the map
        trial = trialitem_factory(blockitem=blockitem_factory(outerblock=outer))
        ag = trialitem_factory(
            blockitem=blockitem_factory(outerblock=outer, label="AGs", position=2),
            label="AG",
            code="AG",
        )
        ag.is_attention_getter = True
        ag.save()
        trial.attention_getter, trial.min_dwell_time = ag, 500
        trial.save()

        import_from_zip(mock_request, export_to_zip(exp.pk))

        copy = TrialItem.objects.get(
            blockitem__outerblockitem__listitem__experiment__exp_name="AGExp copy",
            label=trial.label,
        )
        assert copy.attention_getter.label == "AG"
        assert copy.attention_getter.pk != ag.pk
        assert (
            copy.attention_getter.blockitem.outerblockitem.listitem.experiment.exp_name
            == "AGExp copy"
        )
```

(Add `TrialItem` to the `experiments.models` import in that file if missing.)

- [ ] **Step 2: Run test to verify it fails**

Run: `docker compose -f docker-compose.dev.yml exec web uv run pytest /usr/src/tests/test_unit/test_import_export.py -q --no-cov -k attention_getter`
Expected: FAIL — copy points at the source AG (same pk).

- [ ] **Step 3: Implement** — replace the trial loop in `import_from_zip`:

```python
    # Attention getters first, so each trial's attention_getter can be remapped
    # to the already-imported copy as it is saved.
    trials = sorted(
        serializers.deserialize("json", json.dumps(raw["trials"])),
        key=lambda t: not t.object.is_attention_getter,
    )
    trial_pk_map: dict[Any, Any] = {}
    for trial in trials:
        old_pk = trial.object.pk
        trial.object.id = None
        _remap_fk(trial.object, "blockitem", block_pk_map)
        _remap_fk(trial.object, "attention_getter", trial_pk_map)
        for field_name in _TRIAL_FILE_FIELDS:
            _remap_fk(trial.object, field_name, media_pk_map)
        trial.save()
        trial_pk_map[old_pk] = trial.object.pk
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `docker compose -f docker-compose.dev.yml exec web uv run pytest /usr/src/tests/test_unit/test_import_export.py /usr/src/tests/test_integration/test_import_export.py -q --no-cov`
Expected: PASS

- [ ] **Step 5: Ask the user, then commit**

```bash
git add src/experiments/import_export.py tests/test_unit/test_import_export.py
git commit -m "Remap attention getter references when importing experiments" -m "- Without this, imported trials kept pointing at the source experiment's attention getter"
```

---

### Task 5: Reporter — attention getter numbering + `Dwell (ms)` column

**Files:**
- Modify: `src/experiments/reporter.py` (`trial_columns`, `_get_trial_results`, `create_trial_worksheet`, new `calc_dwell`)
- Test: `tests/test_unit/test_reporter.py`

**Interfaces:**
- Consumes: `parse_samples`, `dwell_time` (Task 1); `TrialItem.dwell_target` (Task 2).
- Produces: `Reporter.calc_dwell(result) -> int | str` (`""` when not applicable); `"Dwell (ms)"` appended as the **last** trial column.

- [ ] **Step 1: Write the failing tests** — append to `tests/test_unit/test_reporter.py` (it already has `reporter`, `make_reporter`, `SimpleNamespace`):

```python
# ---------------------------------------------------------------------------
# calc_dwell / attention getter numbering
# ---------------------------------------------------------------------------


def _dwell_result(recording="EYE", record_gaze=True, is_calibration=False, key=""):
    samples = [{"x": 10, "y": 10, "t": t} for t in (0, 34, 68)]
    return SimpleNamespace(
        key_pressed=key,
        resolution_w=100,
        resolution_h=100,
        webgazer_data=samples,
        trialitem=SimpleNamespace(
            record_gaze=record_gaze,
            is_calibration=is_calibration,
            grid_row=1,
            grid_col=1,
            dwell_target=None,
            blockitem=SimpleNamespace(
                outerblockitem=SimpleNamespace(
                    listitem=SimpleNamespace(
                        experiment=SimpleNamespace(recording_option=recording)
                    )
                )
            ),
        ),
    )


@pytest.mark.parametrize(
    "kwargs,expected",
    [
        ({}, 68),
        ({"recording": "ALL"}, 68),
        ({"recording": "VID"}, ""),
        ({"record_gaze": False}, ""),
        ({"is_calibration": True}, ""),
        ({"key": "PAUSE"}, ""),
    ],
)
def test_calc_dwell(reporter, kwargs, expected):
    """Dwell is reported for gaze-recorded, non-calibration, non-pause rows only."""
    assert reporter.calc_dwell(_dwell_result(**kwargs)) == expected


def test_dwell_column_is_last(reporter):
    """The new column is appended so existing column positions are unchanged."""
    assert reporter.trial_columns[-1] == "Dwell (ms)"


@pytest.mark.django_db
def test_attention_getter_rows_keep_trial_numbers_unique(
    monkeypatch,
    tmp_path,
    subjectdata_factory,
    blockitem_factory,
    trialitem_factory,
):
    """An AG row sharing its trigger's number doesn't force ordinal numbering."""
    trial = trialitem_factory(label="T1")
    ag = trialitem_factory(
        blockitem=blockitem_factory(
            outerblock=trial.blockitem.outerblockitem, label="AGs", position=2
        ),
        label="AG",
        code="AG",
    )
    ag.is_attention_getter = True
    ag.save()
    listitem = trial.blockitem.outerblockitem.listitem
    sd = subjectdata_factory(experiment=listitem.experiment, listitem=listitem)
    for t in (trial, ag):
        rpt.TrialResult.objects.create(subject=sd, trialitem=t, trial_number=1)

    rep = make_reporter(monkeypatch, tmp_path, listitem.experiment)
    _, unique = rep._get_trial_results(sd)
    assert unique is True
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `docker compose -f docker-compose.dev.yml exec web uv run pytest /usr/src/tests/test_unit/test_reporter.py -q --no-cov`
Expected: new tests FAIL (`calc_dwell` missing, column missing, `unique` False).

- [ ] **Step 3: Implement** in `src/experiments/reporter.py`. Import `from .gaze import dwell_time, parse_samples, roi_cell`. Append `"Dwell (ms)",` after `"Record Gaze",` in `trial_columns`. In `_get_trial_results` replace the `trial_numbers` line:

```python
        # Attention getter rows share their trigger's number by design
        trial_numbers = qs.exclude(trialitem__is_attention_getter=True).values_list(
            "trial_number", flat=True
        )
```

Add after `calc_roi_response`:

```python
    def calc_dwell(self, result):
        """Return gaze dwell (ms) in the trial's target, or "" if not recorded."""
        trial = result.trialitem
        recording = trial.blockitem.outerblockitem.listitem.experiment.recording_option
        if (
            recording not in ("EYE", "ALL")
            or not trial.record_gaze
            or trial.is_calibration
            or result.key_pressed == "PAUSE"
        ):
            return ""
        return round(
            dwell_time(
                parse_samples(result.webgazer_data),
                result.resolution_w,
                result.resolution_h,
                trial.grid_row,
                trial.grid_col,
                trial.dwell_target,
            )
        )
```

In `create_trial_worksheet`, append `self.calc_dwell(result),` as the last element of the row list (after the "Record Gaze" expression).

- [ ] **Step 4: Run tests to verify they pass**

Run: `docker compose -f docker-compose.dev.yml exec web uv run pytest /usr/src/tests/test_unit/test_reporter.py /usr/src/tests/test_integration -q --no-cov`
Expected: PASS (fix any existing test that asserts the exact trial column count by adding the new column).

- [ ] **Step 5: Ask the user, then commit**

```bash
git add src/experiments/reporter.py tests/test_unit/test_reporter.py
git commit -m "Report dwell time and keep attention getter rows numbered" -m "- Dwell (ms) gives researchers a per-trial looking-time summary and shows why an attention getter fired
- Attention getter rows share their trigger's trial number, so they no longer force the ordinal-numbering fallback"
```

---

### Task 6: Admin — fieldsets, scoped attention getter choices, formset validation, toggle JS

**Files:**
- Modify: `src/experiments/admin.py:166-199` (`TrialItemInline`); imports
- Create: `src/experiments/static/experiments/js/admin/attention-getter-toggle.js`
- Test: `tests/test_unit/test_admin.py`, `tests/js/attention-getter-toggle.test.js` (new)

**Interfaces:**
- Consumes: Task 2 fields.
- Produces: `TrialItemInline.formset = TrialItemInlineFormSet`; dwell fieldset carries CSS class `dwell-check`; JS module exports `init()` and `sync(checkbox: HTMLInputElement)`.

- [ ] **Step 1: Check the Grappelli inline markup** the JS relies on:

Run: `docker compose -f docker-compose.dev.yml exec web sh -c 'grep -n "grp-dynamic-form\|fieldset" $(uv run python -c "import grappelli,os;print(os.path.dirname(grappelli.__file__))")/templates/admin/edit_inline/stacked.html $(uv run python -c "import grappelli,os;print(os.path.dirname(grappelli.__file__))")/templates/admin/includes/fieldset.html'`
Expected: each inline form is wrapped in an element with class `grp-dynamic-form`, and fieldset `classes` are rendered on the `<fieldset>` element. If the wrapper class differs, use the actual class in `sync()` below and in the Vitest DOM.

- [ ] **Step 2: Write the failing Python tests** — append to `tests/test_unit/test_admin.py` (add imports `from types import SimpleNamespace`, `from experiments.admin import TrialItemInline`, and `BlockItem`, `TrialItem` from models if missing):

```python
# ---------------------------------------------------------------------------
# TrialItemInline — attention getter scoping and formset validation
# ---------------------------------------------------------------------------


@pytest.fixture
def ag_block_setup(trialitem_factory, blockitem_factory, filer_file_factory):
    """Block with trial T1 plus AG (own block, same list) and AG2 (other list)."""
    visual = filer_file_factory("pic.png")
    trial = trialitem_factory(label="T1")
    ag = trialitem_factory(
        blockitem=blockitem_factory(
            outerblock=trial.blockitem.outerblockitem, label="AGs", position=2
        ),
        label="AG",
        code="AG",
    )
    other_ag = trialitem_factory(label="AG2", code="AG2")  # different experiment
    for t in (trial, ag, other_ag):
        t.visual_file = visual
    for t in (ag, other_ag):
        t.is_attention_getter = True
    for t in (trial, ag, other_ag):
        t.save()
    return trial, ag, other_ag


def _inline_request(rf, user, block):
    request = rf.get("/")
    request.user = user
    request.resolver_match = SimpleNamespace(kwargs={"object_id": str(block.pk)})
    return request


@pytest.mark.django_db
def test_attention_getter_choices_limited_to_same_list(
    admin_site, rf, user, ag_block_setup
):
    """Only flagged trials from the block's own list are offered."""
    trial, ag, other_ag = ag_block_setup
    inline = TrialItemInline(BlockItem, admin_site)
    field = inline.formfield_for_foreignkey(
        TrialItem._meta.get_field("attention_getter"),
        _inline_request(rf, user, trial.blockitem),
    )
    assert list(field.queryset) == [ag]


def _formset_data(trials, overrides):
    """POST data for the trial inline formset; overrides: {pk: {field: value|None}}."""
    prefix = "trialitem_set"
    data = {
        f"{prefix}-TOTAL_FORMS": str(len(trials)),
        f"{prefix}-INITIAL_FORMS": str(len(trials)),
        f"{prefix}-MIN_NUM_FORMS": "0",
        f"{prefix}-MAX_NUM_FORMS": "1000",
    }
    for i, t in enumerate(trials):
        values = {
            "id": t.pk,
            "blockitem": t.blockitem_id,
            "label": t.label,
            "code": t.code,
            "visual_onset": 0,
            "visual_file": t.visual_file_id,
            "audio_onset": 0,
            "user_input": "NO",
            "max_duration": 1000,
            "record_media": "on",
            "record_gaze": "on",
            "calibration_points": json.dumps(t.calibration_points),
            "grid_row": 1,
            "grid_col": 1,
            "position": t.position,
            "dwell_target_type": "ANY",
        }
        if t.is_attention_getter:
            values["is_attention_getter"] = "on"
        values.update(overrides.get(t.pk, {}))
        data.update(
            {f"{prefix}-{i}-{k}": v for k, v in values.items() if v is not None}
        )
    return data


@pytest.mark.django_db
def test_formset_rejects_pointing_at_attention_getter_unflagged_in_same_save(
    admin_site, rf, user, ag_block_setup
):
    """Unflagging AG and pointing T1 at it in one save is caught by the formset."""
    trial, ag, _ = ag_block_setup
    ag.blockitem = trial.blockitem  # same block → same formset
    ag.position = 2
    ag.save()
    inline = TrialItemInline(BlockItem, admin_site)
    request = _inline_request(rf, user, trial.blockitem)
    FormSet = inline.get_formset(request, trial.blockitem)
    data = _formset_data(
        [trial, ag],
        {
            trial.pk: {"attention_getter": ag.pk, "min_dwell_time": 500},
            ag.pk: {"is_attention_getter": None},
        },
    )
    formset = FormSet(data, instance=trial.blockitem, prefix="trialitem_set")
    assert not formset.is_valid()
    assert "being unmarked" in str(formset.errors)


@pytest.mark.django_db
def test_formset_accepts_valid_dwell_check(admin_site, rf, user, ag_block_setup):
    """A valid dwell-check configuration saves through the inline formset."""
    trial, ag, _ = ag_block_setup
    inline = TrialItemInline(BlockItem, admin_site)
    request = _inline_request(rf, user, trial.blockitem)
    FormSet = inline.get_formset(request, trial.blockitem)
    data = _formset_data(
        [trial], {trial.pk: {"attention_getter": ag.pk, "min_dwell_time": 500}}
    )
    formset = FormSet(data, instance=trial.blockitem, prefix="trialitem_set")
    assert formset.is_valid(), formset.errors
    formset.save()
    trial.refresh_from_db()
    assert trial.attention_getter == ag
```

(If a form error names a required field missing from `_formset_data`, add that field to `values` with its default — the helper must mirror every editable field of the inline.)

- [ ] **Step 3: Write the failing Vitest test** — create `tests/js/attention-getter-toggle.test.js`:

```js
import { beforeEach, describe, expect, it } from 'vitest'
import { init, sync } from '../../src/experiments/static/experiments/js/admin/attention-getter-toggle.js'

const inline = (i, flagged) => `
  <div class="grp-dynamic-form" id="trialitem_set${i}">
    <input type="checkbox" name="trialitem_set-${i}-is_attention_getter" ${flagged ? 'checked' : ''}>
    <fieldset class="grp-module dwell-check">
      <input name="trialitem_set-${i}-min_dwell_time" value="500">
      <select name="trialitem_set-${i}-dwell_target_type">
        <option value="ANY">Any</option><option value="CELL" selected>Cell</option>
      </select>
      <input name="trialitem_set-${i}-dwell_target_row" value="1">
      <select name="trialitem_set-${i}-attention_getter">
        <option value="">---</option><option value="7" selected>AG</option>
      </select>
    </fieldset>
  </div>`

const fieldset = i => document.querySelector(`#trialitem_set${i} fieldset.dwell-check`)
const field = (i, name) => document.querySelector(`[name="trialitem_set-${i}-${name}"]`)

describe('attention-getter-toggle.js', () => {
  beforeEach(() => { document.body.innerHTML = inline(0, false) + inline(1, true) })

  it('hides the dwell fieldset of already-flagged trials on init', () => {
    init()
    expect(fieldset(0).style.display).toBe('')
    expect(fieldset(1).style.display).toBe('none')
  })

  it('hides and clears the fieldset when a trial is flagged', () => {
    init()
    const box = field(0, 'is_attention_getter')
    box.checked = true
    box.dispatchEvent(new Event('change', { bubbles: true }))
    expect(fieldset(0).style.display).toBe('none')
    expect(field(0, 'min_dwell_time').value).toBe('')
    expect(field(0, 'dwell_target_type').value).toBe('ANY')
    expect(field(0, 'dwell_target_row').value).toBe('')
    expect(field(0, 'attention_getter').value).toBe('')
  })

  it('shows the fieldset again when unflagged', () => {
    const box = field(1, 'is_attention_getter')
    box.checked = false
    sync(box)
    expect(fieldset(1).style.display).toBe('')
  })

  it('handles inline rows added after init', () => {
    init()
    document.body.insertAdjacentHTML('beforeend', inline(2, false))
    const box = field(2, 'is_attention_getter')
    box.checked = true
    box.dispatchEvent(new Event('change', { bubbles: true }))
    expect(fieldset(2).style.display).toBe('none')
  })
})
```

- [ ] **Step 4: Run tests to verify they fail**

Run: `docker compose -f docker-compose.dev.yml exec web uv run pytest /usr/src/tests/test_unit/test_admin.py -q --no-cov` → new tests FAIL
Run: `cd tests && npm run test:unit` → toggle test FAILS (module not found)

- [ ] **Step 5: Implement the JS** — create `src/experiments/static/experiments/js/admin/attention-getter-toggle.js`:

```js
/**
 * Hide (and clear) a trial inline's dwell-check fieldset while the trial is
 * marked as an attention getter, since attention getters cannot have one.
 * Server-side validation remains the real guard.
 */
const FLAG_SELECTOR = 'input[type="checkbox"][name$="-is_attention_getter"]';

/**
 * Show or hide the dwell fieldset belonging to one flag checkbox.
 * @param {HTMLInputElement} checkbox
 */
export function sync(checkbox) {
    const fieldset = checkbox.closest('.grp-dynamic-form')?.querySelector('fieldset.dwell-check');
    if (!fieldset) return;
    fieldset.style.display = checkbox.checked ? 'none' : '';
    if (!checkbox.checked) return;
    fieldset.querySelectorAll('input, select').forEach(el => {
        el.value = el.name.endsWith('-dwell_target_type') ? 'ANY' : '';
    });
}

export function init() {
    document.querySelectorAll(FLAG_SELECTOR).forEach(sync);
    // Delegated, so inline rows added later ("Add another Trial") are covered
    document.addEventListener('change', event => {
        if (event.target.matches?.(FLAG_SELECTOR)) sync(event.target);
    });
}

document.addEventListener('DOMContentLoaded', init);
```

- [ ] **Step 6: Implement the admin** in `src/experiments/admin.py`. Add imports `from django.forms import BaseInlineFormSet, Script` (Django ≥5.2 provides `Script`) and ensure `BlockItem`, `TrialItem` are imported from `.models`. Add above `TrialItemInline`:

```python
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
            and (f.cleaned_data.get("DELETE") or not f.cleaned_data["is_attention_getter"])
        }
        for form in live:
            ag = form.cleaned_data.get("attention_getter")
            if ag is not None and not form.cleaned_data.get("DELETE") and ag.pk in removed:
                form.add_error(
                    "attention_getter",
                    f"'{ag.label}' is being unmarked as an attention getter or deleted"
                    " in this save.",
                )
```

Replace `TrialItemInline`'s `fieldsets` and add `formset`, `Media` and `formfield_for_foreignkey`:

```python
    formset = TrialItemInlineFormSet
    fieldsets = (
        (None, {"fields": ("label", "code", "position", "is_attention_getter")}),
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
            "Eye-tracking calibration",
            {
                "classes": ("grp-collapse", "grp-closed"),
                "fields": ("is_calibration", "calibration_points"),
            },
        ),
        (
            "Grid",
            {
                "fields": (("grid_row", "grid_col"),),
                "description": f'<div class="help">{GRID_LAYOUT_HELP_TEXT}</div>',
            },
        ),
        (
            "Dwell check → attention getter (optional)",
            {
                "classes": ("grp-collapse", "grp-closed", "dwell-check"),
                "fields": (
                    "min_dwell_time",
                    "dwell_target_type",
                    ("dwell_target_row", "dwell_target_col"),
                    "attention_getter",
                ),
                "description": (
                    '<div class="help">If gaze dwell in the target is below the'
                    " minimum, the attention getter is shown before the next trial."
                    " Requires eye-tracking.</div>"
                ),
            },
        ),
    )

    class Media:
        """Hide the dwell fieldset for attention getters."""

        js = (Script("experiments/js/admin/attention-getter-toggle.js", type="module"),)

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
                is_attention_getter=True,
                blockitem__outerblockitem__listitem=listitem_id,
            ).select_related("blockitem")
        field = super().formfield_for_foreignkey(db_field, request, **kwargs)
        if db_field.name == "attention_getter":
            field.label_from_instance = lambda t: f"{t.label} ({t.blockitem.label})"
        return field
```

- [ ] **Step 7: Run tests to verify they pass**

Run: `docker compose -f docker-compose.dev.yml exec web uv run pytest /usr/src/tests/test_unit/test_admin.py -q --no-cov` → PASS
Run: `cd tests && npm run test:unit` → PASS

- [ ] **Step 8: Manual smoke check** — open `http://localhost:8080/admin/`, edit any inner block: fieldsets render as sections; ticking "use as attention getter" hides the dwell section; deleting an attention getter still referenced shows Django's "would require deleting protected related objects" error. Report what you saw.

- [ ] **Step 9: Ask the user, then commit**

```bash
git add src/experiments/admin.py src/experiments/static/experiments/js/admin/attention-getter-toggle.js tests/test_unit/test_admin.py tests/js/attention-getter-toggle.test.js
git commit -m "Organise trial admin into sections and add attention getter controls" -m "- Dwell check fields sit in an optional collapsed section so the extra customisation doesn't clutter the common case
- Attention getter choices are limited to the same list, and the formset catches unflag-and-reference in a single save
- Small JS toggle hides the dwell section for attention getters; server validation stays the real guard"
```

---

### Task 7: Read-only Mermaid flowchart on the list admin page

**Files:**
- Create: `src/experiments/flowchart.py`
- Create: `src/experiments/templates/admin/experiments/listitem/change_form.html`
- Modify: `src/experiments/admin.py:515-532` (`ListItemAdmin.change_view`)
- Test: `tests/test_unit/test_flowchart.py` (new), `tests/test_unit/test_admin.py`

**Interfaces:**
- Consumes: Task 2 fields.
- Produces: `list_flowchart(list_item: ListItem) -> str`; template context key `flowchart`.

- [ ] **Step 1: Write the failing tests** — create `tests/test_unit/test_flowchart.py`:

```python
"""Unit tests for experiments/flowchart.py."""

import pytest

from experiments.flowchart import list_flowchart


@pytest.fixture
def structure(listitem_factory, outerblock_factory, blockitem_factory, trialitem_factory):
    """List → Outer → Block(T1, T2) + Block 'AGs'(AG); T1 → AG when dwell < 500."""
    listitem = listitem_factory()
    outer = outerblock_factory(listitem=listitem, outer_block_name="Fam")
    block = blockitem_factory(outerblock=outer, label="Main")
    t1 = trialitem_factory(blockitem=block, label="T1", position=1)
    t2 = trialitem_factory(blockitem=block, label="T2", code="C2", position=2)
    ag_block = blockitem_factory(outerblock=outer, label="AGs", position=2)
    ag = trialitem_factory(blockitem=ag_block, label="AG", code="AG")
    ag.is_attention_getter = True
    ag.save()
    t1.attention_getter, t1.min_dwell_time = ag, 500
    t1.save()
    return listitem, outer, block, ag_block, t1, t2, ag


@pytest.mark.django_db
def test_flowchart_structure(structure):
    """Subgraphs per block, order edges, and a dashed attention getter edge."""
    listitem, outer, block, ag_block, t1, t2, ag = structure
    src = list_flowchart(listitem)
    assert src.startswith("flowchart TD")
    assert f'subgraph O{outer.pk}["Outer: Fam"]' in src
    assert f'subgraph B{block.pk}["Block: Main"]' in src
    assert f"T{t1.pk} --> T{t2.pk}" in src
    assert f"B{block.pk} --> B{ag_block.pk}" in src
    assert f'T{t1.pk} -.->|"dwell #60; 500 ms"| T{ag.pk}' in src
    assert f'T{ag.pk}(["AG"])' in src
    assert f"class T{ag.pk} ag" in src


@pytest.mark.django_db
def test_flowchart_cell_target_in_edge_label(structure):
    """A CELL target is shown on the edge."""
    listitem, *_, t1, _t2, _ag = structure
    t1.dwell_target_type, t1.dwell_target_row, t1.dwell_target_col = "CELL", 1, 1
    t1.save()
    assert "in cell (1,1)" in list_flowchart(listitem)


@pytest.mark.django_db
def test_flowchart_randomised_block_has_no_order_edges(structure):
    """Randomised trials are labelled and not chained."""
    listitem, _, block, _, t1, t2, _ = structure
    block.randomise_trials = True
    block.save()
    src = list_flowchart(listitem)
    assert "Block: Main (randomised)" in src
    assert f"T{t1.pk} --> T{t2.pk}" not in src


@pytest.mark.django_db
def test_flowchart_escapes_labels(structure):
    """Researcher text can't break Mermaid syntax."""
    listitem, *_, t2, _ = structure
    t2.label = 'a"]; x'
    t2.save()
    src = list_flowchart(listitem)
    assert 'a"]' not in src
    assert "a#34;#93;#59; x" in src


@pytest.mark.django_db
def test_flowchart_empty_list(listitem_factory):
    """A list without blocks renders a placeholder node."""
    assert "No trials yet" in list_flowchart(listitem_factory())
```

And append to `tests/test_unit/test_admin.py`:

```python
@pytest.mark.django_db
def test_listitem_change_view_renders_flowchart(client, listitem_factory):
    """The list change page includes the Mermaid flowchart source."""
    listitem = listitem_factory()
    admin_user = User.objects.create_superuser("flowadmin", "f@x.org", "pw")
    client.force_login(admin_user)
    url = reverse("admin:experiments_listitem_change", args=[listitem.pk])
    response = client.get(url)
    assert response.status_code == 200
    assert b'class="mermaid"' in response.content
    assert b"flowchart TD" in response.content
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `docker compose -f docker-compose.dev.yml exec web uv run pytest /usr/src/tests/test_unit/test_flowchart.py /usr/src/tests/test_unit/test_admin.py -q --no-cov`
Expected: FAIL (`ModuleNotFoundError: experiments.flowchart`; no mermaid block).

- [ ] **Step 3: Implement** — create `src/experiments/flowchart.py`:

```python
"""Read-only Mermaid flowchart of a list's blocks, trials and attention getters."""

import re
from itertools import pairwise

from .models import ListItem, TrialItem

_UNSAFE = re.compile(r"[^\w .,:()'/-]")


def _text(value: str) -> str:
    """Escape text for a quoted Mermaid label using numeric entity codes."""
    return _UNSAFE.sub(lambda m: f"#{ord(m.group())};", value)


def _chain(ids: list[str]) -> list[str]:
    """Return ``a --> b`` edges linking consecutive node ids."""
    return [f"  {a} --> {b}" for a, b in pairwise(ids)]


def _dwell_edge(trial: TrialItem) -> str:
    """Return the dashed edge from a trial to its attention getter."""
    label = f"dwell < {trial.min_dwell_time} ms"
    if trial.dwell_target is not None:
        label += f" in cell ({trial.dwell_target[0]},{trial.dwell_target[1]})"
    return f'  T{trial.pk} -.->|"{_text(label)}"| T{trial.attention_getter_id}'


def list_flowchart(list_item: ListItem) -> str:
    """Return Mermaid source showing a list's structure as configured.

    Outer and inner blocks are nested subgraphs. Solid arrows follow the
    configured order and are omitted where the order is randomised per
    participant. Attention getters are rounded nodes reached by dashed edges
    labelled with the dwell threshold.

    Args:
        list_item (ListItem): The list to draw.

    Returns:
        str: Mermaid ``flowchart`` source.
    """
    lines = ["flowchart TD"]
    edges: list[str] = []
    outer_ids: list[str] = []
    for outer in list_item.outerblockitem_set.order_by("position"):
        outer_ids.append(f"O{outer.pk}")
        suffix = " (randomised blocks)" if outer.randomise_inner_blocks else ""
        lines.append(
            f'  subgraph O{outer.pk}["Outer: {_text(outer.outer_block_name)}{suffix}"]'
        )
        block_ids: list[str] = []
        for block in outer.blockitem_set.order_by("position"):
            block_ids.append(f"B{block.pk}")
            suffix = " (randomised)" if block.randomise_trials else ""
            lines.append(
                f'    subgraph B{block.pk}["Block: {_text(block.label)}{suffix}"]'
            )
            trial_ids: list[str] = []
            for trial in block.trialitem_set.order_by("position"):
                if trial.is_attention_getter:
                    lines.append(f'      T{trial.pk}(["{_text(trial.label)}"])')
                    edges.append(f"  class T{trial.pk} ag")
                    continue
                lines.append(f'      T{trial.pk}["{_text(trial.label)}"]')
                trial_ids.append(f"T{trial.pk}")
                if trial.attention_getter_id:
                    edges.append(_dwell_edge(trial))
            if not block.randomise_trials:
                lines.extend("  " + e for e in _chain(trial_ids))
            lines.append("    end")
        lines.append("  end")
        if not outer.randomise_inner_blocks:
            edges.extend(_chain(block_ids))
    if not outer_ids:
        return 'flowchart TD\n  empty["No trials yet"]'
    edges.extend(_chain(outer_ids))
    lines.extend(edges)
    lines.append("  classDef ag stroke-dasharray: 4 3")
    return "\n".join(lines)
```

- [ ] **Step 4: Pick the Mermaid version and SRI hash**

Run: `npm view mermaid version` (e.g. `11.x.y`), then
`curl -sL https://cdn.jsdelivr.net/npm/mermaid@<version>/dist/mermaid.min.js | openssl dgst -sha384 -binary | openssl base64 -A`
Use both values verbatim in the template below.

- [ ] **Step 5: Create the template** `src/experiments/templates/admin/experiments/listitem/change_form.html` (Django picks it up automatically for `ListItem`):

```django
{% extends "admin/change_form.html" %}

{% block after_field_sets %}
{{ block.super }}
{% if flowchart %}
<fieldset class="grp-module grp-collapse grp-open">
  <h2 class="grp-collapse-handler">Flowchart</h2>
  <div class="grp-row">
    <p class="grp-help">Saved structure only. Dashed arrows lead to attention getters; randomised parts have no order arrows.</p>
    {# Falls back to the raw Mermaid source if the CDN is unreachable #}
    <pre class="mermaid">{{ flowchart }}</pre>
  </div>
</fieldset>
<script src="https://cdn.jsdelivr.net/npm/mermaid@VERSION/dist/mermaid.min.js"
        integrity="sha384-HASH" crossorigin="anonymous"></script>
<script>
  if (window.mermaid) { mermaid.initialize({ startOnLoad: true, securityLevel: "strict" }); }
</script>
{% endif %}
{% endblock %}
```

Replace `VERSION` and `HASH` with the Step 4 values.

- [ ] **Step 6: Wire the admin** — in `ListItemAdmin` (`src/experiments/admin.py`), import `from .flowchart import list_flowchart` and add:

```python
    def change_view(self, request, object_id, form_url="", extra_context=None):
        """Add the list's Mermaid flowchart to the change page."""
        extra_context = extra_context or {}
        obj = self.get_object(request, object_id)
        if obj is not None:
            extra_context["flowchart"] = list_flowchart(obj)
        return super().change_view(request, object_id, form_url, extra_context)
```

- [ ] **Step 7: Run tests to verify they pass**

Run: `docker compose -f docker-compose.dev.yml exec web uv run pytest /usr/src/tests/test_unit/test_flowchart.py /usr/src/tests/test_unit/test_admin.py -q --no-cov` → PASS

- [ ] **Step 8: Manual smoke check** — open a list's admin change page; the diagram renders (subgraphs, arrows, dashed attention getter edge). Report what you saw.

- [ ] **Step 9: Ask the user, then commit**

```bash
git add src/experiments/flowchart.py src/experiments/templates/admin/experiments/listitem/change_form.html src/experiments/admin.py tests/test_unit/test_flowchart.py tests/test_unit/test_admin.py
git commit -m "Show a read-only flowchart of each list in the admin" -m "- Researchers need to see branching structure; this Mermaid view is the interim step before the interactive editor (PR 2b)
- Mermaid is loaded from a pinned jsdelivr URL with an SRI hash; raw source shows if the CDN is unreachable"
```

---

### Task 8: End-to-end — attention getter run + admin toggle

**Files:**
- Modify: `src/experiments/management/commands/create_e2e_fixtures.py`, `delete_e2e_fixtures.py`
- Create: `tests/e2e/specs/attention-getter.spec.js`

**Interfaces:**
- Consumes: everything above. Fixture IDs: experiment `a0e2e000-0000-0000-0000-000000000006`, subject `b0e2e000-0000-0000-0000-000000000006`, trial labels `e2e-ag-trial` / `e2e-ag`.

- [ ] **Step 1: Add the fixture** — in `create_e2e_fixtures.py` add constants below `MODES`:

```python
AG_EXP_ID = "a0e2e000-0000-0000-0000-000000000006"
AG_SUBJECT_ID = "b0e2e000-0000-0000-0000-000000000006"
```

Include `AG_SUBJECT_ID` in the `TrialResult` cleanup at the top of `handle` (`subject_ids = [s for _, s, _ in MODES] + [AG_SUBJECT_ID]`), and before the final `self.stdout.write` add:

```python
        self._create_attention_getter_fixture(user, visual_file)
```

with this method on `Command`:

```python
    def _create_attention_getter_fixture(self, user, visual_file):
        """EYE experiment whose only trial always fails its dwell check.

        The e2e WebGazer stub returns no predictions, so dwell is 0 and the
        attention getter is shown before the thank-you page.
        """
        experiment, _ = Experiment.objects.get_or_create(
            id=AG_EXP_ID,
            defaults={
                "user": user,
                "exp_name": "e2e-attention-getter",
                "recording_option": "EYE",
                "include_pause_page": False,
                "list_selection_strategy": "SEQ",
                "show_gaze_estimations": False,
                "general_onset": 0,
            },
        )
        listitem, _ = ListItem.objects.get_or_create(
            experiment=experiment, list_name="e2e-list"
        )
        outer, _ = OuterBlockItem.objects.get_or_create(
            listitem=listitem, outer_block_name="e2e-outer", defaults={"position": 1}
        )
        main, _ = BlockItem.objects.get_or_create(
            outerblockitem=outer, label="e2e-ag-main", defaults={"position": 1}
        )
        ag_block, _ = BlockItem.objects.get_or_create(
            outerblockitem=outer,
            label="e2e-ag-block",
            defaults={"position": 2, "background_colour": "#000000"},
        )
        common = {
            "visual_file": visual_file,
            "user_input": "NO",
            "max_duration": 500,
            "record_media": False,
            "record_gaze": True,
            "calibration_points": [],
            "position": 1,
        }
        ag, _ = TrialItem.objects.get_or_create(
            blockitem=ag_block,
            label="e2e-ag",
            defaults={**common, "code": "AG", "is_attention_getter": True},
        )
        TrialItem.objects.get_or_create(
            blockitem=main,
            label="e2e-ag-trial",
            defaults={
                **common,
                "code": "T1",
                "attention_getter": ag,
                "min_dwell_time": 1000,
            },
        )
        SubjectData.objects.get_or_create(
            id=AG_SUBJECT_ID,
            defaults={
                "experiment": experiment,
                "listitem": listitem,
                "participant_id": 9100,
            },
        )
```

In `delete_e2e_fixtures.py` append `"a0e2e000-0000-0000-0000-000000000006",` to `EXP_IDS`.

- [ ] **Step 2: Write the e2e spec** — create `tests/e2e/specs/attention-getter.spec.js`:

```js
import { exec } from 'child_process'
import { dirname, resolve } from 'path'
import { promisify } from 'util'
import { fileURLToPath } from 'url'
import { expect, test } from '@playwright/test'
import { stubBrowserAPIs, stubWebgazerScript, proceedPastWebgazerInit } from '../helpers.js'

const execAsync = promisify(exec)
const __dirname = dirname(fileURLToPath(import.meta.url))
const ROOT = resolve(__dirname, '../../..')
const SUBJECT_AG = 'b0e2e000-0000-0000-0000-000000000006'
const EXP_AG = 'a0e2e000-0000-0000-0000-000000000006'

const manage = cmd => execAsync(
  `docker compose -f docker-compose.dev.yml exec -T web uv run python manage.py shell -c "${cmd}"`,
  { cwd: ROOT },
)

test.describe.configure({ mode: 'serial' })

test.describe('attention getter run', () => {
  test.beforeEach(async ({ page }) => {
    await manage(`from experiments.models import TrialResult; TrialResult.objects.filter(subject_id='${SUBJECT_AG}').delete()`)
    await stubWebgazerScript(page)
    await page.addInitScript(stubBrowserAPIs)
  })

  test('shows the attention getter after a failed dwell check, then finishes', async ({ page }) => {
    // The first trial is in the page payload, so the first nexttrial answer
    // is what follows it
    const firstNext = page.waitForResponse(r => r.url().endsWith('/run/nexttrial'))
    await page.goto(`/${SUBJECT_AG}/run`)
    await expect(page.locator('#fullscreen-button')).not.toBeDisabled({ timeout: 5000 })
    await page.locator('#fullscreen-button').click()
    await proceedPastWebgazerInit(page)
    const data = await (await firstNext).json()
    expect(data.trial.label).toBe('e2e-ag')
    await page.waitForURL(`**/${SUBJECT_AG}/run/thankyou`, { timeout: 15000 })
  })
})

test.describe('admin trial inline', () => {
  test('hides the dwell section when a trial is marked as attention getter', async ({ page }) => {
    const { stdout } = await manage(
      `from experiments.models import BlockItem; print(BlockItem.objects.get(label='e2e-ag-main', outerblockitem__listitem__experiment_id='${EXP_AG}').pk)`,
    )
    await page.goto('/admin/login/')
    await page.fill('#id_username', 'e2euser')
    await page.fill('#id_password', 'e2epass')
    await page.locator('input[type="submit"]').click()
    await page.goto(`/admin/experiments/blockitem/${stdout.trim()}/change/`)
    const flag = page.locator('input[name="trialitem_set-0-is_attention_getter"]')
    const section = page.locator('#trialitem_set0 fieldset.dwell-check')
    await expect(section).not.toHaveCSS('display', 'none')
    await flag.check()
    await expect(section).toHaveCSS('display', 'none')
    await flag.uncheck()
    await expect(section).not.toHaveCSS('display', 'none')
  })
})
```

- [ ] **Step 3: Refresh fixtures and run the new spec**

Run: `docker compose -f docker-compose.dev.yml exec web uv run python manage.py create_e2e_fixtures`
Run: `cd tests && npx playwright test --config e2e/playwright.config.js specs/attention-getter.spec.js --project=chromium`
Expected: 2 passed. (If the admin selector `#trialitem_set0` doesn't match, use the wrapper id found in Task 6 Step 1.)

- [ ] **Step 4: Full verification**

Run: `docker compose -f docker-compose.dev.yml exec web uv run pytest -q` → all PASS
Run: `cd tests && npm test` → all PASS (unit + e2e, all browsers)

- [ ] **Step 5: Ask the user, then commit**

```bash
git add src/experiments/management/commands/create_e2e_fixtures.py src/experiments/management/commands/delete_e2e_fixtures.py tests/e2e/specs/attention-getter.spec.js
git commit -m "Add e2e tests for the attention getter flow and admin toggle" -m "- The WebGazer stub returns no predictions, so the fixture trial always fails its dwell check and exercises the full attention getter path"
```

---

## Self-review notes

- Spec coverage: fields/constraints/validation (T2), `gaze.py` + symmetric edges (T1), `nexttrial` + knock-on fixes (T3), import (T4, found during planning), reporter numbering + Dwell column (T5), admin sections/scoping/formset/JS toggle (T6), Mermaid via pinned CDN (T7), Playwright (T8). Skipped per spec: preloading AG video; repeat-after-AG (Stage 3).
- Deviation from spec to confirm: `attention_getter` uses `on_delete=PROTECT` (spec said `SET_NULL`), because `SET_NULL` would leave `min_dwell_time` set without an attention getter and violate the "both or neither" constraint, making the delete fail with a database error instead of a clean message.
