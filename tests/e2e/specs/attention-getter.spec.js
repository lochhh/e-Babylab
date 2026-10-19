import { exec } from 'child_process'
import { dirname, resolve } from 'path'
import { promisify } from 'util'
import { fileURLToPath } from 'url'
import { expect, test } from '@playwright/test'
import { stubBrowserAPIs, stubWebgazerScript, proceedPastWebgazerInit } from '../helpers.js'

const execAsync = promisify(exec)
const __dirname = dirname(fileURLToPath(import.meta.url))
const ROOT = resolve(__dirname, '../../..')
const EXP_AG = 'a0e2e000-0000-0000-0000-000000000006'

const manage = cmd => execAsync(
  `docker compose -f docker-compose.dev.yml exec -T web uv run python manage.py shell -c "${cmd}"`,
  { cwd: ROOT },
)

test.describe.configure({ mode: 'serial' })

test.describe('attention getter run', () => {
  // Projects run in parallel and the run is stateful, so each gets its own subject
  let subject
  test.beforeEach(async ({ page }, testInfo) => {
    const i = testInfo.config.projects.findIndex(p => p.name === testInfo.project.name)
    subject = `b0e2e000-0000-0000-0000-00000000010${i}`
    await manage(`from experiments.models import ListItem, SubjectData; SubjectData.objects.get_or_create(id='${subject}', defaults={'experiment_id': '${EXP_AG}', 'listitem': ListItem.objects.get(experiment_id='${EXP_AG}'), 'participant_id': 9100 + ${i}})`)
    await manage(`from experiments.models import TrialResult; TrialResult.objects.filter(subject_id='${subject}').delete()`)
    await stubWebgazerScript(page)
    await page.addInitScript(stubBrowserAPIs)
  })

  test('shows the attention getter after a failed dwell check, then finishes', async ({ page }) => {
    // The first trial is in the page payload, so the first nexttrial answer
    // is what follows it: the attention getter, then the remaining trial
    // Body is read inside the route, as the page leaves before a response handle could
    const labels = []
    await page.route('**/run/nexttrial', async route => {
      const response = await route.fetch()
      labels.push((await response.json()).trial?.label)
      await route.fulfill({ response })
    })
    await page.goto(`/${subject}/run`)
    await expect(page.locator('#fullscreen-button')).not.toBeDisabled({ timeout: 5000 })
    await page.locator('#fullscreen-button').click()
    await proceedPastWebgazerInit(page)
    await page.waitForURL(`**/${subject}/run/thankyou`, { timeout: 15000 })
    expect(labels.slice(0, 2)).toEqual(['e2e-ag', 'e2e-ag-after'])
  })
})

test.describe('admin trial inline', () => {
  test('shows the sections that suit the selected trial type', async ({ page }) => {
    const { stdout } = await manage(
      `from experiments.models import BlockItem; print(BlockItem.objects.get(label='e2e-ag-main', outerblockitem__listitem__experiment_id='${EXP_AG}').pk)`,
    )
    await page.goto('/admin/login/')
    await page.fill('#id_username', 'e2euser')
    await page.fill('#id_password', 'e2epass')
    await page.locator('input[type="submit"]').click()
    await page.waitForURL('**/admin/')
    const pk = stdout.trim().split('\n').pop() // last line: the shell prints import notices first
    await page.goto(`/admin/experiments/blockitem/${pk}/change/`)
    const row = page.locator('.inline-related').filter({
      has: page.locator('select[name="trialitem_set-0-trial_type"]'),
    })
    const type = row.locator('select[name="trialitem_set-0-trial_type"]')
    const dwell = row.locator('.dwell-check')
    const calibration = row.locator('.eye-calibration')

    await expect(dwell).toBeVisible()
    await expect(calibration).toBeHidden()
    await type.selectOption({ label: 'Attention getter' })
    await expect(dwell).toBeHidden()
    await expect(calibration).toBeHidden()
    await type.selectOption({ label: 'Eye-tracking calibration' })
    await expect(calibration).toBeVisible()
    await expect(dwell).toBeHidden()
    await type.selectOption({ label: 'Regular' })
    await expect(dwell).toBeVisible()
    await expect(calibration).toBeHidden()
  })
})
