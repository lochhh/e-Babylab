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
