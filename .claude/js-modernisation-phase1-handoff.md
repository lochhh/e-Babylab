# JS Modernisation Handoff

## What Phase 1 Completed

Syntax modernisation across all 7 browser-side JS files. jQuery fully removed from two files; kept in five where tests assert jQuery mock state.

| File | jQuery | Changes |
|---|---|---|
| `utils.js` | None (new file) | `getCsrfToken()` global utility; loaded before other scripts in base.html |
| `webcam.js` | **Removed** | `$.ajax` → `fetch` + `getCsrfToken()`; `$.ajaxSetup` removed; `formatNumber` → `padStart`; `const`/`let`; arrow fns; template literals |
| `webgazer-calibration.js` | **Removed** | All jQuery → native DOM; `const`/`let`; arrow fns; template literals; `$(window).height()` → `window.innerHeight` |
| `browser-check.js` | Kept | `const`/`let`; arrow fn; `!= null` check |
| `endpage.js` | Kept | `const`; arrow fns; `'use strict'` added |
| `resolution.js` | Kept | No material changes (file was already minimal) |
| `webcam-calibration.js` | Kept | `const`/`let`; arrow fns; template literals; optional chaining (`mediaRecorder?.state`); nullish coalescing for fallback string |
| `experiment.js` | Kept | `const`/`let`; template literals for all URL/filename strings; arrow fns in safe callbacks; fullscreen vendor-prefix chains → optional chaining; `exitModal?.show()` |

## Why jQuery Remains in 5 Files

Tests for browser-check, endpage, resolution, webcam-calibration, and experiment load each script in isolation via a Node VM (`loadScript` + `runInNewContext`). They inject a mock `$` function and assert outcomes via that mock — e.g.:

```javascript
// Test injects:
const $ = sel => ({ show: () => { dom[sel] = { shown: true } }, ... })

// Test asserts:
expect(dom['#webcam_step_1 .alert-success'].shown).toBe(true)
```

Removing jQuery from those files would make those assertions fail. Phase 2 must update both source and test infrastructure simultaneously.

## Phase 2 Prerequisites

**Test infrastructure must be rewritten before jQuery can be removed from the remaining 5 files.**

The current `tests/js/helpers/load-script.js` uses `vm.runInNewContext` — incompatible with ES module syntax and requires jQuery mocks to test DOM outcomes. Replace with:

1. Update `tests/js/vitest.config.js`: change `environment: 'node'` → `environment: 'jsdom'`
2. Rewrite test files to use real `document` instead of jQuery mocks
3. Use `vi.mock()` or Vitest's built-in module mocking for external deps (webgazer, Cookies)
4. Delete `tests/js/helpers/load-script.js`

## Phase 2 Order of Work

Work from simplest to most complex:

1. **endpage.js** (trivial — 13 LOC, 2 click handlers)
   - Replace `$(...).click(fn)` with `document.querySelector(...).addEventListener('click', fn)`
   - Replace `.addClass()/.removeClass()` with `.classList.add()/.remove()`
   - Test: jsdom, assert classList state

2. **resolution.js** (trivial — 6 LOC)
   - Replace `$("input[name='resolution_w']").val(v)` with `document.querySelector(...).value = v`
   - Test: jsdom, assert `.value`

3. **browser-check.js** (easy — 29 LOC)
   - Replace `$(...).show()` with `el.style.display = 'block'`
   - Replace `.append(html)` with `el.insertAdjacentHTML('beforeend', html)`
   - Replace `.removeAttr('disabled')` with `el.removeAttribute('disabled')`
   - Test: jsdom, assert element properties

4. **webcam-calibration.js** (moderate — 210 LOC)
   - Remove `$.ajaxSetup` + `Cookies` → use `getCsrfToken()` from utils.js
   - Replace `$.ajax` → `fetch`
   - Replace all jQuery DOM calls → native DOM
   - Test: jsdom with `navigator.mediaDevices` mock

5. **experiment.js** (large — 678 LOC, most complex)
   - Replace `$.ajax(storeresult).done().fail()` → `fetch` (requires test mock rewrite)
   - Replace `$.get(error)` → `fetch`
   - Replace `$.ajaxSetup` + `Cookies` → `getCsrfToken()`
   - Replace remaining jQuery DOM calls
   - Remove `$(audio).on('canplay')` / `$(video).on('canplay')` / `$(video).on('ended')` — store handler refs for `removeEventListener`
   - Test: most involved — needs jsdom + careful async test rewrite

## Converting a Test from jQuery Mock to jsdom

Before (current VM-based approach for endpage.js):
```javascript
function run() {
    const classOps = {}
    const clickHandlers = {}
    const jq = sel => ({
        click: fn => { clickHandlers[sel] = fn },
        addClass: cls => { classOps[`add|${sel}|${cls}`] = true },
        removeClass: cls => { classOps[`remove|${sel}|${cls}`] = true },
    })
    loadScript(SRC, [], { $: sel => jq(sel) })
    return { classOps, clickHandlers }
}

it('approve click adds active to approve div', () => {
    const { clickHandlers, classOps } = run()
    clickHandlers['#end_page_step_1 button.btn-primary']()
    expect(classOps['add|#end_page_approve|active']).toBe(true)
})
```

After (jsdom approach):
```javascript
// vitest.config.js: environment: 'jsdom'
import { readFileSync } from 'fs'

beforeEach(() => {
    document.body.innerHTML = `
        <div id="end_page_step_1">
            <button class="btn-primary">Approve</button>
            <button class="btn-danger">Disapprove</button>
        </div>
        <div id="end_page_approve"></div>
        <div id="end_page_disapprove"></div>
    `
    // Script uses global $; provide jQuery from a CDN or npm package, or use vi.mock
    eval(readFileSync(SRC, 'utf8'))
})

it('approve click adds active to approve div', () => {
    document.querySelector('#end_page_step_1 button.btn-primary').click()
    expect(document.getElementById('end_page_approve').classList.contains('active')).toBe(true)
})
```

## Enabling ES Modules (Phase 2 final step)

Once all jQuery is removed and tests use jsdom:

1. Add `export` to each file's public API (or use an IIFE that assigns to `window` for backward compatibility)
2. Change `<script src="...">` → `<script type="module" src="...">`
3. Replace global dependencies with `import` statements
4. Update `vitest.config.js` to remove `environment` override (Vitest handles ESM natively)
5. Replace `loadScript` / `eval` test patterns with `import()`

## Known Fragility After Phase 1

**webcam.js fetch() is not mocked in tests.** The upload path is never triggered in any current test because `stopUploading()` always cancels the pending `setTimeout` before `uploadChunk()` fires. If upload-path tests are added in Phase 2, inject:

```javascript
// In test globals:
document: { cookie: 'csrftoken=test-csrf' }
// And mock fetch:
global.fetch = vi.fn().mockResolvedValue({ ok: true, json: () => Promise.resolve({}) })
```

**`$.ajaxSetup`'s `beforeSend` must stay `function`** (not arrow) because it uses `this.crossDomain`. This constraint disappears in Phase 2 when `$.ajax` is replaced with `fetch` and `$.ajaxSetup` is removed entirely from experiment.js.
