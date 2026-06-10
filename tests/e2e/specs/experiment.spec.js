import { exec } from 'child_process'
import { dirname, resolve } from 'path'
import { promisify } from 'util'
import { fileURLToPath } from 'url'
import { expect, test } from '@playwright/test'
import { stubBrowserAPIs } from '../helpers.js'

const execAsync = promisify(exec)
const __dirname = dirname(fileURLToPath(import.meta.url))
const ROOT = resolve(__dirname, '../../..')
const SUBJECT_NON = 'b0e2e000-0000-0000-0000-000000000001'

// Serial: tests share SubjectData state — completed trials are excluded from the list,
// so running these concurrently would cause race conditions in trial availability.
test.describe.configure({ mode: 'serial' })

test.beforeEach(async ({ page }) => {
  // Reset TrialResults before each test so every test in every browser project
  // sees a fresh trial list. Multiple projects share SUBJECT_NON and run
  // concurrently; a faster project's test3 can mark the trial done before a
  // slower project's test2 starts.
  await execAsync(
    `docker compose -f docker-compose.dev.yml exec -T web uv run python manage.py shell -c "from experiments.models import TrialResult; TrialResult.objects.filter(subject_id='${SUBJECT_NON}').delete()"`,
    { cwd: ROOT },
  )
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
