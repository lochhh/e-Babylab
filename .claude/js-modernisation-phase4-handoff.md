# JS Modernisation Phase 4 Handoff

## What Phase 4a Completed

| Area | Status |
|---|---|
| Playwright infrastructure | ✅ `tests/e2e/` with 6 browser projects |
| Management commands | ✅ `create_e2e_fixtures` + `delete_e2e_fixtures` |
| NON-mode e2e specs | ✅ browser-check, demographic, webcam-calibration, experiment run, end page |
| CI workflow | ✅ `tests.yaml` — 4 jobs: test-js, test-python (3.13+3.14 matrix), e2e-ubuntu (all 6 browsers) |
| experiment.js unit tests | ✅ 16 tests (up from 3): postResult, trial rendering, webcam recording, global timeout, exit button |
| Docs | ✅ local-development.md updated with e2e section and uv run fixes |

**Total JS test count after 4a:** 63 unit tests across all suites + 55 e2e × 6 browsers

---

## What Phase 4b Completed

| Area | Status |
|---|---|
| e2e spec: AUD mode | ✅ `tests/e2e/specs/experiment-aud.spec.js` |
| e2e spec: VID mode | ✅ `tests/e2e/specs/experiment-vid.spec.js` |
| e2e spec: EYE mode | ✅ `tests/e2e/specs/experiment-eye.spec.js` |
| e2e spec: ALL mode | ✅ `tests/e2e/specs/experiment-all.spec.js` |
| experiment.js unit tests | ✅ 3 new describe blocks: video trial, keypress response, click response |
| iOS autoplay fix | ✅ `playsinline`, `play().catch()`, gesture unlock in fullscreen handler |
| e2e helpers | ✅ `stubWebgazerScript`, `proceedPastWebgazerInit`, MediaRecorder stub, full webgazer chain |

**Total JS test count after 4b:** 66 unit tests + ~126 e2e × 6 browsers

### Non-obvious fixes discovered in 4b

**`webgazer.min.js` overwrites `addInitScript` stubs**
The library ends with `var webgazer; ... webgazer=r.default` — a top-level var assignment that runs after `addInitScript` and replaces our mock. For EYE/ALL tests, `begin()` of the real webgazer never resolves (fake stream has no video frames → face detector hangs). Fix: `page.route('**/webgazer.min.js', ...)` to replace the whole script with the stub before the page loads. Implemented in `stubWebgazerScript(page)` in `helpers.js`.

**`#plotting_canvas` blocks button click after `setup()` runs**
`initWebgazer`'s `setup()` sets `#plotting_canvas` to `position: fixed; display: block; width=innerWidth; height=innerHeight`. Fixed-positioned elements stack above static elements (CSS stacking level 6 > level 3), so the canvas covers `#webgazer-init button`. Playwright's `click()` waits indefinitely → 30s test timeout. Fix: `canvas.style.pointerEvents = 'none'` in `proceedPastWebgazerInit`'s `page.evaluate` block.

**iOS Safari video autoplay (production fix)**
Three-part fix in `experiment.js`:
1. `video.setAttribute('playsinline', '')` — prevents iOS AVPlayer takeover (distinct from document fullscreen)
2. `video.play().catch(err => { if (err.name !== 'NotAllowedError') throw err; ... })` — prevents unhandled rejection from propagating to the error handler and destroying the page
3. Gesture unlock loop in fullscreen handler: `videoEl.play().then(() => videoEl.pause()).catch(() => {})` — establishes gesture credit per video element before the async trial chain begins

## CI Notes

**Workflow file:** `.github/workflows/tests.yaml`

**Jobs:**
- `test-js` — Vitest on ubuntu, no Docker
- `test-python` — native uv + postgres service (no Docker build), Python 3.13 and 3.14 matrix, Codecov upload
- `e2e-ubuntu` — all 6 browser projects including `mobile-safari` (WebKit + iPhone 14 emulation)

**No macOS CI job.** `macos-latest` is now Apple Silicon (M1); colima fails with QEMU and fails again with `--vm-type=vz --vz-rosetta` because Rosetta 2 isn't pre-installed on GitHub runners. `mobile-safari` is WebKit with device emulation — no real macOS hardware needed — so it runs on ubuntu.

**Manual fixture cleanup** (if teardown fails):
```bash
docker compose -f docker-compose.dev.yml exec web uv run python manage.py delete_e2e_fixtures
```

## Key Technical Decisions Made in Phase 4a

**Cross-project TrialResult isolation:** Multiple browser projects share `SUBJECT_NON` UUID. `experimentRun` excludes already-completed trials, causing race conditions. Solved with `test.describe.configure({ mode: 'serial' })` inside each spec + `beforeEach` cleanup via `execAsync` (non-blocking — `execSync` blocks Playwright's WebSocket IPC).

**CSRF cookie for direct navigation:** `@ensure_csrf_cookie` added to `experimentRun` view (`src/experiments/views.py`). Real participants go through form pages; tests navigate directly to `/run`, skipping cookie setup.

**`visual_file` field:** `create_e2e_fixtures.py` uses `FileObject('uploads/e2e-test/placeholder.jpg')` — plain strings cause `AttributeError` from `FileBrowseField`.

**`webcam-calibration.js` optional chaining:** `#webcam_step_1` doesn't exist in the AUD microphone-only template; added `?.classList.remove('active')` at line 68.

**Microtask flushing in unit tests:** Vitest 4.x doesn't have `vi.runAllMicrotasksAsync()`. Use `flush()` helper: `for (let i = 0; i < 15; i++) await Promise.resolve()`. The init chain in experiment.js is ~10 Promise levels deep before/after a fullscreen click.

**Teardown as management command:** `global-teardown.js` calls `delete_e2e_fixtures` management command. Multiline `-c "..."` strings in `execSync` break across shell newlines, causing Django shell to drop to interactive mode — always use single-line `-c` or a management command.

## Phase 4b Scope

### Priority 1: Per-recording-mode e2e tests

The `create_e2e_fixtures` management command already created experiments for AUD/VID/EYE/ALL. Phase 4b adds specs for each mode.

**Fixed UUIDs (from `src/experiments/management/commands/create_e2e_fixtures.py`):**

| Mode | Experiment UUID | Subject UUID |
|---|---|---|
| AUD | `a0e2e000-0000-0000-0000-000000000002` | `b0e2e000-0000-0000-0000-000000000002` |
| VID | `a0e2e000-0000-0000-0000-000000000003` | `b0e2e000-0000-0000-0000-000000000003` |
| EYE | `a0e2e000-0000-0000-0000-000000000004` | `b0e2e000-0000-0000-0000-000000000004` |
| ALL | `a0e2e000-0000-0000-0000-000000000005` | `b0e2e000-0000-0000-0000-000000000005` |

**AUD / VID tests (`tests/e2e/specs/experiment-aud.spec.js`, `experiment-vid.spec.js`):**
- `stubBrowserAPIs` in `tests/e2e/helpers.js` already stubs `getUserMedia` → use it via `page.addInitScript(stubBrowserAPIs)`
- Test webcam calibration page `/{subject}/test` shows recording UI
- Test experiment run: stream initialises → trial completes → `/thankyou` navigation
- `webcam.startRecording` internally calls `MediaRecorder`; stub it via `page.addInitScript` if it throws:
  ```js
  window.MediaRecorder = class {
    constructor() {}
    start() {}
    stop() {}
    addEventListener() {}
  }
  ```

**EYE / ALL tests (`tests/e2e/specs/experiment-eye.spec.js`, `experiment-all.spec.js`):**
- WebGazer already stubbed in `stubBrowserAPIs` (`window.webgazer = { pause, resume, ... }`)
- Test that `initWebgazer` path runs (check no JS errors on page load)
- For calibration trials, set `is_calibration=True` on the fixture's `TrialItem` — currently it's `False` in `create_e2e_fixtures.py:116`
- Note: changing the fixture affects all 5 experiments; create a separate fixture or update EYE/ALL entries specifically

**Suggested new files:**
- `tests/e2e/specs/experiment-aud.spec.js`
- `tests/e2e/specs/experiment-vid.spec.js`
- `tests/e2e/specs/experiment-eye.spec.js`
- `tests/e2e/specs/experiment-all.spec.js`

### Priority 2: Additional unit tests for experiment.js

Remaining untested behaviours (file: `tests/js/experiment.test.js`, function: `init` in `src/experiments/static/experiments/js/experiment.js`):

**Video trial type** — `playTrialVideo` + `setupVideoEnd` (lines 352–376, 565–576):
- jsdom doesn't dispatch `canplay`/`ended` events automatically
- Mock `HTMLVideoElement.prototype.play = vi.fn()` and dispatch events manually:
  ```js
  const video = document.querySelector('video')
  video.dispatchEvent(new Event('canplay'))  // triggers playTrialVideo resolve
  video.dispatchEvent(new Event('ended'))    // triggers setupVideoEnd resolve
  ```

**Keypress response** (`setupKeyPresses`, line 527–558):
- Dispatch `KeyboardEvent` after trial starts:
  ```js
  document.dispatchEvent(new KeyboardEvent('keydown', { which: 65, bubbles: true }))
  ```
- Verify trial ends and `location.replace` is called

**Click response** (`response_keys: ['click']`, lines 544–557):
- Dispatch `MouseEvent` on document:
  ```js
  document.dispatchEvent(new MouseEvent('click', { bubbles: true }))
  ```

## Known Caveats

**Edge browser cache:** `npx playwright install msedge --with-deps` downloads ~200 MB. Add Playwright cache action if CI times become unacceptable.

**`storeresult` POST creates TrialResult rows:** `global-teardown.js` calls `delete_e2e_fixtures`. If teardown fails, rows accumulate. Clean up manually:
```bash
docker compose -f docker-compose.dev.yml exec web uv run python manage.py delete_e2e_fixtures
```

**`webcam-calibration.spec.js` uses AUD subject:** Phase 4a uses `SUBJECT_AUD` (`b0e2e000-...-000000000002`) for the webcam test page. AUD mode subjects are shown the webcam/microphone check page. Verify `views.webcam_test` doesn't redirect them away before adding AUD run tests.
