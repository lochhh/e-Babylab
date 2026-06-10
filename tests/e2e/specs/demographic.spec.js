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
