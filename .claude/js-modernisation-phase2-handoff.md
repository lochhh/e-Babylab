# JS Modernisation Phase 2 Handoff

## What Phase 2 Completed

jQuery fully removed from all 5 remaining browser-side JS files. Test infrastructure migrated from `vm.runInNewContext` + jQuery mocks to jsdom + native DOM.

| File | jQuery | Changes |
|---|---|---|
| `endpage.js` | **Removed** | `$(sel).click(fn)` → `addEventListener`; `.addClass/.removeClass` → `.classList` |
| `resolution.js` | **Removed** | `$(function(){})` wrapper removed; `$(sel).val(v)` → `.value = v` |
| `browser-check.js` | **Removed** | `$(function(){})` → IIFE; `.show()` → `.style.display = 'block'`; `.append()` → `insertAdjacentHTML`; `.removeAttr()` → `removeAttribute` |
| `webcam-calibration.js` | **Removed** | `$.ajaxSetup` + `Cookies` removed; `$.ajax` → `fetch`; `.data()` → `.dataset`; `.one()` → `addEventListener({once:true})`; `.modal()` → `bootstrap.Modal.getOrCreateInstance()` |
| `experiment.js` | **Removed** | `$.ajaxSetup` + `Cookies` removed; `$.ajax` → `fetch` + `URLSearchParams`; `$.get` → `fetch`; all DOM jQuery → native; stored handler refs for `removeEventListener` |

## Test Infrastructure Change

**Before**: `vm.runInNewContext` + jQuery mock objects. Tests tracked DOM state via custom mock records (e.g. `classOps`, `clickHandlers`, `domState`).

**After**: jsdom environment (`vitest.config.js: environment: 'jsdom'`). Tests set `document.body.innerHTML`, assign globals via `globalThis`, then `eval(readFileSync(SRC, 'utf8'))`. Assertions use real DOM APIs (`classList.contains`, `style.display`, `innerHTML`, etc.).

**Pattern used in migrated tests**:
```js
beforeEach(() => {
    document.body.innerHTML = `<div id="...">...</div>`
    globalThis.getCsrfToken = vi.fn().mockReturnValue('test-csrf')
    eval(readFileSync(SRC, 'utf8'))
})
```

## What Was NOT Changed

`tests/js/helpers/load-script.js` **was kept**. Three test files still depend on it for legitimate reasons unrelated to jQuery:

| Test | Why loadScript stays |
|---|---|
| `queue.test.js` | Extracts `Queue` class from `queue.src.js` — `var`/function exports visible in VM context |
| `webcam.test.js` | Extracts `let webcam` from `webcam.js` via `capture` parameter |
| `webgazer_calculations.test.js` | Extracts 4 `let`-declared functions from `webgazer-calibration.js` |

`eval` in jsdom cannot expose `let`-declared variables to the test scope (strict-mode eval scopes them locally). These files belong in Phase 3 when ES modules are added — `import` will replace `loadScript` entirely.

## Known Caveats Discovered

**`dataset` returns strings; jQuery `.data()` did type coercion.** Boolean attributes (e.g. `data-include-pause-page`) now require explicit conversion: `config.includePausePage?.toLowerCase() === 'true'`. Applied in `webcam-calibration.js` and `experiment.js`.

**Disabled buttons don't fire click events in jsdom.** The `#fullscreen-button` in `experiment.test.js` must NOT have the `disabled` attribute in the test HTML, otherwise `button.click()` is silently ignored. The production `load` event (which removes `disabled`) doesn't fire in test context.

**`fetch` in `postResult` (experiment.js) now sends `URLSearchParams` body** with `Content-Type: application/x-www-form-urlencoded`, matching jQuery's default POST encoding. The response is expected to return `{ resultId: ... }` (camelCase) — the original test used `{ result_id: ... }` (snake\_case) which was inconsistent; updated to `{ resultId: 42 }` in the test mock.

**`bootstrap.Modal.getOrCreateInstance(el).hide()`** is called in `checkStepFour` (`webcam-calibration.js`) for the repeat modal — tests must provide this on `globalThis.bootstrap`.

## Phase 3 Scope

ES module migration across all 7 browser-side JS files:

1. Add `export` to each file's public API (or assign to `window` for backward compatibility)
2. Change `<script src="...">` → `<script type="module" src="...">` in Django templates
3. Replace global dependencies (`getCsrfToken`, `webcam`, `webgazer`) with `import` statements
4. Update `vitest.config.js` (remove environment override — Vitest handles ESM natively)
5. Replace `loadScript` / `eval` test patterns with `import()` — this finally deletes `load-script.js`

## E2e Testing Recommendation

Add Playwright in Phase 3 or Phase 4 (depending on scope). Priority flows to cover:

1. **Webcam calibration flow** (steps 1–4, VID and AUD modes) — most complex UI, multiple async steps
2. **Trial run progression** (fullscreen → trials → thankyou redirect) — core experiment path
3. **End page approve/disapprove** — simple but important for researcher workflow
4. **CDI assessment** — involves the catsim/IRT backend, worth e2e coverage

Playwright tests should run inside Docker (or against a live dev server) to cover the Django template rendering, CSRF, and media upload paths that unit tests cannot reach.

## All Tests Passing

62/62 tests pass on branch `refactor-js` after Phase 2.
