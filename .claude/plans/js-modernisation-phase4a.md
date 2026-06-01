# JS Modernisation Phase 4a Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** (4a) Playwright infrastructure, NON-mode e2e tests across all browsers + devices, CI workflow, docs update, experiment.js unit tests. (4b, separate plan) Per-recording-mode e2e tests (AUD/VID/EYE/ALL).

**Architecture:** Playwright `tests/e2e/` with 6 browser projects (chromium, firefox, webkit, edge, mobile-chrome, mobile-safari); a Django management command creates 5 deterministic experiments (one per recording mode) so 4b tests can reuse them without re-seeding. Phase 4a only writes NON-mode specs. CI: two GHA jobs — ubuntu (chromium/firefox/webkit/edge/mobile-chrome) and macos (mobile-safari via WebKit). Unit tests extend existing vitest suite in `tests/js/`.

**Tech Stack:** Playwright 1.x, Vitest 4.x, jsdom, vi.useFakeTimers(), Docker Compose, colima (macOS CI only), GitHub Actions, Django management commands

**Phase split:**
- **4a (this plan):** infrastructure + NON-mode e2e + unit tests + CI + docs
- **4b (next plan):** AUD/VID/EYE/ALL mode e2e tests using fixtures created here

---

## File Map

**Created:**
- `tests/package.json` — root test runner: `npm test` runs unit + e2e; `npm run test:unit` / `test:e2e` run each suite alone
- `tests/e2e/package.json`
- `tests/e2e/playwright.config.js`
- `tests/e2e/global-setup.js`
- `tests/e2e/global-teardown.js`
- `src/experiments/management/__init__.py` (if missing)
- `src/experiments/management/commands/__init__.py` (if missing)
- `src/experiments/management/commands/create_e2e_fixtures.py`
- `tests/e2e/specs/browser-check.spec.js`
- `tests/e2e/specs/demographic.spec.js`
- `tests/e2e/specs/webcam-calibration.spec.js`
- `tests/e2e/specs/experiment.spec.js`
- `tests/e2e/specs/endpage.spec.js`
- `.github/workflows/tests.yml`

**Modified:**
- `docs/source/get_started/local-development.md` — add e2e section
- `tests/js/experiment.test.js` — extend makeEnv, add makeTrial, ~12 new tests

---

## Part A — Playwright e2e (Priority 1)

### Task 1: Root test runner

**Files:**
- Create: `tests/package.json`

A single entry point so `npm test` (from `tests/`) runs unit tests then e2e tests in sequence. The e2e suite requires the dev server; unit tests do not. Each can also be run independently.

- [ ] Check whether a `tests/package.json` already exists:

```bash
ls tests/package.json 2>/dev/null || echo "MISSING"
```

- [ ] Create `tests/package.json`

```json
{
  "scripts": {
    "test": "npm run test:unit && npm run test:e2e",
    "test:unit": "npm test --prefix js",
    "test:e2e": "npm test --prefix e2e"
  }
}
```

- [ ] Verify the unit suite still runs via the new entry point (dev server not needed):

```bash
cd tests && npm run test:unit
```

Expected: 50 passed (all existing unit tests).

- [ ] Update the CLAUDE.md `## Tests → JavaScript (Vitest)` section run command to:

```bash
cd tests
npm run test:unit   # unit tests only (no dev server needed)
npm run test:e2e    # e2e tests (dev server must be running)
npm test            # both suites in sequence
```

- [ ] Commit:

```
git add tests/package.json CLAUDE.md
git commit -m "$(cat <<'EOF'
Add tests/package.json unified JS test runner

- npm test runs vitest unit suite then Playwright e2e suite in sequence
- npm run test:unit / test:e2e run each suite independently
- Update CLAUDE.md test commands accordingly
EOF
)"
```

---

### Task 2: Playwright package and config

**Files:**
- Create: `tests/e2e/package.json`
- Create: `tests/e2e/playwright.config.js`

- [ ] Create `tests/e2e/package.json`

```json
{
  "type": "module",
  "scripts": {
    "test": "playwright test",
    "test:headed": "playwright test --headed",
    "test:ui": "playwright test --ui"
  },
  "devDependencies": {
    "@playwright/test": "^1.44.0"
  }
}
```

- [ ] Create `tests/e2e/playwright.config.js`

```js
import { defineConfig, devices } from '@playwright/test'

export default defineConfig({
  testDir: './specs',
  globalSetup: './global-setup.js',
  globalTeardown: './global-teardown.js',
  fullyParallel: true,
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? 'github' : 'list',
  use: {
    baseURL: 'http://localhost:8080',
    trace: 'on-first-retry',
  },
  webServer: {
    command: 'echo "Using existing dev server — start with: docker compose -f docker-compose.dev.yml up -d"',
    url: 'http://localhost:8080',
    reuseExistingServer: true,
    timeout: 10000,
  },
  projects: [
    { name: 'chromium',      use: { ...devices['Desktop Chrome'] } },
    { name: 'firefox',       use: { ...devices['Desktop Firefox'] } },
    { name: 'webkit',        use: { ...devices['Desktop Safari'] } },
    { name: 'edge',          use: { ...devices['Desktop Edge'], channel: 'msedge' } },
    { name: 'mobile-chrome', use: { ...devices['Pixel 5'] } },
    { name: 'mobile-safari', use: { ...devices['iPhone 14'] } },
  ],
})
```

- [ ] Install Playwright and browsers

```bash
cd tests/e2e && npm install
npx playwright install chromium firefox webkit msedge --with-deps
```

Expected: no errors, browsers downloaded.

---

### Task 3: Django management command (5 recording modes)

**Files:**
- Create: `src/experiments/management/__init__.py`
- Create: `src/experiments/management/commands/__init__.py`
- Create: `src/experiments/management/commands/create_e2e_fixtures.py`

Five deterministic experiments — one per `recording_option`. All share the same `ListItem`→`TrialItem` structure. Each gets its own `SubjectData` so specs can navigate directly to `/{subject_id}/run` without going through the form flow.

Fixed IDs (used in every spec file):

| Mode | Experiment UUID                        | Subject UUID                           |
|------|----------------------------------------|----------------------------------------|
| NON  | `a0e2e000-0000-0000-0000-000000000001` | `b0e2e000-0000-0000-0000-000000000001` |
| AUD  | `a0e2e000-0000-0000-0000-000000000002` | `b0e2e000-0000-0000-0000-000000000002` |
| VID  | `a0e2e000-0000-0000-0000-000000000003` | `b0e2e000-0000-0000-0000-000000000003` |
| EYE  | `a0e2e000-0000-0000-0000-000000000004` | `b0e2e000-0000-0000-0000-000000000004` |
| ALL  | `a0e2e000-0000-0000-0000-000000000005` | `b0e2e000-0000-0000-0000-000000000005` |

- [ ] Check if management directory exists:

```bash
docker compose -f docker-compose.dev.yml exec web ls src/experiments/management/ 2>/dev/null || echo "MISSING"
```

Create `__init__.py` files if missing (both empty).

- [ ] Create `src/experiments/management/commands/create_e2e_fixtures.py`

```python
"""Management command to seed deterministic e2e test fixtures."""

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

from experiments.models import (
    BlockItem,
    Experiment,
    ListItem,
    OuterBlockItem,
    SubjectData,
    TrialItem,
)

MODES = [
    ('a0e2e000-0000-0000-0000-000000000001', 'b0e2e000-0000-0000-0000-000000000001', 'NON'),
    ('a0e2e000-0000-0000-0000-000000000002', 'b0e2e000-0000-0000-0000-000000000002', 'AUD'),
    ('a0e2e000-0000-0000-0000-000000000003', 'b0e2e000-0000-0000-0000-000000000003', 'VID'),
    ('a0e2e000-0000-0000-0000-000000000004', 'b0e2e000-0000-0000-0000-000000000004', 'EYE'),
    ('a0e2e000-0000-0000-0000-000000000005', 'b0e2e000-0000-0000-0000-000000000005', 'ALL'),
]


class Command(BaseCommand):
    """Create or refresh e2e test fixtures for all recording modes."""

    help = 'Create deterministic e2e test fixtures (idempotent)'

    def handle(self, *args, **options):
        """Create all e2e test objects idempotently."""
        user, _ = User.objects.get_or_create(
            username='e2euser',
            defaults={'email': 'e2e@test.local', 'is_staff': True, 'is_superuser': True},
        )
        user.set_password('e2epass')
        user.save()

        for exp_id, subject_id, mode in MODES:
            experiment, _ = Experiment.objects.get_or_create(
                id=exp_id,
                defaults={
                    'user': user,
                    'exp_name': f'e2e-{mode.lower()}',
                    'recording_option': mode,
                    'include_pause_page': False,
                    'list_selection_strategy': 'SEQ',
                    'show_gaze_estimations': False,
                    'general_onset': 0,
                },
            )

            listitem, _ = ListItem.objects.get_or_create(
                experiment=experiment,
                list_name='e2e-list',
                defaults={'global_timeout': 300000, 'exclude_list': False},
            )

            outer_block, _ = OuterBlockItem.objects.get_or_create(
                listitem=listitem,
                outer_block_name='e2e-outer',
                defaults={'position': 1, 'randomise_inner_blocks': False},
            )

            block, _ = BlockItem.objects.get_or_create(
                outerblockitem=outer_block,
                label='e2e-block',
                defaults={
                    'background_colour': '#FFFFFF',
                    'randomise_trials': False,
                    'position': 1,
                },
            )

            TrialItem.objects.get_or_create(
                blockitem=block,
                label='e2e-trial',
                defaults={
                    'code': 'E2E1',
                    'visual_onset': 0,
                    'audio_onset': 0,
                    'audio_file': '',
                    # Path need not exist — trial div still renders
                    'visual_file': 'uploads/e2e-test/placeholder.jpg',
                    'user_input': 'NO',
                    'max_duration': 1500,
                    'record_media': False,
                    'record_gaze': False,
                    'is_calibration': False,
                    'calibration_points': [],
                    'position': 1,
                },
            )

            SubjectData.objects.get_or_create(
                id=subject_id,
                defaults={
                    'experiment': experiment,
                    'listitem': listitem,
                    'participant_id': 9000 + MODES.index((exp_id, subject_id, mode)),
                },
            )

        self.stdout.write(self.style.SUCCESS('e2e fixtures created for all 5 recording modes'))
```

- [ ] Verify:

```bash
docker compose -f docker-compose.dev.yml exec web uv run python manage.py create_e2e_fixtures
```

Expected: `e2e fixtures created for all 5 recording modes`

---

### Task 3: global-setup and global-teardown

**Files:**
- Create: `tests/e2e/global-setup.js`
- Create: `tests/e2e/global-teardown.js`

- [ ] Create `tests/e2e/global-setup.js`

```js
import { execSync } from 'child_process'

export default async function globalSetup() {
  execSync(
    'docker compose -f docker-compose.dev.yml exec -T web uv run python manage.py create_e2e_fixtures',
    { stdio: 'inherit' },
  )
}
```

- [ ] Create `tests/e2e/global-teardown.js`

```js
import { execSync } from 'child_process'

// IDs match MODES in create_e2e_fixtures.py
const SUBJECT_IDS = [
  'b0e2e000-0000-0000-0000-000000000001',
  'b0e2e000-0000-0000-0000-000000000002',
  'b0e2e000-0000-0000-0000-000000000003',
  'b0e2e000-0000-0000-0000-000000000004',
  'b0e2e000-0000-0000-0000-000000000005',
]
const EXP_IDS = [
  'a0e2e000-0000-0000-0000-000000000001',
  'a0e2e000-0000-0000-0000-000000000002',
  'a0e2e000-0000-0000-0000-000000000003',
  'a0e2e000-0000-0000-0000-000000000004',
  'a0e2e000-0000-0000-0000-000000000005',
]

export default async function globalTeardown() {
  const subjectList = SUBJECT_IDS.map(id => `'${id}'`).join(', ')
  const expList = EXP_IDS.map(id => `'${id}'`).join(', ')
  execSync(
    `docker compose -f docker-compose.dev.yml exec -T web uv run python manage.py shell -c "
from experiments.models import SubjectData, Experiment, TrialResult
TrialResult.objects.filter(subject_id__in=[${subjectList}]).delete()
SubjectData.objects.filter(id__in=[${subjectList}]).delete()
Experiment.objects.filter(id__in=[${expList}]).delete()
print('e2e fixtures cleaned up')
"`,
    { stdio: 'inherit' },
  )
}
```

---

### Task 4: Shared test helpers

Create a shared helpers file to avoid repeating stub setup in every spec.

**Files:**
- Create: `tests/e2e/helpers.js`

- [ ] Create `tests/e2e/helpers.js`

```js
/**
 * Stubs browser APIs that require hardware or real fullscreen.
 * Call via page.addInitScript(stubBrowserAPIs) in beforeEach.
 */
export function stubBrowserAPIs() {
  // Fullscreen API — Chromium/WebKit block requestFullscreen in tests
  document.documentElement.requestFullscreen = () => Promise.resolve()
  document.exitFullscreen = () => Promise.resolve()
  Object.defineProperty(document, 'fullscreenElement', {
    get: () => document.documentElement,
    configurable: true,
  })

  // WebGazer — vendored script, not an ES module
  window.webgazer = {
    pause: () => {},
    resume: () => Promise.resolve(),
    setGazeListener: () => window.webgazer,
    setTracker: () => window.webgazer,
    saveDataAcrossSessions: () => window.webgazer,
    showPredictionPoints: () => window.webgazer,
    begin: () => Promise.resolve(window.webgazer),
    getCurrentPrediction: () => Promise.resolve(null),
  }

  // getUserMedia — avoids real camera/mic permission dialogs
  const fakeStream = {
    getTracks: () => [{ stop: () => {} }],
    getVideoTracks: () => [{ stop: () => {} }],
    getAudioTracks: () => [{ stop: () => {} }],
  }
  if (navigator.mediaDevices) {
    navigator.mediaDevices.getUserMedia = () => Promise.resolve(fakeStream)
  } else {
    Object.defineProperty(navigator, 'mediaDevices', {
      value: { getUserMedia: () => Promise.resolve(fakeStream) },
      configurable: true,
    })
  }
}
```

---

### Task 5: Browser check e2e spec

**Files:**
- Create: `tests/e2e/specs/browser-check.spec.js`

URL: `/{experiment_id}/browsercheck/`. Tests run across all 6 browser projects via the default Playwright config.

- [ ] Create `tests/e2e/specs/browser-check.spec.js`

```js
import { expect, test } from '@playwright/test'
import { stubBrowserAPIs } from '../helpers.js'

const EXP_NON = 'a0e2e000-0000-0000-0000-000000000001'

test.beforeEach(async ({ page }) => {
  await page.addInitScript(stubBrowserAPIs)
})

test('browser check page loads without JS errors', async ({ page }) => {
  const errors = []
  page.on('pageerror', e => errors.push(e.message))
  await page.goto(`/${EXP_NON}/browsercheck/`)
  await page.waitForLoadState('networkidle')
  expect(errors, `JS errors: ${errors.join('; ')}`).toHaveLength(0)
})

test('no SyntaxError — ES2022 features supported in all target browsers', async ({ page }) => {
  const syntaxErrors = []
  page.on('console', msg => {
    if (msg.type() === 'error' && msg.text().includes('SyntaxError')) {
      syntaxErrors.push(msg.text())
    }
  })
  await page.goto(`/${EXP_NON}/browsercheck/`)
  await page.waitForLoadState('networkidle')
  expect(syntaxErrors).toHaveLength(0)
})
```

- [ ] Run against chromium only to verify:

```bash
cd tests/e2e && npx playwright test specs/browser-check.spec.js --project=chromium
```

Expected: 2 passed

---

### Task 6: Demographic form e2e spec

**Files:**
- Create: `tests/e2e/specs/demographic.spec.js`

URL: `/{experiment_id}/form/`. `resolution.js` populates hidden `resolution_w` / `resolution_h` inputs.

- [ ] Create `tests/e2e/specs/demographic.spec.js`

```js
import { expect, test } from '@playwright/test'
import { stubBrowserAPIs } from '../helpers.js'

const EXP_NON = 'a0e2e000-0000-0000-0000-000000000001'

test.beforeEach(async ({ page }) => {
  await page.addInitScript(stubBrowserAPIs)
})

test('demographic form page loads without JS errors', async ({ page }) => {
  const errors = []
  page.on('pageerror', e => errors.push(e.message))
  await page.goto(`/${EXP_NON}/form/`)
  await page.waitForLoadState('networkidle')
  expect(errors, `JS errors: ${errors.join('; ')}`).toHaveLength(0)
})

test('resolution.js populates resolution_w and resolution_h inputs', async ({ page }) => {
  await page.goto(`/${EXP_NON}/form/`)
  await page.waitForLoadState('networkidle')
  const w = await page.inputValue('input[name="resolution_w"]')
  const h = await page.inputValue('input[name="resolution_h"]')
  expect(Number(w)).toBeGreaterThan(0)
  expect(Number(h)).toBeGreaterThan(0)
})
```

- [ ] Run:

```bash
cd tests/e2e && npx playwright test specs/demographic.spec.js --project=chromium
```

Expected: 2 passed

---

### Task 7: Webcam calibration e2e spec

**Files:**
- Create: `tests/e2e/specs/webcam-calibration.spec.js`

URL: `/{subject_id}/test`. The webcam check page is only shown for non-NON recording modes. Use the AUD subject (`b0e2e000-0000-0000-0000-000000000002`) so the page is actually visited.

**Note:** Verify in `views.py` that the webcam test page is accessible for AUD mode (not redirected away). If the view checks recording_option and redirects for certain modes, adjust the subject UUID accordingly.

- [ ] Create `tests/e2e/specs/webcam-calibration.spec.js`

```js
import { expect, test } from '@playwright/test'
import { stubBrowserAPIs } from '../helpers.js'

// AUD mode subject — webcam test page is shown for non-NON modes
const SUBJECT_AUD = 'b0e2e000-0000-0000-0000-000000000002'

test.beforeEach(async ({ page }) => {
  await page.addInitScript(stubBrowserAPIs)
})

test('webcam calibration page loads without JS errors', async ({ page }) => {
  const errors = []
  page.on('pageerror', e => errors.push(e.message))
  await page.goto(`/${SUBJECT_AUD}/test`)
  await page.waitForLoadState('networkidle')
  expect(errors, `JS errors: ${errors.join('; ')}`).toHaveLength(0)
})

test('page body is visible after getUserMedia resolves (stubbed)', async ({ page }) => {
  await page.goto(`/${SUBJECT_AUD}/test`)
  await page.waitForLoadState('networkidle')
  await expect(page.locator('body')).toBeVisible()
})
```

- [ ] Run:

```bash
cd tests/e2e && npx playwright test specs/webcam-calibration.spec.js --project=chromium
```

Expected: 2 passed (or redirected — see note above and adjust subject UUID)

---

### Task 8: Experiment run page e2e spec (NON mode)

**Files:**
- Create: `tests/e2e/specs/experiment.spec.js`

URL: `/{subject_id}/run`. NON mode — no `getUserMedia` needed. `requestFullscreen` stubbed.

The `storeresult` POST hits the real Django backend. The NON subject's listitem is linked to a TrialItem with `max_duration=1500`, so after ~1.5 s the trial posts and navigates to `/thankyou`.

- [ ] Create `tests/e2e/specs/experiment.spec.js`

```js
import { expect, test } from '@playwright/test'
import { stubBrowserAPIs } from '../helpers.js'

const SUBJECT_NON = 'b0e2e000-0000-0000-0000-000000000001'

test.beforeEach(async ({ page }) => {
  await page.addInitScript(stubBrowserAPIs)
})

test('experiment run page loads without JS errors', async ({ page }) => {
  const errors = []
  page.on('pageerror', e => errors.push(e.message))
  await page.goto(`/${SUBJECT_NON}/run`)
  await page.waitForLoadState('networkidle')
  expect(errors, `JS errors: ${errors.join('; ')}`).toHaveLength(0)
})

test('clicking fullscreen button renders trial image', async ({ page }) => {
  await page.goto(`/${SUBJECT_NON}/run`)
  // fullscreen-button is disabled until window load fires
  await expect(page.locator('#fullscreen-button')).not.toBeDisabled({ timeout: 5000 })
  await page.locator('#fullscreen-button').click()
  // .trial-image appended after visual_onset (0ms)
  await expect(page.locator('.trial-image')).toBeVisible({ timeout: 3000 })
})

test('navigates to thankyou after trial completes (max_duration=1500ms)', async ({ page }) => {
  await page.goto(`/${SUBJECT_NON}/run`)
  await expect(page.locator('#fullscreen-button')).not.toBeDisabled({ timeout: 5000 })
  await page.locator('#fullscreen-button').click()
  // 1500ms trial + fetch roundtrip + navigation
  await page.waitForURL(`**/${SUBJECT_NON}/run/thankyou`, { timeout: 10000 })
})
```

- [ ] Run:

```bash
cd tests/e2e && npx playwright test specs/experiment.spec.js --project=chromium
```

Expected: 3 passed

**Troubleshooting:** If `storeresult` returns 403, the CSRF token may not be set. `getCsrfToken()` reads from `document.cookie`. Verify that the Django dev server sends the `csrftoken` cookie on the `/run` page.

---

### Task 9: End page e2e spec

**Files:**
- Create: `tests/e2e/specs/endpage.spec.js`

- [ ] Create `tests/e2e/specs/endpage.spec.js`

```js
import { expect, test } from '@playwright/test'

const SUBJECT_NON = 'b0e2e000-0000-0000-0000-000000000001'

test('end page loads without JS errors', async ({ page }) => {
  const errors = []
  page.on('pageerror', e => errors.push(e.message))
  await page.goto(`/${SUBJECT_NON}/run/thankyou`)
  await page.waitForLoadState('networkidle')
  expect(errors, `JS errors: ${errors.join('; ')}`).toHaveLength(0)
})

test('end page body is visible', async ({ page }) => {
  await page.goto(`/${SUBJECT_NON}/run/thankyou`)
  await expect(page.locator('body')).toBeVisible()
})
```

- [ ] Run:

```bash
cd tests/e2e && npx playwright test specs/endpage.spec.js --project=chromium
```

Expected: 2 passed

---

### Task 10: Run full Playwright suite across all browsers

- [ ] Run full suite (skip edge for now — needs msedge installed):

```bash
cd tests/e2e && npx playwright test --project=chromium --project=firefox --project=webkit --project=mobile-chrome --project=mobile-safari
```

Fix any failures before proceeding to CI.

- [ ] Commit Playwright tests and management command:

```
git add tests/e2e/ src/experiments/management/
git commit -m "$(cat <<'EOF'
Add Playwright e2e test suite for participant-facing flows

- Add tests/e2e/ with Playwright 1.x, 6 browser projects (Chrome, Firefox,
  WebKit, Edge, Pixel 5/mobile-chrome, iPhone 14/mobile-safari)
- Add create_e2e_fixtures management command: idempotent creation of 5
  experiments (one per recording mode NON/AUD/VID/EYE/ALL) with fixed
  UUIDs for stable test URLs across runs
- global-setup seeds fixtures; global-teardown removes e2e data including
  any TrialResults created during the run
- stubBrowserAPIs helper stubs getUserMedia, requestFullscreen, webgazer
- Specs: browser check (ES2022 compat), demographic form (resolution.js),
  webcam calibration (stubbed stream), experiment run NON mode
  (fullscreen→trial image→thankyou nav), end page
EOF
)"
```

---

## Part B — CI and docs

### Task 11: GitHub Actions workflow

**Files:**
- Create: `.github/workflows/tests.yml`

The workflow has three jobs:
1. `python-tests`: pytest inside Docker on ubuntu
2. `js-unit-tests`: vitest on ubuntu (no Docker)
3. `e2e-ubuntu`: Playwright chromium/firefox/webkit/mobile-chrome on ubuntu
4. `e2e-macos`: Playwright mobile-safari (WebKit + iPhone emulation) on macos — most accurate Safari/iOS approximation

Edge is included in the ubuntu job. Docker on macOS CI requires colima.

- [ ] Create `.github/workflows/tests.yml`

```yaml
name: Tests

on:
  push:
    branches: [main, refactor-js]
  pull_request:

jobs:
  python-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Start dev server
        run: docker compose -f docker-compose.dev.yml up -d --build

      - name: Wait for server to be ready
        run: |
          for i in $(seq 1 30); do
            curl -fs http://localhost:8080/admin/ && break
            sleep 3
          done

      - name: Run database migrations
        run: docker compose -f docker-compose.dev.yml exec -T web uv run python manage.py migrate

      - name: Run pytest
        run: docker compose -f docker-compose.dev.yml exec -T web uv run pytest

  js-unit-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: npm
          cache-dependency-path: tests/js/package-lock.json

      - name: Install dependencies
        run: cd tests/js && npm ci

      - name: Run Vitest
        run: cd tests && npm run test:unit

  e2e-ubuntu:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Start dev server
        run: docker compose -f docker-compose.dev.yml up -d --build

      - name: Wait for server to be ready
        run: |
          for i in $(seq 1 30); do
            curl -fs http://localhost:8080/admin/ && break
            sleep 3
          done

      - name: Run database migrations
        run: docker compose -f docker-compose.dev.yml exec -T web uv run python manage.py migrate

      - uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: npm
          cache-dependency-path: tests/e2e/package-lock.json

      - name: Install Playwright dependencies
        run: cd tests/e2e && npm ci && npx playwright install --with-deps chromium firefox webkit msedge

      - name: Run e2e tests (Chrome, Firefox, WebKit, Edge, Android Chrome)
        run: >
          cd tests/e2e && npx playwright test
          --project=chromium
          --project=firefox
          --project=webkit
          --project=edge
          --project=mobile-chrome

      - name: Upload Playwright report
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: playwright-report-ubuntu
          path: tests/e2e/playwright-report/
          retention-days: 7

  e2e-macos:
    runs-on: macos-latest
    steps:
      - uses: actions/checkout@v4

      # macOS GitHub runners do not include Docker — install via colima
      - name: Install colima and Docker CLI
        run: |
          brew install colima docker docker-compose
          colima start --cpu 2 --memory 4 --disk 20

      - name: Start dev server
        run: docker compose -f docker-compose.dev.yml up -d --build

      - name: Wait for server to be ready
        run: |
          for i in $(seq 1 30); do
            curl -fs http://localhost:8080/admin/ && break
            sleep 3
          done

      - name: Run database migrations
        run: docker compose -f docker-compose.dev.yml exec -T web uv run python manage.py migrate

      - uses: actions/setup-node@v4
        with:
          node-version: '20'

      - name: Install Playwright WebKit
        run: cd tests/e2e && npm ci && npx playwright install --with-deps webkit

      - name: Run e2e tests (iOS Safari — WebKit + iPhone 14 emulation)
        run: cd tests/e2e && npx playwright test --project=mobile-safari

      - name: Upload Playwright report
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: playwright-report-macos
          path: tests/e2e/playwright-report/
          retention-days: 7
```

- [ ] Commit workflow:

```
git add .github/
git commit -m "$(cat <<'EOF'
Add GitHub Actions CI workflow for all test suites

- python-tests: pytest inside Docker on ubuntu-latest
- js-unit-tests: vitest on ubuntu-latest (no Docker)
- e2e-ubuntu: Playwright on ubuntu, covers Chrome/Firefox/WebKit/Edge/
  Android Chrome (Pixel 5 emulation)
- e2e-macos: Playwright WebKit on macos-latest via colima, covers
  iOS Safari (iPhone 14 emulation); macOS runner gives most accurate
  WebKit/Safari behaviour
- Upload Playwright HTML reports as artifacts on failure
EOF
)"
```

---

### Task 12: Update local-development.md

**Files:**
- Modify: `docs/source/get_started/local-development.md`

Add an "End-to-End Tests (Playwright)" section after the existing Vitest section.

- [ ] Add the following after the `### JavaScript (Vitest)` section (before `## Database Admin`):

```markdown
### End-to-End Tests (Playwright)

E2e tests run against the live dev server. Requires Docker and Node.js.

**Prerequisites:** The dev server must be running (see [First-Time Setup](#first-time-setup)).

**Install once:**

```bash
cd tests/e2e
npm install
npx playwright install chromium firefox webkit msedge --with-deps
```

**Seed test data:**

The test suite uses deterministic fixtures (fixed UUIDs for 5 recording-mode experiments). Seed them once — the command is idempotent:

```bash
docker compose -f docker-compose.dev.yml exec web uv run python manage.py create_e2e_fixtures
```

**Run all browsers:**

```bash
cd tests/e2e && npm test
```

**Run a single browser:**

```bash
cd tests/e2e && npx playwright test --project=chromium
```

**Run a single spec:**

```bash
cd tests/e2e && npx playwright test specs/experiment.spec.js --project=chromium
```

**Interactive UI mode:**

```bash
cd tests/e2e && npm run test:ui
```

**Browser coverage:**

| Project        | Browser              | Platform          |
|----------------|----------------------|-------------------|
| `chromium`     | Chrome               | Desktop           |
| `firefox`      | Firefox              | Desktop           |
| `webkit`       | Safari (approximate) | Desktop           |
| `edge`         | Edge                 | Desktop           |
| `mobile-chrome`| Chrome               | Android (Pixel 5) |
| `mobile-safari`| Safari               | iOS (iPhone 14)   |

> **Note:** `mobile-safari` uses WebKit with iPhone 14 device emulation. For the most accurate Safari results, run this project on macOS (CI uses a macOS runner; locally, it works on any platform but macOS gives the closest match to real Safari).
```

- [ ] Update the existing `exec web python` commands to use `uv run python`:

```bash
# OLD (line 12):
docker compose -f docker-compose.dev.yml exec web python manage.py migrate
# NEW:
docker compose -f docker-compose.dev.yml exec web uv run python manage.py migrate
```

Apply the same `uv run python` → `uv run python` fix to all `manage.py` commands in the file (lines 12, 17, 22, 27, 99, 102, 114).

- [ ] Commit:

```
git add docs/source/get_started/local-development.md
git commit -m "$(cat <<'EOF'
Update local-development.md for e2e tests and uv run consistency

- Add Playwright e2e section: install, fixture seeding, run commands,
  browser coverage table, note about mobile-safari on macOS
- Fix all manage.py examples to use uv run python (was plain python)
EOF
)"
```

---

## Part C — experiment.js unit tests (Priority 2)

### Task 13: Extend makeEnv + add makeTrial

**Files:**
- Modify: `tests/js/experiment.test.js`

`makeEnv` currently only accepts `{ recordingOption, trials }`. Extend to accept `globalTimeout` and `includePausePage` — needed for timeout tests without calling `init()` twice.

- [ ] Replace the existing `makeEnv` function (lines 49–76):

```js
function makeTrial(overrides = {}) {
  return {
    trial_id: 1,
    trial_number: 1,
    trial_type: 'image',
    label: 'test',
    visual_file: '/media/test.jpg',
    audio_file: '',
    require_user_input: 'NO',
    is_calibration: false,
    record_gaze: false,
    record_media: true,
    response_keys: [],
    max_duration: 50,
    background_colour: '#ffffff',
    audio_onset: '0',
    visual_onset: '0',
    ...overrides,
  }
}

function makeEnv({
  recordingOption = 'NON',
  trials = [],
  globalTimeout = '600000',
  includePausePage = 'false',
} = {}) {
  document.body.innerHTML = BASE_HTML
  const trialsEl = document.getElementById('trials')
  trialsEl.dataset.recordingOption = recordingOption
  trialsEl.dataset.globalTimeout = globalTimeout
  trialsEl.dataset.includePausePage = includePausePage
  document.getElementById('trials-data').textContent = JSON.stringify(trials)

  const locationReplace = vi.fn()
  vi.stubGlobal('location', { replace: locationReplace, href: '', assign: vi.fn() })
  vi.stubGlobal('webgazer', {
    pause:                vi.fn(),
    resume:               vi.fn().mockResolvedValue(undefined),
    getCurrentPrediction: vi.fn().mockResolvedValue(null),
  })
  vi.stubGlobal('bootstrap', { Modal: class { constructor() {} show() {} } })
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
    ok:   true,
    json: () => Promise.resolve({ resultId: 42 }),
    text: () => Promise.resolve(''),
  }))

  vi.mocked(webcam.initStream).mockResolvedValue({})
  vi.mocked(webcam.getLength).mockReturnValue(0)
  vi.mocked(webcam.waitForQueue).mockResolvedValue(undefined)
  vi.mocked(webcam.stopRecording).mockResolvedValue(undefined)
  vi.mocked(initWebgazer).mockResolvedValue(undefined)

  init()
  return { locationReplace, mockWebcam: webcam, mockInitWebgazer: initWebgazer }
}
```

- [ ] Run existing tests — verify 3 still pass:

```bash
cd tests/js && npm test
```

---

### Task 14: postResult tests

- [ ] Add after existing `describe('experiment.js — trial flow', ...)` block:

```js
describe('experiment.js — postResult', () => {
  beforeEach(() => { vi.useFakeTimers() })
  afterEach(() => { vi.useRealTimers() })

  it('POSTs to storeresult URL with trial data', async () => {
    makeEnv({ recordingOption: 'NON', trials: [makeTrial()] })
    await vi.runAllMicrotasksAsync()
    document.getElementById('fullscreen-button').click()
    await vi.runAllMicrotasksAsync()
    // visual_onset=0 (setTimeout 0) + max_duration=50
    await vi.advanceTimersByTimeAsync(60)
    await vi.runAllMicrotasksAsync()
    expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining('/run/storeresult'),
      expect.objectContaining({ method: 'POST' }),
    )
  })

  it('passes resultId from response to webcam.stopRecording', async () => {
    const { mockWebcam } = makeEnv({ recordingOption: 'NON', trials: [makeTrial()] })
    await vi.runAllMicrotasksAsync()
    document.getElementById('fullscreen-button').click()
    await vi.runAllMicrotasksAsync()
    await vi.advanceTimersByTimeAsync(60)
    await vi.runAllMicrotasksAsync()
    // fetch mock resolves { resultId: 42 }
    expect(mockWebcam.stopRecording).toHaveBeenCalledWith(42)
  })
})
```

- [ ] Run: `cd tests/js && npm test` — expect 5 passed

---

### Task 15: Trial rendering and advance tests

- [ ] Add inside existing `describe('experiment.js — trial flow', ...)`:

```js
it('appends .trial-image to body for image trial', async () => {
  vi.useFakeTimers()
  makeEnv({ recordingOption: 'NON', trials: [makeTrial()] })
  await vi.runAllMicrotasksAsync()
  document.getElementById('fullscreen-button').click()
  await vi.runAllMicrotasksAsync()
  await vi.advanceTimersByTimeAsync(0) // flush visual_onset setTimeout(0)
  await vi.runAllMicrotasksAsync()
  expect(document.querySelector('.trial-image')).not.toBeNull()
  vi.useRealTimers()
})

it('renders second trial after first completes via max_duration', async () => {
  vi.useFakeTimers()
  const trial1 = makeTrial({ trial_id: 1, visual_file: '/media/a.jpg' })
  const trial2 = makeTrial({ trial_id: 2, trial_number: 2, visual_file: '/media/b.jpg' })
  makeEnv({ recordingOption: 'NON', trials: [trial1, trial2] })
  await vi.runAllMicrotasksAsync()
  document.getElementById('fullscreen-button').click()
  await vi.runAllMicrotasksAsync()
  await vi.advanceTimersByTimeAsync(60)  // first trial max_duration
  await vi.runAllMicrotasksAsync()
  await vi.advanceTimersByTimeAsync(10)  // postResult + stopRecording settle
  await vi.runAllMicrotasksAsync()
  const img = document.querySelector('.trial-image')
  expect(img).not.toBeNull()
  expect(img.style.backgroundImage).toContain('b.jpg')
  vi.useRealTimers()
})

it('navigates to thankyou after all trials complete', async () => {
  vi.useFakeTimers()
  const { locationReplace } = makeEnv({ recordingOption: 'NON', trials: [makeTrial()] })
  await vi.runAllMicrotasksAsync()
  document.getElementById('fullscreen-button').click()
  await vi.runAllMicrotasksAsync()
  await vi.advanceTimersByTimeAsync(60)
  await vi.runAllMicrotasksAsync()
  await vi.advanceTimersByTimeAsync(10)
  await vi.runAllMicrotasksAsync()
  expect(locationReplace).toHaveBeenCalledWith(expect.stringContaining('thankyou'))
  vi.useRealTimers()
})
```

- [ ] Run: `cd tests/js && npm test` — expect 8 passed

---

### Task 16: Webcam recording branch tests

- [ ] Add new describe block:

```js
describe('experiment.js — webcam recording', () => {
  beforeEach(() => { vi.useFakeTimers() })
  afterEach(() => { vi.useRealTimers() })

  it('calls startRecording for VID trial with record_media true', async () => {
    const { mockWebcam } = makeEnv({
      recordingOption: 'VID',
      trials: [makeTrial({ record_media: true })],
    })
    await vi.runAllMicrotasksAsync()
    document.getElementById('fullscreen-button').click()
    await vi.runAllMicrotasksAsync()
    await vi.advanceTimersByTimeAsync(10)
    await vi.runAllMicrotasksAsync()
    expect(mockWebcam.startRecording).toHaveBeenCalledWith(
      expect.stringContaining('trial1'),
      'VID',
      expect.anything(),
    )
  })

  it('does not call startRecording when record_media is false', async () => {
    const { mockWebcam } = makeEnv({
      recordingOption: 'VID',
      trials: [makeTrial({ record_media: false })],
    })
    await vi.runAllMicrotasksAsync()
    document.getElementById('fullscreen-button').click()
    await vi.runAllMicrotasksAsync()
    await vi.advanceTimersByTimeAsync(10)
    await vi.runAllMicrotasksAsync()
    expect(mockWebcam.startRecording).not.toHaveBeenCalled()
  })

  it('does not call startRecording for NON recording option', async () => {
    const { mockWebcam } = makeEnv({
      recordingOption: 'NON',
      trials: [makeTrial({ record_media: true })],
    })
    await vi.runAllMicrotasksAsync()
    document.getElementById('fullscreen-button').click()
    await vi.runAllMicrotasksAsync()
    await vi.advanceTimersByTimeAsync(10)
    await vi.runAllMicrotasksAsync()
    expect(mockWebcam.startRecording).not.toHaveBeenCalled()
  })
})
```

- [ ] Run: `cd tests/js && npm test` — expect 11 passed

---

### Task 17: Global timeout tests

- [ ] Add new describe block:

```js
describe('experiment.js — global timeout', () => {
  beforeEach(() => { vi.useFakeTimers() })
  afterEach(() => { vi.useRealTimers() })

  it('navigates to thankyou on timeout when include_pause_page is false', async () => {
    const { locationReplace } = makeEnv({
      recordingOption: 'NON',
      trials: [makeTrial({ max_duration: 500 })],
      globalTimeout: '100',
      includePausePage: 'false',
    })
    await vi.runAllMicrotasksAsync()
    document.getElementById('fullscreen-button').click()
    await vi.runAllMicrotasksAsync()
    // advance past global_timeout (100) but before max_duration (500)
    await vi.advanceTimersByTimeAsync(110)
    await vi.runAllMicrotasksAsync()
    expect(locationReplace).toHaveBeenCalledWith(expect.stringContaining('thankyou'))
  })

  it('navigates to pause on timeout when include_pause_page is true', async () => {
    const { locationReplace } = makeEnv({
      recordingOption: 'NON',
      trials: [makeTrial({ max_duration: 500 })],
      globalTimeout: '100',
      includePausePage: 'true',
    })
    await vi.runAllMicrotasksAsync()
    document.getElementById('fullscreen-button').click()
    await vi.runAllMicrotasksAsync()
    await vi.advanceTimersByTimeAsync(110)
    await vi.runAllMicrotasksAsync()
    expect(locationReplace).toHaveBeenCalledWith(expect.stringContaining('pause'))
  })
})
```

- [ ] Run: `cd tests/js && npm test` — expect 13 passed

---

### Task 18: Exit button tests

- [ ] Add new describe block:

```js
describe('experiment.js — exit button', () => {
  it('navigates when exit button clicked and upload queue is empty', () => {
    const { locationReplace, mockWebcam } = makeEnv({ recordingOption: 'NON', trials: [] })
    vi.mocked(mockWebcam.getLength).mockReturnValue(0)
    document.getElementById('exit-button').click()
    expect(locationReplace).toHaveBeenCalledWith(expect.stringMatching(/thankyou|pause/))
  })

  it('shows modal when exit button clicked and upload queue is non-empty', () => {
    const showSpy = vi.fn()
    vi.stubGlobal('bootstrap', { Modal: class { constructor() {} show() { showSpy() } } })
    const { mockWebcam } = makeEnv({ recordingOption: 'NON', trials: [] })
    vi.mocked(mockWebcam.getLength).mockReturnValue(3)
    document.getElementById('exit-button').click()
    expect(showSpy).toHaveBeenCalled()
  })
})
```

- [ ] Run full suite: `cd tests/js && npm test` — expect 15 passed

---

### Task 19: Commit unit tests

- [ ] Commit:

```
git add tests/js/experiment.test.js
git commit -m "$(cat <<'EOF'
Expand experiment.js unit test coverage from 3 to 15 tests

- Add makeTrial() helper for concise trial fixture construction
- Extend makeEnv() with globalTimeout and includePausePage options
- Test postResult: POSTs to storeresult URL, passes resultId to
  webcam.stopRecording
- Test showNextTrial: .trial-image rendered, advances to next trial after
  max_duration elapses, navigates to /thankyou when trials exhausted
- Test webcam recording: startRecording called/skipped based on
  recording_option and record_media flag
- Test global timeout: fires /thankyou or /pause per include_pause_page
- Test exit button: navigates directly when queue empty, shows modal when not
EOF
)"
```

---

## Part D — Write Phase 4b Handoff

### Task 20: Write handoff document

**Files:**
- Create: `.claude/js-modernisation-phase4-handoff.md`

- [ ] Create `.claude/js-modernisation-phase4-handoff.md` with the following content:

```markdown
# JS Modernisation Phase 4b Handoff

## What Phase 4a Completed

| Area | Status |
|---|---|
| Playwright infrastructure | ✅ `tests/e2e/` with 6 browser projects |
| Management command | ✅ `create_e2e_fixtures` — 5 experiments (NON/AUD/VID/EYE/ALL) + 5 subjects |
| NON-mode e2e specs | ✅ browser-check, demographic, webcam-calibration, experiment run, end page |
| CI workflow | ✅ `.github/workflows/tests.yml` — ubuntu (Chrome/Firefox/WebKit/Edge/Android) + macos (iOS Safari) |
| experiment.js unit tests | ✅ 15 tests (up from 3): postResult, trial flow, webcam recording, global timeout, exit button |
| Docs | ✅ local-development.md updated with e2e section and uv run fixes |

**Total JS test count:** ~65 (50 unit + ~15 e2e × 6 browsers)

## Phase 4b Scope

### Priority 1: Per-recording-mode e2e tests

The `create_e2e_fixtures` command already seeded experiments for AUD/VID/EYE/ALL. Phase 4b adds specs for each mode.

**Fixed UUIDs (from create_e2e_fixtures.py):**

| Mode | Experiment UUID | Subject UUID |
|---|---|---|
| AUD | `a0e2e000-0000-0000-0000-000000000002` | `b0e2e000-0000-0000-0000-000000000002` |
| VID | `a0e2e000-0000-0000-0000-000000000003` | `b0e2e000-0000-0000-0000-000000000003` |
| EYE | `a0e2e000-0000-0000-0000-000000000004` | `b0e2e000-0000-0000-0000-000000000004` |
| ALL | `a0e2e000-0000-0000-0000-000000000005` | `b0e2e000-0000-0000-0000-000000000005` |

**AUD / VID tests:**
- Stub `getUserMedia` via `stubBrowserAPIs` helper (already in `tests/e2e/helpers.js`)
- Test that webcam calibration page (`/{subject}/test`) shows recording UI
- Test full experiment run: stream initialised → trial completes → `webcam.stopRecording` called → thankyou nav
- Note: `webcam.startRecording` actually calls `MediaRecorder` internally; stub `MediaRecorder` via `page.addInitScript` if it throws in test context

**EYE / ALL tests:**
- WebGazer is already stubbed in `stubBrowserAPIs`
- Test that `initWebgazer` is called after fullscreen (experiment.js:603–605)
- Test that `webgazer.resume` is called per trial
- `calibrate()` (from webgazer-calibration.js) is called for `is_calibration` trials; set `is_calibration=True` on the EYE/ALL trial fixture if testing calibration flow

**Suggested new files:**
- `tests/e2e/specs/experiment-aud.spec.js`
- `tests/e2e/specs/experiment-vid.spec.js`
- `tests/e2e/specs/experiment-eye.spec.js`
- `tests/e2e/specs/experiment-all.spec.js`

### Priority 2: Additional unit tests for experiment.js

Remaining untested behaviours (see original Phase 3 handoff):

- **Video trial type** — `playTrialVideo` + `setupVideoEnd`: jsdom doesn't dispatch `canplay`/`ended` events; mock `HTMLVideoElement.prototype.play` and manually dispatch events
- **Keypress response** (`setupKeyPresses`): dispatch `KeyboardEvent` via `document.dispatchEvent(new KeyboardEvent('keydown', { which: 65 }))` after trial starts; verify `keysPressed` populated and `location.replace` called
- **Click response** (`response_keys: ['click']`): dispatch `MouseEvent` on document

### Priority 3: Vite bundling (optional)

Still out of scope — file count small, no measurable load-time issue. Revisit if network request count becomes a concern.

## Known Caveats

**`e2e_macos` CI job is slow:** colima startup adds ~3–4 min. Consider caching colima VM image or running macOS job on schedule (not every push) if it becomes a bottleneck.

**Edge in CI:** Requires `npx playwright install msedge --with-deps`. Edge download is ~200 MB. The ubuntu CI job caches npm but not browser binaries by default. Add `cache: playwright` action if CI times out.

**`storeresult` POST creates TrialResult rows:** `global-teardown.js` deletes them, but if the teardown fails (crash, SIGKILL), rows accumulate. The `participant_id: 9000+` range makes them easy to clean up manually.

**`webcam-calibration.spec.js` AUD subject:** Phase 4a uses `SUBJECT_AUD` for the webcam test page. Verify `views.webcam_test` doesn't redirect AUD mode subjects away from the test page.
```

- [ ] Commit handoff:

```
git add .claude/js-modernisation-phase4-handoff.md
git commit -m "$(cat <<'EOF'
Add Phase 4b handoff for per-recording-mode e2e tests

- Documents AUD/VID/EYE/ALL fixture UUIDs and test approach
- Notes MediaRecorder and WebGazer stub strategies
- Lists remaining experiment.js unit test gaps (video trials, keypress)
- Carries forward known caveats: colima CI overhead, Edge browser cache,
  storeresult row accumulation
EOF
)"
```

---

## Self-Review

**Spec coverage:**
- ✅ Browser check e2e — Task 5
- ✅ Demographic form + resolution.js — Task 6
- ✅ Webcam calibration page — Task 7
- ✅ Experiment run (NON): fullscreen→image→thankyou — Task 8
- ✅ End page — Task 9
- ✅ All browsers: Chrome/Firefox/WebKit/Edge/Android — Task 10
- ✅ iOS Safari (macOS runner) — Task 11 (CI)
- ✅ 5 recording mode experiments seeded — Task 2
- ✅ postResult — Task 14
- ✅ Trial image render + advance + thankyou nav — Task 15
- ✅ webcam.startRecording branches — Task 16
- ✅ Global timeout (thankyou + pause) — Task 17
- ✅ Exit button (empty/non-empty queue) — Task 18
- ✅ CI workflow (ubuntu + macos) — Task 11
- ✅ local-development.md update — Task 12
- ✅ Phase 4b handoff — Task 20
- ⚠️ AUD/VID/EYE/ALL e2e specs — deferred to Phase 4b per plan split
- ⚠️ Video trial unit tests — deferred to Phase 4b

**Placeholder scan:** All tasks contain actual code or exact commands. No "TBD" or "implement as appropriate" language.

**Type consistency:** `makeTrial()` keys (`trial_id`, `trial_type`, `audio_file`, etc.) match the property accesses in experiment.js. `makeEnv` return shape unchanged from existing 3-test usage.
