# Gaze/Response-Contingent Trial Presentation

## Context

e-Babylab currently pre-generates the full ordered trial sequence on the server at experiment start and ships the entire list as JSON to the frontend, which iterates through it sequentially. This makes it impossible to branch based on participant behaviour (gaze, key presses, accumulated performance). The goal is to move to a **per-trial request/response model** where the backend decides the next trial after each response is submitted, enabling gaze-contingent, response-contingent, and habituation-driven experiment designs.

---

## Current Architecture (brief)

- `views.experiment_run()` builds the full trial list → JSON → template context
- `src/static/experiments/js/experiment.js`: `showNextTrial()` iterates `trials[currentTrial++]` locally
- `POST /run/storeresult` saves a `TrialResult` (key_pressed, timings, webgazer_data JSON)
- ROI/dwell computation happens **at report time** in `reporter.py`, not during the experiment
- No branching fields exist on any model today

---

## Proposed Phased Plan

---

### Stage 1 — Dynamic Trial Fetching (prerequisite for all other stages)

**Goal:** Replace the static pre-generated array with a per-trial server-side API. No new experiment behaviour yet — identical to current sequential presentation, but the architecture now supports branching.

**Backend changes:**
- New endpoint `POST /run/nexttrial`: accepts `{subject_uuid, last_trial_result_id}`, returns the next trial dict (same shape as `create_trial_dict()`). Internally reuses the existing sequential logic from `experiment_run()` but evaluates it lazily.
- `GET /run` still renders the page but sends an empty or minimal bootstrap payload (just the first trial) instead of the full list. Subject UUID and config remain in the HTML.
- `store_result()` response extended to include `{resultId, done: bool}` so the frontend knows when the experiment is complete without a separate count.

**Frontend changes (`experiment.js`):**
- After `postResult()` resolves, call `/run/nexttrial` instead of incrementing `currentTrial`.
- Render the returned trial object (same `showNextTrial` rendering code, just driven by server data now).
- Handle `done: true` to trigger the completion flow.

**No model changes** in this stage.

**Verification:** Existing Playwright e2e tests must pass unchanged. Run `cd tests && npm test` and `uv run pytest`.

---

### Stage 2 — Live AOI / Dwell Time + Attention Getter Flow

**Goal:** Support the "show attention getter if dwell time insufficient" rule. Flow: trial → dwell in target AOI < `min_dwell_time` → attention getter (AG) → **continue** to next trial in sequence (no repeat, so no loops).

**Decision — dwell computed server-side (approach A).** `storeresult` already posts full gaze samples (`webgazer_data`), so `nexttrial` computes dwell in Python from the latest `TrialResult`. No JS port, no `roi_summary` payload. Post-trial decisions (Stages 2–4, incl. habituation) all stay server-side; Stage 5 adds a JS ROI helper for its own mid-trial need. Dropped from original plan as YAGNI: `trial_kind`, `max_attempts`, `SessionState`.

**Decision — AG is a flagged `TrialItem`** (not a separate model): AGs get every trial capability (image/video/audio, onsets, recording, future text stimuli/branching) for free. Flagged trials are skipped by the sequence wherever they live; a dedicated "Attention getters" block is recommended practice (AG uses its block's `background_colour`) but mixed blocks are allowed.

**TrialItem fields (one migration):**
```python
is_attention_getter = BooleanField(default=False)
attention_getter = ForeignKey("self", null=True, blank=True, on_delete=SET_NULL,
                              related_name="triggering_trials",
                              limit_choices_to={"is_attention_getter": True})
min_dwell_time = PositiveIntegerField("minimum dwell time (ms)", null=True, blank=True)
dwell_target_type = CharField(choices=[("ANY", "Anywhere on screen"), ("CELL", "Specific grid cell")], default="ANY")
dwell_target_row = PositiveSmallIntegerField(null=True, blank=True)  # 1-based, matches report "(row,col)"
dwell_target_col = PositiveSmallIntegerField(null=True, blank=True)
# existing grid_row/grid_col → PositiveSmallIntegerField + MinValueValidator(1)
```

**Validation (layered):**
- DB `CheckConstraint`s (same-row; also guard import/shell): flagged ⇒ no `attention_getter`/`min_dwell_time`; `attention_getter` and `min_dwell_time` set together; grid/dwell row/col ≥ 1.
- `limit_choices_to` + formfield narrowed to flagged trials in the same ListItem.
- `TrialItem.clean()` (cross-row): AG in same ListItem; can't unflag a trial still referenced; `CELL` needs row/col within grid; no `min_dwell_time` on calibration trials (their `webgazer_data[0]` is validation data).
- Inline formset `clean()`: catches unflag-A + point-B-at-A in one save.
- Runtime: `nexttrial` never runs the dwell check for flagged trials.

**New module `src/experiments/gaze.py` (pure functions).** Public functions here and in `flowchart.py` get precise type hints and Google-style docstrings (`Args:` with `name (type): ...`, `Returns:`, `Raises:` where relevant). No bare `dict`/`list`/`Any`: `GazeSample = TypedDict("GazeSample", {"x": float, "y": float, "t": float})`, `Cell = tuple[int, int]`, samples as `Sequence[GazeSample]`, dwell target as `Cell | None` (`None` = ANY), `list_flowchart(list_item: ListItem) -> str`.
- `roi_cell(x, y, width, height, rows, cols) -> (row, col)`, 1-based. `Reporter.calc_roi_response` delegates to it. WebGazer clamps off-screen predictions to the screen edge, so a coordinate at `0` **or** at `width`/`height` → `0` on that axis = "off-screen" (symmetric; today only left/top give 0, right/bottom count as the edge cell, and non-divisible sizes can give nonexistent cell `rows+1`/`cols+1`). Only report change: right/bottom edge samples now show 0 instead of the last cell.
- `dwell_time(samples, width, height, rows, cols, target) -> ms`: Σ `min(Δt, 100ms)` over consecutive sample pairs whose first sample is in target (`ANY` = any on-screen cell; off-screen samples never count). Cap stops face-lost gaps counting as looking.

**Backend — `nexttrial`:**
1. `last` = subject's latest non-PAUSE `TrialResult`.
2. If `last.trialitem` has `min_dwell_time`, is not flagged/calibration, `recording_option` ∈ EYE/ALL and `record_gaze` → if `dwell_time(...) < min_dwell_time`, return AG dict (AG's own block for background, `trial_number = last.trial_number`).
3. Else pending sequence as before.
Once AG result is stored, `last` is the AG → sequence continues. Idempotent on refetch; pause between trial and AG still shows AG on resume; no gaze samples ⇒ dwell 0 ⇒ AG.

**Knock-on fixes:**
- `_trial_sequence` skips flagged trials.
- `experiment_end` completeness counts only non-flagged trials, and *distinct* completed trial items.
- `experiment_run` `videos` list includes flagged video trials (iOS unlock).
- Reporter: AG row shares triggering trial's number; uniqueness check (ordinal fallback) ignores flagged rows.
- Reporter: new "Dwell (ms)" column in Trials sheet for every gaze-recorded non-calibration trial, using the trial's configured target (default `ANY` = on-screen looking time); blank otherwise.

**Admin UI:** `TrialItemInline` split into Grappelli fieldsets — main (label, code, position, `is_attention_getter`), Stimulus, Response, Recording, Eye-tracking calibration (collapsed), Grid, "Dwell check → attention getter (optional)" (collapsed). Small admin JS hides/clears the dwell fieldset when `is_attention_getter` is ticked (event delegation, works for dynamically added inlines); server validation remains the real guard.

**Mermaid flowchart (read-only):** Pure function `list_flowchart(list_item) -> str` in new `src/experiments/flowchart.py`, passed via `ListItemAdmin.change_view` `extra_context` to a template override `admin/experiments/listitem/change_form.html` (collapsible "Flowchart" panel above the inlines). Outer/inner blocks as nested subgraphs; solid arrows = configured order, randomised blocks labelled "(randomised)"; AG nodes distinct shape/class with dashed edges labelled with threshold (+ target cell if `CELL`). Labels escaped. Reflects saved state only. Mermaid loaded from jsdelivr, exact version pinned + SRI hash (no CSP in project); fallback shows raw source in `<pre>` if CDN unreachable.

**Skipped (add when needed):** preloading AG video (loads on fetch; add if delay noticeable). "Repeat trial after AG" option deferred to Stage 3 (shares repeat semantics with `repeat_mode`).

**Verification:** Parametrised pytest for `roi_cell`/`dwell_time`, `list_flowchart`, validation rules (incl. formset unflag case), `nexttrial` (low dwell → AG; sufficient dwell / flagged / no eye recording / calibration → sequence; AG → continue), completeness count, reporter numbering + dwell column. Playwright: admin fieldset toggle; attention getter happy path through to thank-you page.

**Commit sequence (PR 2a):** plan → `gaze.py` + reporter delegation → model fields/constraints/migration/`clean()` → `nexttrial` dwell check + sequence/end/videos fixes → reporter numbering + dwell column → admin fieldsets/scoping/formset clean/toggle JS → Mermaid flowchart → Playwright e2e.

---

### Stage 3 — Response-Contingent Branching (Feedback + Repeat)

**Goal:** Define success criteria per trial; play conditional audio/show feedback; branch to different next trials based on outcome.

**New model: `TrialBranchRule`** (linked to `TrialItem`):
```python
class TrialBranchRule(models.Model):
    trial = OneToOneField(TrialItem)
    # Success criterion
    success_key = CharField(null=True)           # key press counted as success
    success_aoi_row = IntegerField(null=True)    # grid cell counted as success via gaze
    success_aoi_col = IntegerField(null=True)
    min_success_dwell = IntegerField(null=True)  # ms; required dwell in success AOI
    # Branching targets
    on_success = ForeignKey(TrialItem, null=True, related_name='success_sources')
    on_failure = ForeignKey(TrialItem, null=True, related_name='failure_sources')
    # Repeat behaviour on failure
    repeat_mode = CharField(choices=[('IMMEDIATE', ...), ('ENQUEUE', ...)], null=True)
    # Feedback
    success_audio = FilerFileField(null=True)
    failure_audio = FilerFileField(null=True)
```

**New `TrialResult` field:** `is_success = BooleanField(null=True)` — set by backend when evaluating the branch rule, stored permanently.

**Backend — `nexttrial`:** After storing result, evaluate `TrialBranchRule` → set `is_success`, look up `on_success` or `on_failure` trial FK, return that trial dict (or fall through to sequential if FK is null). Include `feedback_audio` URL in response so frontend plays it before showing next trial.

**Frontend:** If `nexttrial` response includes `feedback_audio`, play it in a small interstitial before calling `showNextTrial()`.

**Repeat semantics (deferred from Stage 2):** Build once here, shared by `repeat_mode` and a new "repeat trial after attention getter" option on `TrialItem` (`after_attention_getter` = CONTINUE/REPEAT, default CONTINUE, + `max_attempts`). Repeat = re-run from start (post-trial check; mid-trial resume would need live JS gaze). Needs:
- Attempt count = number of non-PAUSE `TrialResult`s for that trial item (no `SessionState`).
- **Webcam filename attempt suffix** — `…_trial{n}_{label}_…` is identical on repeat and would overwrite the earlier recording (cf. #38).
- Report "Attempt" column; ordinal-numbering fallback ignores repeats.

**Admin UI:** `TrialBranchRuleInline` inside `TrialItemInline`.

**Verification:** Parametrised pytest tests for all combinations of key/gaze/both success criteria and branch outcomes.

---

### Stage 4 — Block-Level Accumulated Conditions (Habituation + Consecutive Successes)

**Goal:** Transition between outer blocks based on accumulated gaze or success metrics across trials in a block.

**New model: `BlockTransitionRule`** (linked to `OuterBlockItem`):
```python
class BlockTransitionRule(models.Model):
    outer_block = OneToOneField(OuterBlockItem)
    condition_type = CharField(choices=[
        ('DWELL_HABITUATION', ...),   # dwell drops to X% of first-N-trial average
        ('SUCCESS_RATE', ...),        # success rate >= threshold
        ('SUCCESS_COUNT', ...),       # consecutive successes >= threshold
    ])
    window_size = IntegerField(null=True)   # N trials to compute reference dwell
    threshold = FloatField()                # percentage (0–1) or count
    next_outer_block = ForeignKey(OuterBlockItem, null=True)  # jump target; null = end experiment
```

**Session state:** A lightweight JSON blob on `SubjectData` (new field `session_state = JSONField(default=dict)`) tracks per-block accumulators: trial dwell times, success flags.

**Backend — `nexttrial`:** After each trial in a block, evaluate the block's `BlockTransitionRule`. If condition met → set next block pointer, skip remaining trials in current block.

**Admin UI:** `BlockTransitionRuleInline` on `OuterBlockItemInline`.

**Verification:** pytest tests simulating habituation (decreasing dwell) and success-count conditions.

---

### Stage 5 — Gaze-Triggered Stimulus Selection (Looking-While-Listening / Active Learning)

**Goal:** At trial onset, measure where participant is looking → use that to select which audio/stimulus to play (Cases 2 and 3 from the requirements). Needed soon — include in near-term plan.

**Sub-cases:**
- **Case 2 (looking-while-listening):** The object participant is fixating at the moment of audio onset becomes the *distractor*; the other object is the *target*. RT = latency from audio onset until gaze shifts to target.
- **Case 3 (active learning):** Name the object in the grid that participant has looked at most over the preceding X ms window. Optionally, pair that choice with subsequent test trials in a later block.

**New TrialItem fields:**
```python
stimulus_selection = CharField(choices=['FIXED', 'GAZE_TRIGGERED'], default='FIXED')
gaze_window_ms = IntegerField(null=True)   # sampling window before audio onset
stimulus_pairs = JSONField(null=True)      # [{"aoi_row": r, "aoi_col": c, "audio_file_id": id, "visual_file_id": id}, ...]
```

**New endpoint `POST /run/selectstimulus`:**
- Called by frontend after `gaze_window_ms` of sampling, before playing audio
- Receives `{subject_uuid, trial_id, dominant_aoi: [row, col]}`
- Evaluates stimulus pair lookup → returns `{audio_url, visual_url, rt_reference_t}` (the `rt_reference_t` is the server timestamp to align RT measurement)
- For Case 2: `dominant_aoi` = fixation at onset → distractor; the *other* stimulus pair entry = target
- For Case 3: selects the stimulus paired with the most-dwelled AOI; optionally records choice in session state for block-level pairing

**Retention pairing (Case 3 extension):**
- Store chosen `(trial_id, selected_aoi)` in `SubjectData.session_state`
- Block-level rule can use this to populate a test block with the objects the participant was shown during active learning

---

### Stage 6 — Native Text Stimuli

**Goal:** Display text as a visual stimulus without requiring researchers to pre-render images.

**Changes:**
- New `TrialItem` field: `visual_type = CharField(choices=['IMAGE', 'VIDEO', 'TEXT'], default='IMAGE')`, `visual_text = CharField(null=True)`, `visual_text_style = JSONField(null=True)` (font size, colour, position)
- Frontend: `showNextTrial()` checks `trial_type === 'text'` → renders a styled `<div>` instead of `<img>`/`<video>`
- `create_trial_dict()` (or new `nexttrial` endpoint) includes `visual_text` and `visual_text_style`

---

### Stage 7 — Project-Wide Type Hints + Google-Style Docstrings

**Goal:** Bring existing Python code up to the standard set for new modules in Stage 2 (`gaze.py`, `flowchart.py`): precise type hints (no bare `dict`/`list`/`Any`) and Google-style docstrings (`Args:`, `Returns:`, `Raises:`). Independent of Stages 3–6; can run any time.

**Approach:**
- One PR per module (or small group) to keep diffs reviewable: `cdi.py`, `reporter.py`, `views.py`, `models.py`, `admin.py`, `forms.py`, `import_export.py`, `webcam.py`, `captcha.py`, etc.
- Enforce via ruff once coverage is complete: `[tool.ruff.lint.pydocstyle] convention = "google"`, add `ANN` rules (with per-file ignores during rollout).
- Optional: static type checking (`mypy` + `django-stubs`, or `pyright`) in CI after hints land.

**No behaviour changes.** Verification: existing test suites pass; ruff clean.

---

## Branching Rule UI — Flowchart Required from Day One

Researchers confirmed they need a visual flowchart from Stage 2 onward; FK dropdowns alone are not sufficient to reason about branching structures.

**Approach: Custom Django admin view with an interactive flowchart.**

- A new URL under the admin (e.g. `/admin/experiments/listitems/<id>/flowchart/`) renders a flowchart of all trials and their branching connections within a list.
- **Library:** [Reactflow](https://reactflow.dev/) (MIT licence) bundled as a small ES module — the project already uses ES modules. Nodes = `TrialItem`s; edges = `on_success`, `on_failure`, `attention_getter` links; accumulator transitions = edges between `OuterBlockItem` nodes.
- **Editing:** Clicking a node opens the trial's existing Django admin change form in a sidebar/modal. Dragging a new edge between two trial nodes creates or updates a `TrialBranchRule`. The underlying data is still stored in the existing models; the flowchart is a visual layer on top.
- **Read-only fallback:** A simpler option using Mermaid (renders server-side from model data, no edit capability) as an interim milestone inside the existing `ListItem` change view before the full interactive version ships.

**Milestone sequence for UI:**
1. Stage 2, PR 2a: Add Mermaid-rendered flowchart diagram to the `ListItem` admin change view (read-only, auto-generated from trial FK structure). Immediate visual feedback for researchers setting up trials via forms.
2. Stage 2, PR 2b: Interactive Reactflow editor as a dedicated admin view. Drag edges to create/update branch rules; click nodes to edit trial properties.

---

## Build Pipeline

The interactive Reactflow admin editor (PR 2b) uses a **scoped Vite build** in `src/static/admin-flow/` with its own `package.json` and `vite.config.js`. Output is a single `admin-flow.bundle.js` baked into the Docker image at build time via a multi-stage Dockerfile (Node alpine stage → Python stage). End users deploying via Docker never interact with Node. Developers can build via `docker compose run --rm node-builder` without needing Node locally. The existing `experiment.js` ES module files are untouched.

## Resolved Design Decisions

1. **AOI target (Stage 2):** Flexible per trial — `dwell_target_type` field (ANY / CELL) with `dwell_target_row/col`.
5. **Dwell computation (Stage 2):** Server-side from stored `webgazer_data`, not live JS. AG flow is "AG then continue" (no repeat).
2. **Repeat position (Stage 3):** Configurable per branch rule — `repeat_mode` field (IMMEDIATE / ENQUEUE).
3. **Stage 5 priority:** Needed soon — included in near-term plan alongside Stage 4.
4. **Branching UI:** Visual flowchart required from day one. Mermaid read-only diagram ships with PR 2a; interactive Reactflow editor ships with PR 2b.

## Remaining Open Questions (resolve before each stage)

- **Stage 4 — habituation window reference:** Is the reference dwell always "first N trials" or can the researcher pick any N consecutive trials not including the current one? Can the window span blocks?
- **Stage 4 — condition evaluation timing:** For block-level conditions, is the condition checked after every trial, or only at the last trial of the block?
- **Stage 6 — urgency:** Is text stimuli blocking any active experiment designs, or can it wait until after Stage 3?

---

## Testing Requirements (all PRs)

- **Existing tests must continue to pass** after every PR: `uv run pytest` (Python) and `npm test` (Vitest unit + Playwright e2e).
- **Update or delete tests** that break due to intentional behaviour changes (e.g. the trials-data JSON in the template changing shape in PR 1).
- **New backend logic gets pytest coverage**: parametrise over edge cases (no trials remaining, mid-session resume, error paths).
- **New JS logic gets Vitest unit tests** where the function is pure or easily isolated (e.g. the live AOI/dwell calculation in Stage 2).
- **New user-facing flows get Playwright e2e tests**: at minimum a happy-path test per PR that runs a minimal experiment through to the thank-you page.
- **Test-driven where practical**: write the pytest/Vitest test first for new backend endpoints and pure JS helpers, then implement.

---

## Suggested PR Sequence

| PR | Stage | Est. scope |
|----|-------|-----------|
| PR 1 | Stage 1: Dynamic trial fetching (`nexttrial` API) | Medium — pure refactor, no new features |
| PR 2a | Stage 2: Server-side dwell check + attention getter fields + Mermaid read-only flowchart | Large |
| PR 2b | Stage 2: Interactive Reactflow admin editor for trial branching | Large — custom admin view + bundled JS |
| PR 3 | Stage 3: Response-contingent branching (`TrialBranchRule`, feedback audio, `is_success`) | Medium |
| PR 4 | Stage 4: Block-level accumulated conditions (`BlockTransitionRule`, session accumulators) | Large |
| PR 5 | Stage 5: Gaze-triggered stimulus selection (`selectstimulus` endpoint, stimulus pairs) | Large |
| PR 6 | Stage 6: Native text stimuli | Small — new field type, frontend rendering |
| PR 7+ | Stage 7: Project-wide type hints + Google-style docstrings (one PR per module) | Medium overall — no behaviour change |

**Minimum viable set for most common research designs:** PR 1 + PR 2a + PR 3.
PR 2b (interactive flowchart editor) significantly improves usability but is not required for correct behaviour.
PR 5 (gaze-triggered) is needed for looking-while-listening and active learning designs.

## Release Tagging

- Stage 1 shipped and tagged `v2.0.0a3` (#31 dynamic trial fetching, plus #35, #36, #38).
- **Reminder:** `pyproject.toml` `version` is stale (`"2.0.0.a1"`; not bumped for a2 or a3). Bump it to the new version in the commit being tagged *before* creating the next tag (e.g. `2.0.0a4`).
- Stay on alpha (`aN`) while stages can still change behaviour/data model; move to `b1` once 2.0 is feature-complete.
