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

**Status:** PR 2a implemented in #39 (branch `dwell-time`, rebased onto main 2026-10-19, CI green, draft awaiting review). PR 2b not started. This section describes PR 2a as built; departures from the original design are marked **(changed in PR 2a)**.

**Goal:** Support the "show attention getter if dwell time insufficient" rule. Flow: trial → dwell in target AOI < `min_dwell_time` → attention getter (AG) → **continue** to next trial in sequence (no repeat, so no loops). In the UI and docs this is the **gaze dwell time check**, framed as the trigger for launching the AG rather than a gaze measurement.

**Decision — dwell computed server-side (approach A).** `storeresult` already posts full gaze samples (`webgazer_data`), so `nexttrial` computes dwell in Python from the latest `TrialResult`. No JS port, no `roi_summary` payload. Post-trial decisions (Stages 2–4, incl. habituation) all stay server-side; Stage 5 adds a JS ROI helper for its own mid-trial need. Dropped from original plan as YAGNI: `max_attempts`, `SessionState`.

**Decision — AG is a `TrialItem` with `trial_type = AG`** (not a separate model): AGs get every trial capability (image/video/audio, onsets, recording, future text stimuli/branching) for free. AG trials are skipped by the sequence wherever they live; they can sit in any outer/inner block of the list (AG uses its block's `background_colour`). Placing them in a dedicated block is optional; AG-only blocks contribute no trials to the normal order.

**(changed in PR 2a) `trial_type` replaces boolean flags.** The planned `is_attention_getter` boolean and the existing `is_calibration` were merged into one `trial_type` choice field: `REG` "Regular" (default), `CAL` "Eye-tracking calibration", `AG` "Attention getter". Read-only `is_calibration`/`is_attention_getter` properties keep existing readers working; code uses the `TrialItem` constants, not literals. Experiment import maps the old boolean keys onto `trial_type`. Migration 0020 was edited in place with no data step, since there is no production data before v2.0.0 (the test server will be reset).

**TrialItem fields (migration 0020):**
```python
trial_type = CharField(choices=TRIAL_TYPE_OPTIONS, default=REGULAR)  # replaces is_calibration
attention_getter = ForeignKey("self", null=True, blank=True, on_delete=RESTRICT,  # SET_NULL would violate the both-or-neither constraint; RESTRICT (unlike PROTECT) still lets a cascade delete the trigger and its AG together, while deleting a still-referenced AG alone is refused
                              related_name="triggering_trials",
                              limit_choices_to={"trial_type": ATTENTION_GETTER})
min_dwell_time = PositiveIntegerField("minimum dwell time (ms)", null=True, blank=True)
dwell_target_type = CharField(choices=[("ANY", "Anywhere on screen"), ("CELL", "Specific grid cell")], default="ANY")
dwell_target_row = PositiveSmallIntegerField(null=True, blank=True)  # 1-based, matches report "(row,col)"
dwell_target_col = PositiveSmallIntegerField(null=True, blank=True)
# existing grid_row/grid_col → PositiveSmallIntegerField + MinValueValidator(1)
```

**Validation (layered):**
- DB `CheckConstraint`s (same-row; also guard import/shell): only regular trials may have `attention_getter`/`min_dwell_time`; `attention_getter` and `min_dwell_time` set together; grid/dwell row/col ≥ 1.
- `limit_choices_to` + formfield narrowed to AG trials in the same ListItem. Dropdown labels show the location, `<label> — <outer block> › <block>`.
- `TrialItem.clean()` (cross-row): AG in same ListItem (defence in depth; moving a block to another list can still split an AG from its triggers, accepted as rare and harmless at runtime); can't change the type of an AG that is still referenced; `CELL` needs row/col within grid and is rejected on a 1×1 grid; dwell check needs `record_gaze` **(added in PR 2a)**; `min_dwell_time` ≤ `max_duration` except video trials without user input **(added in PR 2a)**; no dwell check on calibration trials (their `webgazer_data[0]` is validation data).
- `TrialItemForm`: model errors on fields hidden from the form (non-eye experiments) are remapped to non-field errors instead of crashing with a 500; `clean()` clears the dwell fields when `trial_type` is not `REG`, so the JS only shows/hides them and switching type back and forth doesn't lose values.
- Inline formset `clean()`: catches retype-A + point-B-at-A in one save.
- Runtime: `nexttrial` only runs the dwell check for regular trials.

**New module `src/experiments/gaze.py` (pure functions).** Public functions here and in `flowchart.py` get precise type hints and Google-style docstrings (`Args:` with `name (type): ...`, `Returns:`, `Raises:` where relevant). No bare `dict`/`list`/`Any`: `GazeSample = TypedDict("GazeSample", {"x": float, "y": float, "t": float})`, `Cell = tuple[int, int]`, samples as `Sequence[GazeSample]`, dwell target as `Cell | None` (`None` = ANY), `list_flowchart(list_item: ListItem) -> str`.
- `roi_cell(x, y, width, height, rows, cols) -> (row, col)`, 1-based. `Reporter.calc_roi_response` delegates to it. WebGazer clamps off-screen predictions to the screen edge, so a coordinate at `0` **or** at `width`/`height` → `0` on that axis = "off-screen" (symmetric; today only left/top give 0, right/bottom count as the edge cell, and non-divisible sizes can give nonexistent cell `rows+1`/`cols+1`). Only report change: right/bottom edge samples now show 0 instead of the last cell.
- `dwell_time(samples, width, height, rows, cols, target) -> ms`: Σ `min(Δt, 100ms)` over consecutive sample pairs whose first sample is in target (`ANY` = any on-screen cell; off-screen samples never count). Cap stops face-lost gaps counting as looking.

**Backend — `nexttrial`:**
1. `last` = subject's latest non-PAUSE `TrialResult`.
2. If `last.trialitem` has `min_dwell_time`, is a regular trial, `recording_option` ∈ EYE/ALL and `record_gaze` → if `dwell_time(...) < min_dwell_time`, return AG dict (AG's own block for background, `trial_number = last.trial_number`).
3. Else pending sequence as before.
Once AG result is stored, `last` is the AG → sequence continues. Idempotent on refetch; resuming (reloading `/run`) never leads with an AG — it repeats the most recent completed calibration (WebGazer restarts uncalibrated) under the next pending trial's number (so its recording doesn't overwrite the original's) and carries on with that trial; no gaze samples ⇒ dwell 0 ⇒ AG. No AG after the final trial of the experiment (nothing left to regain attention for) — the run finishes; block boundaries still show it.

**Knock-on fixes:**
- `_trial_sequence` skips AG trials, including inside randomised blocks.
- `experiment_end` completeness counts only non-AG trials, and *distinct* completed trial items.
- `experiment_run` `videos` list includes AG video trials (iOS unlock); trial validation and the trial payload share one null-safe video check.
- Reporter: AG row shares triggering trial's number; uniqueness check (ordinal fallback) ignores AG rows.
- Reporter: new "Dwell (ms)" column in Trials sheet for every gaze-recorded non-calibration trial, using the trial's configured target (default `ANY` = on-screen looking time); blank otherwise.
- **(added in PR 2a)** Reporter: "Trial Type" column (display label) right after "Trial Code" in the Trials sheet (shifts later columns by one), and in the EyeTrackingData sheet.
- **(added in PR 2a)** `create_trial_dict` key `trial_type` (video/image) renamed to `stimulus_type` to free the name; JS updated.
- **(added in PR 2a)** Pause rows record the trial on screen when paused (incl. AGs and the first trial): JS tracks `currentTrial` (the last trial shown) and appends `?trialitem=&trial_number=` to both pause redirects. The view validates them and falls back to the first pending trial when missing or out of range. Pause rows share that trial's number, so they no longer force the ordinal fallback.
- **(added in PR 2a)** Experiment import remaps `attention_getter` references to the imported copies.
- **(added in PR 2a)** Turning the recording option from eye-tracking to non-eye-tracking on a saved experiment: browser confirm with counts (shown only if trials are affected), then the server clears dwell checks, resets CAL/AG trials to REG, and reports what changed. Cannot be undone.

**Admin UI (changed in PR 2a):** `TrialItemInline` split into Grappelli fieldsets with no collapsing. The `trial_type` select drives a small admin JS toggle (event delegation; handles Grappelli's late `.grp-dynamic-form` rows): AG hides the "Gaze dwell time and attention getter" section, Eye-tracking calibration shows the calibration section. The eye-tracking sections and `trial_type` only appear when the experiment's recording option includes eye-tracking, with a hint naming where to change it. Server validation remains the real guard.

**Mermaid flowchart (read-only):** Pure function `list_flowchart(list_item) -> str` in new `src/experiments/flowchart.py`, passed via `ListItemAdmin.change_view` `extra_context` to a template override `admin/experiments/listitem/change_form.html`. As built, it is a Grappelli collapsible group (open by default so Mermaid renders at full size) above the inlines, styled with the Grappelli palette (theme `base`, Arial 12px), with a short help paragraph. Outer/inner blocks as nested subgraphs; solid arrows = configured order, omitted when randomised; blocks with only AGs get no order edges; AG nodes distinct shape/class with dashed edges labelled with threshold (+ target cell if `CELL`). Labels escaped. Reflects saved state only. Mermaid loaded from jsdelivr, exact version pinned + SRI hash (no CSP in project); fallback shows raw source in `<pre>` if CDN unreachable.

**Docs:** user guide covers trial types, the gaze dwell time check, attention getters, the recording-option cleanup (`:::{note}`) and the list flowchart; FAQ updated.

**Skipped (add when needed):** preloading AG video (loads on fetch; add if delay noticeable). "Repeat trial after AG" option deferred to Stage 3 (shares repeat semantics with `repeat_mode`).

**Follow-up — unsent media uploads (found testing PR 2a; fixed on branch `interrupted-trials`, before `v2.0.0a4`):** recordings upload as 1 s chunks through a sequential queue, with a merge request queued last; leaving the run page drops whatever is still queued. A *finished* trial then keeps its uploaded chunks on disk, unmerged and unlinked — always a prefix (end cut off; sequential queue means no gaps), and without the merge request there's no reliable completeness signal. Seen in the dev DB: participant 4 (`7740…`) `dwell-look-left` #5, 4 of ~5–6 chunks.
- Only the exit button warns (Quit/Return to study modal). **Leaving fullscreen, the global timeout, closing the tab, crashes and network drops lose uploads silently.** Normal completion waits for the queue.
- **B (built):** `webcam.recover_recordings(subject, min_age)` merges leftover chunks of a result that has no `webcam_file` into `…_partial.webm` (numbered if taken) and attaches it; the `_partial` name is the flag in the admin and the Trials sheet. Chunks are matched on `_trial<n>_<label>_<uuid>` because the run template sets the participant-ID prefix. Runs on resume (`experiment_run`, no age limit) and at report time (`Reporter.create_report`, only chunks untouched for 10 min, so participants still uploading keep their merge request). Each recording is recovered once. Pause rows are skipped (they share the interrupted trial's number and label). Interrupted trials (no result) keep today's behaviour (chunks discarded when the trial restarts).
- **Silent exits (built for fullscreen exit and the global timeout):** `interruptRun` stops the run (the interrupted trial isn't stored or followed by the next trial), abandons its recording without a merge request and drops its queued chunks except the one that may be uploading (`webcam.abandonRecording`), and shows the loading image while waiting up to 30 s for the queue before the pause/thank-you page. Not covered: closing the tab, crashes, network drops — recovery handles those.
- **Uploads giving up (built):** after 10 failed uploads `webcam.js` stops uploading, so the queue never empties and finishing waited forever (already on `main`). Giving up now releases every `waitForQueue` wait, so the participant reaches the thank-you page (debrief, completion code, delete option); the server recovers what was sent.
- **C (later, larger):** keep the unsent queue in IndexedDB across the pause and finish uploading after resuming; only helps participants who resume, in the same browser.

**Verification:** Parametrised pytest for `roi_cell`/`dwell_time`, `list_flowchart`, validation rules (incl. formset retype case), `nexttrial` (low dwell → AG; sufficient dwell / AG / no eye recording / calibration → sequence; AG → continue; no AG after final trial), pause trial recording, completeness count, reporter numbering + dwell/trial-type columns, recording-option cleanup, import remapping; 100% Python coverage. Vitest for pause tracking and the recording-option confirm. Playwright: admin trial-type toggle; attention getter happy path through to thank-you page.

**PR 2a:** merged as #39 (2026-11-07). The unsent uploads fix (PR 2a-fix) lands before `v2.0.0a4` is released (see Release Plan).

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
- Frontend: `showNextTrial()` checks `stimulus_type === 'text'` (renamed from `trial_type` in PR 2a) → renders a styled `<div>` instead of `<img>`/`<video>`
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
5. **Dwell computation (Stage 2):** Server-side from stored `webgazer_data`, not live JS. AG flow is "AG then continue" (no repeat). No AG after the final trial of the experiment.
6. **Trial kinds (Stage 2):** One `trial_type` field (REG / CAL / AG), not per-kind booleans. Later stages that add trial kinds extend its choices.
7. **Migrations before v2.0.0:** No production data, so unreleased migrations can be edited in place and need no data step.
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
- **New JS logic gets Vitest unit tests** where the function is pure or easily isolated (e.g. the Stage 5 JS ROI helper; Stage 2's dwell calculation ended up server-side).
- **New user-facing flows get Playwright e2e tests**: at minimum a happy-path test per PR that runs a minimal experiment through to the thank-you page.
- **Test-driven where practical**: write the pytest/Vitest test first for new backend endpoints and pure JS helpers, then implement.

---

## Suggested PR Sequence

| PR | Stage | Est. scope | Status |
|----|-------|-----------|--------|
| PR 1 | Stage 1: Dynamic trial fetching (`nexttrial` API) | Medium — pure refactor, no new features | Released in `v2.0.0a3` |
| PR 2a | Stage 2: Server-side dwell check + attention getter trial type + Mermaid read-only flowchart | Large | Merged (#39) → `v2.0.0a4` |
| PR 2a-fix | Stage 2 follow-up: recover unsent media uploads, wait for uploads on fullscreen exit / global timeout | Medium | Branch `interrupted-trials`, PR not yet opened → `v2.0.0a4` |
| PR 2b | Stage 2: Interactive Reactflow admin editor for trial branching | Large — custom admin view + bundled JS | Not started |
| PR 3 | Stage 3: Response-contingent branching (`TrialBranchRule`, feedback audio, `is_success`) | Medium | Not started → `v2.0.0a5` |
| PR 4 | Stage 4: Block-level accumulated conditions (`BlockTransitionRule`, session accumulators) | Large | Not started |
| PR 5 | Stage 5: Gaze-triggered stimulus selection (`selectstimulus` endpoint, stimulus pairs) | Large | Not started |
| PR 6 | Stage 6: Native text stimuli | Small — new field type, frontend rendering | Not started |
| PR 7+ | Stage 7: Project-wide type hints + Google-style docstrings (one PR per module) | Medium overall — no behaviour change | Not started |
| Docs | Refresh the Trial admin screenshot (`docs/source/user_guide/experiment-setup.md`, TODO comment) | Small | In `v2.0.0rc1`; retake if PR 5 or 6 changes the trial form |

**Minimum viable set for most common research designs:** PR 1 + PR 2a + PR 3.
PR 2b (interactive flowchart editor) significantly improves usability but is not required for correct behaviour.
PR 5 (gaze-triggered) is needed for looking-while-listening and active learning designs.

## Release Plan

**Decisions (2026-11-01):** 2.0.0 is the MVP (Stages 1–3); PR 2b, 4, 5 and 6 ship as 2.x minor releases. One alpha per merged stage PR. Every tag gets a GitHub Release (pre-release for a/b/rc). Clean migration history at 2.0.0.

**Versioning:** PEP 440 (`2.0.0a4`, `2.0.0b1`, `2.0.0rc1`), git tag `v<version>`. Pushing a `v*` tag publishes the Docker image `ghcr.io/lochhh/e-babylab:<version>` (`publish.yaml`; `{{major}}.{{minor}}` is skipped for pre-releases) and deploys the docs to gh-pages (`docs.yaml`), so the public docs always describe the latest tag, alphas included.

**Roadmap → releases**

| Release | Contents | Gate |
|---|---|---|
| `v2.0.0a3` | PR 1 (#31) dynamic trial fetching, plus #35, #36, #38 | Done 2026-09-27 |
| `v2.0.0a4` | PR 2a (#39): attention getters, gaze dwell time check, trial type, Mermaid flowchart; PR 2a-fix: recovery of unsent media uploads | #39 and PR 2a-fix merged |
| `v2.0.0a5` | PR 3: response-contingent branching, feedback audio, repeat (incl. repeat after AG) | PR 3 merged; MVP feature-complete |
| `v2.0.0b1` | Freeze: no new features or model changes, only fixes and docs | Researchers trial a real MVP design on the test server |
| `v2.0.0rc1` | Migration reset, docs refresh (incl. Trial screenshot), release notes | Beta feedback resolved |
| `v2.0.0` | Stable MVP | rc unchanged after a test-server soak; fresh install + experiment import/export checked |
| `v2.1.0` | PR 2b: interactive Reactflow editor | Merged |
| `v2.2.0` | PR 4: block-level conditions (habituation) | Merged |
| `v2.3.0` | PR 5: gaze-triggered stimulus selection | Merged |
| `v2.4.0` | PR 6: native text stimuli | Merged |
| `2.x.y` | Stage 7 type-hint PRs and bug fixes | Patch releases, or ride along with the next minor |

The order of 2.1–2.4 follows the roadmap and can change by priority (Stage 5 is "needed soon"). Version numbers are assigned when a PR merges, not in advance. A post-2.0 feature that changes the data model heavily may get its own `a`/`rc` pre-releases.

**Migration policy:** v1 used the `ipl` app (migrations 0001–0063); v2 restarted at `src/experiments/migrations/0001`, so v1 → v2 is not a migration upgrade (the README tells v1 users to stay on v1.0.2).
- Within an unmerged PR, edit its own migration in place.
- From `v2.0.0a4` on, merged migrations aren't rewritten; changes go in new migrations. If an alpha still needs a database reset, the release notes say so.
- At rc1, reset the v2 history: delete `0001`–`00NN`, regenerate `0001_initial` with `makemigrations`, and fold the data migrations still needed on a fresh database (e.g. `0005_create_default_filer_folders`, `0006_add_r_script_to_filer_instruments`) into one hand-written `0002` RunPython migration. Delete `tests/test_integration/test_migrations.py` (it tests `0020`'s calibration-flag data step, which the reset removes). Reset the test server. Release notes say alpha/beta databases must be recreated: export experiments from the admin first, then import them.
- From 2.0.0, migrations are append-only.

**Release checklist (every tag)**
1. Main is green (tests and docs build).
2. Bump `pyproject.toml` `version` and run `uv lock`, in a "Release vX" commit on main (skip if the version is already right, as for a4, bumped in #39).
3. Tag `vX` on that commit and push the tag.
4. Create the GitHub Release from the tag (`--prerelease` for a/b/rc). Start from the auto-generated notes and add **Highlights**, **Breaking changes / migration notes**, and **Upgrading** (Docker tag to pull, whether a database reset is needed).
5. Update the Status column in the Suggested PR Sequence table.

**One-off fixes**
- Before a4: replace the hardcoded `release = "v2.0.0"` in `docs/source/conf.py` with the installed package version (`importlib.metadata.version("e-Babylab")`), so the docs show the version they were built from.
- At 2.0.0: point Docker `latest` at the newest stable tag instead of the tip of main (`flavor: latest=auto` in `publish.yaml`), and add an `edge` tag for main, so production users pulling `latest` get a release.
- At 2.0.0: change the README banner from "v2 in development" to stable, and point v1 users at the 2.0.0 install docs.
