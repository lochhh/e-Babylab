import { exec } from 'child_process'
import { dirname, resolve } from 'path'
import { promisify } from 'util'
import { fileURLToPath } from 'url'
import { expect, test } from '@playwright/test'
import { stubBrowserAPIs, stubWebgazerScript, proceedPastWebgazerInit } from '../helpers.js'

const execAsync = promisify(exec)
const __dirname = dirname(fileURLToPath(import.meta.url))
const ROOT = resolve(__dirname, '../../..')
const SUBJECT_ALL = 'b0e2e000-0000-0000-0000-000000000005'

test.describe.configure({ mode: 'serial' })

test.beforeEach(async ({ page }) => {
  await execAsync(
    `docker compose -f docker-compose.dev.yml exec -T web uv run python manage.py shell -c "from experiments.models import TrialResult; TrialResult.objects.filter(subject_id='${SUBJECT_ALL}').delete()"`,
    { cwd: ROOT },
  )
  await stubWebgazerScript(page)
  await page.addInitScript(stubBrowserAPIs)
})

test('ALL run page loads without JS errors', async ({ page }) => {
  const errors = []
  page.on('pageerror', e => errors.push(e.message))
  await page.goto(`/${SUBJECT_ALL}/run`)
  await page.waitForLoadState('networkidle')
  expect(errors, `JS errors: ${errors.join('; ')}`).toHaveLength(0)
})

test('ALL: trial renders and navigates to thankyou after webgazer-init', async ({ page }) => {
  await page.goto(`/${SUBJECT_ALL}/run`)
  await expect(page.locator('#fullscreen-button')).not.toBeDisabled({ timeout: 5000 })
  await page.locator('#fullscreen-button').click()
  await proceedPastWebgazerInit(page)
  await expect(page.locator('.trial-image')).toBeVisible({ timeout: 3000 })
  await page.waitForURL(`**/${SUBJECT_ALL}/run/thankyou`, { timeout: 10000 })
})
