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

test('demographic form submits after solving the CAPTCHA', async ({ page }) => {
  const errors = []
  page.on('pageerror', e => errors.push(e.message))
  await page.goto(`/${EXP_NON}/form/`)
  await page.waitForLoadState('networkidle')

  const provider = await page.getAttribute('#subjectForm', 'data-captcha-provider')
  test.skip(
    provider !== 'altcha' && provider !== '',
    `${provider} requires real third-party test credentials, not covered here`,
  )

  // Wait for resolution.js to fill these asynchronously; the form is
  // required-field-invalid (and never reaches CAPTCHA verification) if
  // submitted before it runs.
  await expect(page.locator('input[name="resolution_w"]')).not.toHaveValue('')
  await page.click('button[type="submit"]')
  await page.waitForURL(url => !url.pathname.endsWith('/form/'), { timeout: 15000 })
  expect(errors, `JS errors: ${errors.join('; ')}`).toHaveLength(0)
})

test('demographic form rejects a tampered CAPTCHA solution', async ({ page }) => {
  test.setTimeout(45000)
  await page.goto(`/${EXP_NON}/form/`)
  await page.waitForLoadState('networkidle')

  const provider = await page.getAttribute('#subjectForm', 'data-captcha-provider')
  test.skip(provider !== 'altcha', `${provider} not covered here`)

  await page.route('**/captcha/challenge', async route => {
    const response = await route.fetch()
    const json = await response.json()
    // Flip one hex digit rather than prepending text: this keeps the
    // signature's format/length valid so the widget still submits it,
    // exercising the server's HMAC check
    const last = json.signature.at(-1)
    json.signature = json.signature.slice(0, -1) + (last === '0' ? '1' : '0')
    await route.fulfill({ response, json })
  })

  await expect(page.locator('input[name="resolution_w"]')).not.toHaveValue('')
  const [response] = await Promise.all([
    // networkidle can settle during the widget's PBKDF2 solve (pure CPU, no
    // network activity) before the POST actually fires, so wait for the
    // response itself rather than an idle heuristic. The real proof-of-work
    // solve time is variable, so give it a generous budget.
    page.waitForResponse(r => r.url().endsWith('/form/submit'), { timeout: 30000 }),
    page.click('button[type="submit"]'),
  ])
  expect(response.status()).toBe(200)
  // subject_form_submit re-renders the form template in place on failure —
  // there's no redirect back to /form/, so the URL stays at /form/submit.
  await expect(page).toHaveURL(/\/form\/submit$/)
  await expect(page.locator('.alert-danger')).toContainText('Security check failed')
})
