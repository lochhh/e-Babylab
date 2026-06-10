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
