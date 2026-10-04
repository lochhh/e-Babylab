import { beforeEach, describe, expect, it } from 'vitest'
import { init, sync } from '../../src/experiments/static/experiments/js/admin/attention-getter-toggle.js'

const inline = (i, flagged) => `
  <div class="grp-dynamic-form" id="trialitem_set${i}">
    <input type="checkbox" name="trialitem_set-${i}-is_attention_getter" ${flagged ? 'checked' : ''}>
    <fieldset class="grp-module dwell-check">
      <input name="trialitem_set-${i}-min_dwell_time" value="500">
      <select name="trialitem_set-${i}-dwell_target_type">
        <option value="ANY">Any</option><option value="CELL" selected>Cell</option>
      </select>
      <input name="trialitem_set-${i}-dwell_target_row" value="1">
      <select name="trialitem_set-${i}-attention_getter">
        <option value="">---</option><option value="7" selected>AG</option>
      </select>
    </fieldset>
  </div>`

const fieldset = i => document.querySelector(`#trialitem_set${i} fieldset.dwell-check`)
const field = (i, name) => document.querySelector(`[name="trialitem_set-${i}-${name}"]`)

describe('attention-getter-toggle.js', () => {
  beforeEach(() => { document.body.innerHTML = inline(0, false) + inline(1, true) })

  it('hides the dwell fieldset of already-flagged trials on init', () => {
    init()
    expect(fieldset(0).style.display).toBe('')
    expect(fieldset(1).style.display).toBe('none')
  })

  it('hides and clears the fieldset when a trial is flagged', () => {
    init()
    const box = field(0, 'is_attention_getter')
    box.checked = true
    box.dispatchEvent(new Event('change', { bubbles: true }))
    expect(fieldset(0).style.display).toBe('none')
    expect(field(0, 'min_dwell_time').value).toBe('')
    expect(field(0, 'dwell_target_type').value).toBe('ANY')
    expect(field(0, 'dwell_target_row').value).toBe('')
    expect(field(0, 'attention_getter').value).toBe('')
  })

  it('shows the fieldset again when unflagged', () => {
    const box = field(1, 'is_attention_getter')
    box.checked = false
    sync(box)
    expect(fieldset(1).style.display).toBe('')
  })

  it('handles inline rows added after init', () => {
    init()
    document.body.insertAdjacentHTML('beforeend', inline(2, false))
    const box = field(2, 'is_attention_getter')
    box.checked = true
    box.dispatchEvent(new Event('change', { bubbles: true }))
    expect(fieldset(2).style.display).toBe('none')
  })
})
