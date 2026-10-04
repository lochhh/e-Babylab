import { beforeEach, describe, expect, it, vi } from 'vitest'
import { init } from '../../src/experiments/static/experiments/js/admin/recording-option-confirm.js'

const page = (initial, counts) => `
  <form id="f"><select name="recording_option" data-initial="${initial}" data-eye-values="EYE,ALL"
    data-dwell-count="${counts[0]}" data-attention-getter-count="${counts[1]}" data-calibration-count="${counts[2]}">
    <option value="NON">None</option><option value="AUD">Audio</option>
    <option value="EYE">Eye</option><option value="ALL">All</option>
  </select></form>`

const submit = () => {
  const event = new Event('submit', { cancelable: true, bubbles: true })
  document.getElementById('f').dispatchEvent(event)
  return event
}
const setup = (initial, value, counts = [3, 2, 1]) => {
  document.body.innerHTML = page(initial, counts)
  document.querySelector('select').value = value
  init()
}

describe('recording-option-confirm.js', () => {
  beforeEach(() => {
    document.body.innerHTML = ''
    vi.restoreAllMocks()
  })

  it.each([
    ['singulars', [1, 4, 1], 'clear gaze dwell time checks on 1 trial and reset 4 attention getters and 1 calibration trial to Regular'],
    ['no calibration', [3, 2, 0], 'clear gaze dwell time checks on 3 trials and reset 2 attention getters to Regular'],
    ['only calibration', [0, 0, 2], 'reset 2 calibration trials to Regular'],
  ])('asks on eye to non-eye, cancel blocks the submit: %s', (_id, counts, text) => {
    const confirm = vi.spyOn(window, 'confirm').mockReturnValue(false)
    setup('EYE', 'AUD', counts)
    expect(submit().defaultPrevented).toBe(true)
    expect(confirm).toHaveBeenCalledWith(
      `Changing the recording option to one without eye-tracking will ${text}. This cannot be undone. Continue?`)
  })

  it('lets the submit through when confirmed', () => {
    vi.spyOn(window, 'confirm').mockReturnValue(true)
    setup('ALL', 'NON')
    expect(submit().defaultPrevented).toBe(false)
  })

  it.each([
    ['eye-to-all', 'EYE', 'ALL', [3, 2, 1]],
    ['none-to-eye', 'NON', 'EYE', [3, 2, 1]],
    ['audio-to-none', 'AUD', 'NON', [3, 2, 1]],
    ['unchanged', 'EYE', 'EYE', [3, 2, 1]],
    ['zero-counts', 'EYE', 'NON', [0, 0, 0]],
  ])('no dialog: %s', (_id, initial, value, counts) => {
    const confirm = vi.spyOn(window, 'confirm').mockReturnValue(false)
    setup(initial, value, counts)
    expect(submit().defaultPrevented).toBe(false)
    expect(confirm).not.toHaveBeenCalled()
  })
})
