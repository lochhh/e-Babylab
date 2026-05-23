import { describe, it, expect, beforeEach } from 'vitest'
import { init } from '../../src/experiments/static/experiments/js/endpage.js'

describe('endpage.js', () => {
  beforeEach(() => {
    document.body.innerHTML = `
      <div id="end_page_step_1" class="active">
        <button class="btn-primary">Approve</button>
        <button class="btn-danger">Disapprove</button>
      </div>
      <div id="end_page_approve"></div>
      <div id="end_page_disapprove"></div>
    `
    init()
  })

  it('approve click removes active from step_1', () => {
    document.querySelector('#end_page_step_1 button.btn-primary').click()
    expect(document.getElementById('end_page_step_1').classList.contains('active')).toBe(false)
  })

  it('approve click adds active to approve div', () => {
    document.querySelector('#end_page_step_1 button.btn-primary').click()
    expect(document.getElementById('end_page_approve').classList.contains('active')).toBe(true)
  })

  it('approve click does not touch disapprove div', () => {
    document.querySelector('#end_page_step_1 button.btn-primary').click()
    expect(document.getElementById('end_page_disapprove').classList.contains('active')).toBe(false)
  })

  it('disapprove click removes active from step_1', () => {
    document.querySelector('#end_page_step_1 button.btn-danger').click()
    expect(document.getElementById('end_page_step_1').classList.contains('active')).toBe(false)
  })

  it('disapprove click adds active to disapprove div', () => {
    document.querySelector('#end_page_step_1 button.btn-danger').click()
    expect(document.getElementById('end_page_disapprove').classList.contains('active')).toBe(true)
  })

  it('disapprove click does not touch approve div', () => {
    document.querySelector('#end_page_step_1 button.btn-danger').click()
    expect(document.getElementById('end_page_approve').classList.contains('active')).toBe(false)
  })
})
