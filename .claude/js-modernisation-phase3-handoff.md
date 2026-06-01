# JS Modernisation Phase 4 Handoff

## What Phase 3 Completed

All 10 browser-side JS files converted to ES modules. `eval`/`loadScript` test patterns replaced with native `import`. Templates updated. DB migration written.

| File | Change |
|---|---|
| `recaptcha-handler.js` | jQuery removed → native DOM (no exports needed — standalone script) |
| `queue.src.js` | `export { Queue }` |
| `utils.js` | IIFE removed, `export function getCsrfToken` |
| `webcam.js` | Imports Queue + getCsrfToken; exports `webcam` (singleton) + `createWebcam` (factory) |
| `webgazer-calibration.js` | `let clockStart` declared; 8 functions exported; `resetGazeData`/`getGazeData` added; `window.show_gaze_estimations` |
| `experiment.js` | Imports all deps; `window.show_gaze_estimations`; `resetGazeData()`/`getGazeData()`; `export init` |
| `browser-check.js` | `export init`; null guard; `init()` at bottom |
| `endpage.js` | `export init`; null guard; `init()` at bottom |
| `resolution.js` | `export setResolution`; null guards; `setResolution()` at bottom |
| `webcam-calibration.js` | Imports getCsrfToken; `export init`; null guard; `init()` at bottom |

**Templates:**
- `base.html`: removed all global script tags except `bootstrap.min.js`
- `template_defaults.py`: all page-specific scripts use `type="module"`; `resolution.js` moved to demographic page; `webgazer-calibration.js` no longer a standalone tag (imported by experiment.js)
- Migration `0004_update_template_script_tags.py`: updates existing DB Experiment records

**Tests:**
- `load-script.js` helper deleted
- `vitest.config.js`: added `clearMocks: true`
- All test files use `import { ... }` directly — no eval, no loadScript
- **50/50 tests pass**

## Test Count Change

Phase 2 ended at 62 tests. Phase 3 ends at 50.

| Test file | Before | After | Reason |
|---|---|---|---|
| `webcam.test.js` | 9 | 4 | loadScript extracted full webcam object; new tests use `createWebcam` factory with fewer stubbed paths |
| `experiment.test.js` | varies | 3 | eval-based tests were brittle + tightly coupled to internal structure; rewritten with vi.mock pattern |
| others | unchanged | unchanged | |

The 3-test experiment.test.js is the main coverage gap — see Phase 4 scope below.

## Key Design Decisions Made in Phase 3

**`show_gaze_estimations`**: Assigned to `window.show_gaze_estimations` in `experiment.js` (line ~13); read via `window.show_gaze_estimations?.toLowerCase()` in `webgazer-calibration.js` (line ~28). Not imported — stays a window-mediated coupling between the two modules.

**`webgazer`**: Stays as `window.webgazer` (vendored, not importable). `webgazer.min.js` loaded as a plain `<script>` before `experiment.js` module script in the experiment page template.

**`bootstrap`**: Stays as `window.bootstrap` (loaded by base.html).

**`recaptcha-handler.js`**: No exports. It's a standalone side-effectful module — `type="module"` gives it deferred execution and strict mode without needing any exports.

**Auto-init pattern**: Files with DOM side effects export `init()` with a null guard, then call `init()` at module bottom. Browser: deferred by `type="module"`, runs with full DOM. Tests: import triggers early-exit `init()`; test sets up DOM then calls `init()` explicitly.

## Known Caveats Carried Forward

All caveats from Phase 2 handoff still apply. Additionally:

**No bundler.** Modules are served as individual files via Django's static file serving. Each page loads 2–5 module files with relative imports resolved by the browser. Works in all modern browsers (Chrome/Firefox/Safari/Edge since 2018). No tree-shaking or minification beyond the vendored `webgazer.min.js`.

**Import maps not used.** Bare imports like `import { Queue } from './queue.src.js'` use relative paths — no import map needed for current structure.

**`webgazer-calibration.js` module-level side effects**: The file has no top-level side effects beyond variable declarations — safe to import in test context. `initWebgazer` (which calls `webgazer.setGazeListener` etc.) is only called when experiment.js explicitly invokes it.

## Phase 4 Scope

### Priority 1: Playwright e2e tests

Unit tests cannot cover: Django template rendering, CSRF flow, `<script type="module">` loading order, webcam/microphone permission dialogs, WebGazer calibration UI, file upload to the server.

Recommended flows (from Phase 2 handoff):

1. **Browser check page** — MediaRecorder/getUserMedia feature detection UI; browser check should additionally check that the user's browser supports ES2022 features
2. **Demographic form** — resolution inputs populated, reCAPTCHA (can mock), form submission
3. **Webcam calibration** — step 1→2→3 transitions, NON vs VID vs AUD mode, stream error handling
4. **Experiment page** — fullscreen → trials → thankyou redirect (NON recording mode is simplest, but should test all modes if possible; see flowchart in docs/source/user_guide/typical-experiment-run.md)
5. **End page** — approve/disapprove routing

Setup: Playwright runs against `docker compose -f docker-compose.dev.yml up` dev server. Tests live at `tests/e2e/`. Use `page.addInitScript` to stub `navigator.mediaDevices.getUserMedia` so webcam tests don't require real hardware.

### Priority 2: experiment.js unit test coverage

`experiment.js` is 673 lines with 3 unit tests. Key behaviours untested:

- `postResult` — POST to `/result/`, handles `resultId` from response, calls `webcam.startUploading`
- `showNextTrial` — advances trial index, renders stimulus image, calls `startGazeRecording`
- Pause page flow — `data-include-pause-page="true"` inserts pause between trials
- Global timeout — `data-global-timeout` fires `location.replace` after N ms
- CDI trial type — routes to CDI page instead of trial rendering

These are all testable with `vi.mock` + `init()` pattern already established. Use `vi.useFakeTimers()` for timeout tests.

### Priority 3 (optional): Vite bundling

Currently no build step. Advantages of adding Vite:
- Tree-shaking (removes unused exports)
- Single bundled file per page (fewer network requests)
- Source maps for debugging
- Can colocate JS with Django static without changing import paths

Not urgent — file count is small and the app targets research participants on reliable university networks. Revisit if page load performance becomes a concern.
