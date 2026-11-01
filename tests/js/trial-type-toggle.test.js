import { beforeEach, describe, expect, it } from 'vitest'
import { init, sync } from '../../src/experiments/static/experiments/js/admin/trial-type-toggle.js'

const inline = (i, type, { dwell = true, calibration = true } = {}) => `
  <div class="inline-related" id="trialitem_set${i}">
    <select name="trialitem_set-${i}-trial_type">
      <option value="REG" ${type === 'REG' ? 'selected' : ''}>Regular</option>
      <option value="CAL" ${type === 'CAL' ? 'selected' : ''}>Calibration</option>
      <option value="AG" ${type === 'AG' ? 'selected' : ''}>Attention getter</option>
    </select>
    ${calibration ? `<fieldset class="grp-module eye-calibration">
      <textarea name="trialitem_set-${i}-calibration_points">[[10,50]]</textarea>
    </fieldset>` : ''}
    ${dwell ? `<fieldset class="grp-module dwell-check">
      <input name="trialitem_set-${i}-min_dwell_time" value="500">
      <select name="trialitem_set-${i}-dwell_target_type">
        <option value="ANY">Any</option><option value="CELL" selected>Cell</option>
      </select>
      <input name="trialitem_set-${i}-dwell_target_row" value="1">
      <select name="trialitem_set-${i}-attention_getter">
        <option value="">---</option><option value="7" selected>AG</option>
      </select>
    </fieldset>` : ''}
  </div>`

const section = (i, cls) => document.querySelector(`#trialitem_set${i} fieldset.${cls}`)
const field = (i, name) => document.querySelector(`[name="trialitem_set-${i}-${name}"]`)
const choose = (i, type) => {
  const select = field(i, 'trial_type')
  select.value = type
  select.dispatchEvent(new Event('change', { bubbles: true }))
}
const dwellValues = i =>
  ['min_dwell_time', 'dwell_target_type', 'dwell_target_row', 'attention_getter'].map(n => field(i, n).value)
const ORIGINAL = ['500', 'CELL', '1', '7']

describe('trial-type-toggle.js', () => {
  beforeEach(() => { document.body.innerHTML = '' })

  it.each([
    ['REG', '', 'none'],
    ['CAL', 'none', ''],
    ['AG', 'none', 'none'],
  ])('applies %s on init without touching values', (type, dwellDisplay, calDisplay) => {
    document.body.innerHTML = inline(0, type)
    init()
    expect(section(0, 'dwell-check').style.display).toBe(dwellDisplay)
    expect(section(0, 'eye-calibration').style.display).toBe(calDisplay)
    expect(dwellValues(0)).toEqual(ORIGINAL)
  })

  it('never clears calibration points', () => {
    document.body.innerHTML = inline(0, 'REG')
    init()
    choose(0, 'AG')
    choose(0, 'CAL')
    expect(field(0, 'calibration_points').value).toBe('[[10,50]]')
  })

  it('keeps dwell values when switching REG -> AG -> REG', () => {
    document.body.innerHTML = inline(0, 'REG')
    init()
    choose(0, 'AG')
    expect(dwellValues(0)).toEqual(ORIGINAL)
    choose(0, 'REG')
    expect(dwellValues(0)).toEqual(ORIGINAL)
  })

  it('reacts to changes and restores the dwell check for REG', () => {
    document.body.innerHTML = inline(0, 'REG')
    init()
    choose(0, 'AG')
    expect(section(0, 'dwell-check').style.display).toBe('none')
    choose(0, 'REG')
    expect(section(0, 'dwell-check').style.display).toBe('')
    expect(section(0, 'eye-calibration').style.display).toBe('none')
  })

  it('handles inline rows added after init', () => {
    document.body.innerHTML = inline(0, 'REG')
    init()
    document.body.insertAdjacentHTML('beforeend', inline(1, 'REG'))
    choose(1, 'CAL')
    expect(section(1, 'dwell-check').style.display).toBe('none')
    expect(section(1, 'eye-calibration').style.display).toBe('')
  })

  it('works before Grappelli adds grp-dynamic-form to the rows', () => {
    document.body.innerHTML = inline(0, 'AG')
    expect(document.querySelector('.grp-dynamic-form')).toBeNull()
    init()
    expect(section(0, 'dwell-check').style.display).toBe('none')
  })

  it('is a no-op when the sections are absent', () => {
    document.body.innerHTML = inline(0, 'AG', { dwell: false, calibration: false })
    expect(() => { init(); sync(field(0, 'trial_type')) }).not.toThrow()
  })
})
