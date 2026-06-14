import { describe, it, expect, beforeEach } from 'vitest'
import { init } from '../../src/experiments/static/experiments/js/endpage.js'

describe('endpage.js', () => {
  beforeEach(() => {
    document.body.innerHTML = `
      <div id="end_page_step_1">
        <button class="btn-primary">Approve</button>
        <button class="btn-danger">Disapprove</button>
      </div>
      <div id="end_page_approve" style="display:none"></div>
      <div id="end_page_disapprove" style="display:none"></div>
    `
    init()
  })

  it('approve click hides step_1', () => {
    document.querySelector('#end_page_step_1 button.btn-primary').click()
    expect(document.getElementById('end_page_step_1').style.display).toBe('none')
  })

  it('approve click shows approve div', () => {
    document.querySelector('#end_page_step_1 button.btn-primary').click()
    expect(document.getElementById('end_page_approve').style.display).toBe('block')
  })

  it('approve click does not show disapprove div', () => {
    document.querySelector('#end_page_step_1 button.btn-primary').click()
    expect(document.getElementById('end_page_disapprove').style.display).toBe('none')
  })

  it('disapprove click hides step_1', () => {
    document.querySelector('#end_page_step_1 button.btn-danger').click()
    expect(document.getElementById('end_page_step_1').style.display).toBe('none')
  })

  it('disapprove click shows disapprove div', () => {
    document.querySelector('#end_page_step_1 button.btn-danger').click()
    expect(document.getElementById('end_page_disapprove').style.display).toBe('block')
  })

  it('disapprove click does not show approve div', () => {
    document.querySelector('#end_page_step_1 button.btn-danger').click()
    expect(document.getElementById('end_page_approve').style.display).toBe('none')
  })
})
