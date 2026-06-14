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

**Verification:** Existing Playwright e2e tests must pass unchanged. Run `npm run test:e2e` and `uv run pytest`.

---

### Stage 2 — Live AOI / Dwell Time + Attention Getter Flow

**Goal:** Move ROI computation from report time to real time in the browser, and support the "launch attention getter if dwell time insufficient" branching rule.

**New TrialItem fields:**
```python
trial_kind = CharField(choices=[('STANDARD', ...), ('REPEATABLE', ...), ('REPEATABLE_LIMITED', ...)], default='STANDARD')
max_attempts = IntegerField(null=True)      # only for REPEATABLE_LIMITED
attention_getter = ForeignKey('TrialItem', null=True, related_name='parent_trials')
min_dwell_time = IntegerField(null=True)   # ms threshold; if AOI dwell < this → show attention_getter
# Configurable AOI target for dwell check:
dwell_target_type = CharField(choices=[('ANY', 'Anywhere on screen'), ('SPECIFIC_CELL', 'Specific grid cell')], null=True)
dwell_target_row = IntegerField(null=True)  # grid row; only used when dwell_target_type='SPECIFIC_CELL'
dwell_target_col = IntegerField(null=True)  # grid col; only used when dwell_target_type='SPECIFIC_CELL'
```

**Live AOI in JS (`webgazer-calibration.js`):**
- Extract `calc_roi_response()` logic from `reporter.py` → port to JS as `getGazeROI(x, y, gridRow, gridCol, resW, resH)`
- Accumulate per-cell dwell time during gaze recording
- At trial end, attach `{roi_summary: {(row,col): dwell_ms, ...}}` to the `postResult()` payload

**Backend — `nexttrial` logic:**
- If the posted result includes `roi_summary` and the trial has `min_dwell_time`, check dwell in expected AOI
- If insufficient → return the `attention_getter` trial (REPEATABLE, so not counted as a unique trial)
- Track attention getter cycles in a new `SessionState` model (or Django session dict) to avoid infinite loops

**Admin UI:** Add the new fields as an inline fieldset on `TrialItemInline` in `admin.py`. FK dropdowns for `attention_getter` scoped to the same `BlockItem`.

**Verification:** Write a pytest test that simulates low-dwell-time posting and confirms the attention getter trial is returned. Add a Playwright test for the attention getter loop.

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

1. **AOI target (Stage 2):** Flexible per trial — `dwell_target_type` field (ANY / SPECIFIC_CELL) with `dwell_target_row/col`.
2. **Repeat position (Stage 3):** Configurable per branch rule — `repeat_mode` field (IMMEDIATE / ENQUEUE).
3. **Stage 5 priority:** Needed soon — included in near-term plan alongside Stage 4.
4. **Branching UI:** Visual flowchart required from day one. Mermaid read-only diagram ships with PR 2a; interactive Reactflow editor ships with PR 2b.

## Remaining Open Questions (resolve before each stage)

- **Stage 4 — habituation window reference:** Is the reference dwell always "first N trials" or can the researcher pick any N consecutive trials not including the current one? Can the window span blocks?
- **Stage 4 — condition evaluation timing:** For block-level conditions, is the condition checked after every trial, or only at the last trial of the block?
- **Stage 6 — urgency:** Is text stimuli blocking any active experiment designs, or can it wait until after Stage 3?

---

## Suggested PR Sequence

| PR | Stage | Est. scope |
|----|-------|-----------|
| PR 1 | Stage 1: Dynamic trial fetching (`nexttrial` API) | Medium — pure refactor, no new features |
| PR 2a | Stage 2: Live AOI in JS + attention getter fields + Mermaid read-only flowchart | Large |
| PR 2b | Stage 2: Interactive Reactflow admin editor for trial branching | Large — custom admin view + bundled JS |
| PR 3 | Stage 3: Response-contingent branching (`TrialBranchRule`, feedback audio, `is_success`) | Medium |
| PR 4 | Stage 4: Block-level accumulated conditions (`BlockTransitionRule`, session accumulators) | Large |
| PR 5 | Stage 5: Gaze-triggered stimulus selection (`selectstimulus` endpoint, stimulus pairs) | Large |
| PR 6 | Stage 6: Native text stimuli | Small — new field type, frontend rendering |

**Minimum viable set for most common research designs:** PR 1 + PR 2a + PR 3.  
PR 2b (interactive flowchart editor) significantly improves usability but is not required for correct behaviour.  
PR 5 (gaze-triggered) is needed for looking-while-listening and active learning designs.
