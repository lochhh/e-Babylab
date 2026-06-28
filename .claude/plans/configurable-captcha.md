# Configurable CAPTCHA Providers

## Context

e-Babylab currently hardcodes Cloudflare Turnstile as its CAPTCHA provider. Turnstile is US-hosted and not necessarily GDPR-compliant, which is a problem for deploying at EU institutions. The goal is to make CAPTCHA configurable so deployers can choose the provider that fits their compliance requirements, or disable it entirely.

**Providers to support:** ALTCHA (default), Cloudflare Turnstile, TrustSig, none
**Default:** ALTCHA when no `CAPTCHA_PROVIDER` env var is set and no legacy Turnstile keys exist. Existing Turnstile deployments auto-detected via legacy `CLOUDFLARE_TURNSTILE_SECRET_KEY`.

## Architecture: Strategy Pattern

Single module `src/experiments/captcha.py` with an abstract base class, all 4 provider implementations, the factory function, and the ALTCHA challenge view. Each provider is ~30-40 lines — no need for a package with separate files.

### Provider interface

```python
class CaptchaProvider(ABC):
    def is_enabled(self) -> bool: ...
    def get_widget_html(self) -> str: ...       # HTML for the CAPTCHA widget
    def get_scripts_html(self) -> str: ...      # <script> tags (CDN + handler)
    def get_form_attrs(self) -> dict[str, str]: ... # data-* attrs for <form>
    def verify(self, request_post: dict) -> bool: ... # server-side verification
    def get_post_field_name(self) -> str: ...   # POST field name for token
```

### Factory

`get_captcha_provider()` reads `settings.CAPTCHA_PROVIDER`:
- If empty and `CLOUDFLARE_TURNSTILE_SECRET_KEY` exists -> `"turnstile"` (backward compat)
- If empty and no legacy keys -> `"altcha"` (new default)
- If explicit value -> use that provider
- Unknown value -> raise `ValueError` with valid choices

The `NoneProvider` is just 6 one-liner methods (returns `True`/`""`) — lives in the same file, no separate module needed.

### Provider details

**ALTCHA** (`AltchaProvider`):
- Uses `altcha` Python library (MIT, free) for HMAC-based verification — no Docker sidecar
- Needs a Django challenge endpoint view at `/captcha/challenge/` (also in `captcha.py`) that returns `altcha.create_challenge(hmac_key=settings.ALTCHA_HMAC_KEY)`
- JS widget from CDN: `https://cdn.jsdelivr.net/npm/altcha/dist/altcha.min.js`
- Env vars: `ALTCHA_HMAC_KEY` (generate with `openssl rand -hex 32`)

**Turnstile** (`TurnstileProvider`):
- Existing logic from `_verify_turnstile()` moved here
- `requests.post` to Cloudflare siteverify endpoint
- Env vars: `CLOUDFLARE_TURNSTILE_SITE_KEY`, `CLOUDFLARE_TURNSTILE_SECRET_KEY` (kept for backward compat)

**TrustSig** (`TrustSigProvider`):
- Invisible hardware-signal verification, EU-hosted (Germany)
- JS widget, server-side token verification via REST API
- Env vars: `TRUSTSIG_SITE_KEY`, `TRUSTSIG_SECRET_KEY`

**None** (`NoneProvider`):
- `verify()` always returns `True`, all HTML methods return `""`

## Key Change: Decouple CAPTCHA from Stored Templates

**Problem:** `Experiment.demographic_data_page_tpl` is an HTMLField stored per-experiment in the DB. Currently contains hardcoded Turnstile HTML. Switching providers would otherwise require a DB migration each time.

**Solution:** Replace provider-specific HTML with generic Django template variables (`{{ }}`):
- `{{captcha_form_attrs}}` — data attributes on `<form>` tag
- `{{captcha_widget}}` — the CAPTCHA widget HTML
- `{{captcha_scripts}}` — script tags (CDN + handler)

This uses the same Django template mechanism already in place (e.g. `{{turnstile_site_key}}`). The view passes these as context variables to `_render_tpl()`, which renders them via `Template(tpl_string).render(RequestContext(...))`. No Jinja2 or new templating — same system, just different variable names.

Switching providers then needs only an env var change — no DB migration.

**Note on `{% static %}` tags:** Provider `get_scripts_html()` methods must use `django.templatetags.static.static()` to resolve URLs in Python, not `{% static %}` template tags, because the HTML is injected as a context variable (not part of the template string) and template tags inside context variables are not rendered.

## Implementation Steps

### 1. Create `src/experiments/captcha.py`
Single module containing:
- `CaptchaProvider` abstract base class
- `TurnstileProvider`, `AltchaProvider`, `TrustSigProvider`, `NoneProvider` implementations
- `get_captcha_provider()` factory with registry
- `altcha_challenge_view()` for ALTCHA's challenge endpoint

### 2. Update settings (`src/config/settings.py`)
- Add `CAPTCHA_PROVIDER` env var
- Add `ALTCHA_HMAC_KEY`, `TRUSTSIG_SITE_KEY`, `TRUSTSIG_SECRET_KEY`
- Keep existing `CLOUDFLARE_TURNSTILE_*` vars for backward compat

### 3. Update template defaults (`src/experiments/template_defaults.py`)
Replace in `demographic_data_page_content`:
- `data-turnstile-site-key="{{turnstile_site_key}}"` -> `{{captcha_form_attrs}}`
- The `<div class="cf-turnstile ...">` widget div -> `{{captcha_widget}}`
- Turnstile CDN script tag -> remove (now in `{{captcha_scripts}}`)
- `turnstile-handler.js` script tag -> `{{captcha_scripts}}`

### 4. Data migration (0016) — update stored experiment templates
String replacement on `Experiment.demographic_data_page_tpl` (same pattern as migrations 0008, 0011):
- Replace Turnstile-specific HTML with generic `{{captcha_*}}` placeholders
- Reversible — reverse migration restores Turnstile HTML
- Log warning for experiments where Turnstile HTML detected but replacement didn't match (customized templates)

### 5. AlterField migration (0017) — update model field default
Run `makemigrations` to capture the updated `default=demographic_data_page_content` on the field.

### 6. Update views (`src/experiments/views.py`)
- Remove `_verify_turnstile()` function
- Remove `import requests` (each provider handles its own HTTP)
- Add `_captcha_context()` helper that calls `get_captcha_provider()` and returns dict with `captcha_form_attrs`, `captcha_widget`, `captcha_scripts` (all `mark_safe`)
- `subject_form()`: replace `turnstile_site_key` context with `**_captcha_context()`
- `subject_form_submit()`: replace `_verify_turnstile(...)` with `provider.verify(request.POST)`

### 7. Add ALTCHA challenge URL (`src/experiments/urls.py`)
- Add `re_path(r"^captcha/challenge$", altcha_challenge_view, name="captchaChallenge")` (imported from `experiments.captcha`)

### 8. Rename and rewrite JS handler
- Rename `turnstile-handler.js` -> `captcha-handler.js`
- Read `data-captcha-provider` from form to dispatch:
  - `turnstile` -> `turnstile.execute()`
  - `trustsig` -> TrustSig widget execution
  - `altcha` -> ALTCHA widget handles it automatically
  - no provider -> direct submit

### 9. Update CSS (`src/experiments/static/experiments/css/trials.css`)
- Rename `.turnstile-badge` -> `.captcha-badge`

### 10. Update dependencies (`pyproject.toml`)
- Add `"altcha"` to dependencies

### 11. Update `.env.template`
Document all provider options with comments explaining each.

### 12. Update docs (`docs/getting-started/index.md`)
Add CAPTCHA configuration section explaining **why CAPTCHA matters** (bot prevention for data quality in research studies — without it, automated submissions can pollute participant data and waste researcher time reviewing fake responses) and a comparison table:

| | ALTCHA (default) | Turnstile | TrustSig | None |
|---|---|---|---|---|
| **Compliance** | Universal (self-hosted, no data leaves your server) | US-based | EU-based (Germany) | N/A |
| **User friction** | Invisible (proof-of-work) | Low (checkbox) | Invisible (hardware signals) | None |
| **Third-party data** | None | Cloudflare (US) | TrustSig (EU) | None |
| **Cookies** | Zero | Some | Zero | None |
| **Cost** | [Free forever (MIT)](https://altcha.org/) | [Free](https://www.cloudflare.com/en-gb/products/turnstile/) | [Free 50k/mo, then from 9 EUR/mo](https://trustsig.eu/#pricing) | Free |
| **Best for** | GDPR/privacy-first deployments | Zero server maintenance, easy setup, battle-tested | EU institutions wanting invisible protection | Dev/testing only |

Include guidance: "We recommend keeping CAPTCHA enabled in production. Disabling it (`CAPTCHA_PROVIDER=none`) is suitable for development and testing but leaves your study open to automated submissions in production."

### 13. Write tests

**New `tests/test_unit/test_captcha.py`:**
- Factory tests: correct provider returned for each `CAPTCHA_PROVIDER` value
- Auto-detection: legacy Turnstile keys -> turnstile, no keys -> altcha
- Unknown provider -> `ValueError`
- Each provider: `verify()` success/failure/disabled, `get_widget_html()`, `get_scripts_html()`
- `_captcha_context()` helper returns correct template vars
- ALTCHA challenge view returns valid JSON

**Update existing tests:**
- `tests/test_unit/test_views.py`: mock target changes from `experiments.views.requests.post` to `experiments.captcha.requests.post`
- `tests/test_integration/test_views.py`: same mock target update
- Add migration test verifying string replacements work on sample templates

**New `tests/js/captcha-handler.test.js`:**
- Generic handler dispatches correctly per provider

### 14. Delete old file
- Remove `src/experiments/static/experiments/js/turnstile-handler.js` after creating `captcha-handler.js`
- Remove `src/static/experiments/js/turnstile-handler.js` (collected static copy) if it exists

## Verification

1. Run pytest inside container — all existing + new tests pass
2. Run JS tests (`npm test` in `tests/`)
3. Manual test with `CAPTCHA_PROVIDER=altcha` + generated HMAC key — participant form shows ALTCHA widget, form submission works
4. Manual test with `CAPTCHA_PROVIDER=none` — no widget, form submits directly
5. Manual test with legacy `CLOUDFLARE_TURNSTILE_SECRET_KEY` set, no `CAPTCHA_PROVIDER` — auto-detects turnstile, backward compat works
6. Verify migration forward/reverse on test DB

## Files to modify
- `src/experiments/captcha.py` — new single module (all providers + factory + ALTCHA challenge view)
- `src/config/settings.py` — add env vars
- `src/experiments/views.py` — refactor to use provider
- `src/experiments/template_defaults.py` — generic placeholders
- `src/experiments/urls.py` — ALTCHA challenge endpoint
- `src/experiments/static/experiments/js/captcha-handler.js` — new (replaces turnstile-handler.js)
- `src/experiments/static/experiments/css/trials.css` — rename class
- `src/experiments/migrations/0016_*.py` — data migration
- `src/experiments/migrations/0017_*.py` — field default update
- `pyproject.toml` — add altcha dependency
- `.env.template` — document all options
- `docs/getting-started/index.md` — comparison table + setup guide
- `tests/test_unit/test_captcha.py` — new
- `tests/test_unit/test_views.py` — update mock targets
- `tests/test_integration/test_views.py` — update mock targets
- `tests/js/captcha-handler.test.js` — new
