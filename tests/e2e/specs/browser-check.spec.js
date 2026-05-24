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
