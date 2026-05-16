import { describe, it, expect, beforeEach } from 'vitest'
import { resolve, dirname } from 'path'
import { fileURLToPath } from 'url'
import { loadScript } from './helpers/load-script.js'

const __dirname = dirname(fileURLToPath(import.meta.url))
const SRC = resolve(__dirname, '../../src/experiments/static/experiments/js/endpage.js')

describe('endpage.js', () => {
  let clickHandlers, classOps

  beforeEach(() => {
    clickHandlers = {}
    classOps = {}
    const jq = (sel) => ({
      click:       (fn)  => { clickHandlers[sel] = fn },
      removeClass: (cls) => { classOps[`remove|${sel}|${cls}`] = true },
      addClass:    (cls) => { classOps[`add|${sel}|${cls}`]    = true },
    })
    loadScript(SRC, [], { $: (sel) => jq(sel) })
  })

  it('approve click removes active from step_1', () => {
    clickHandlers['#end_page_step_1 button.btn-primary']()
    expect(classOps['remove|#end_page_step_1|active']).toBe(true)
  })

  it('approve click adds active to approve div', () => {
    clickHandlers['#end_page_step_1 button.btn-primary']()
    expect(classOps['add|#end_page_approve|active']).toBe(true)
  })

  it('approve click does not touch disapprove div', () => {
    clickHandlers['#end_page_step_1 button.btn-primary']()
    expect(classOps['add|#end_page_disapprove|active']).toBeUndefined()
  })

  it('disapprove click removes active from step_1', () => {
    clickHandlers['#end_page_step_1 button.btn-danger']()
    expect(classOps['remove|#end_page_step_1|active']).toBe(true)
  })

  it('disapprove click adds active to disapprove div', () => {
    clickHandlers['#end_page_step_1 button.btn-danger']()
    expect(classOps['add|#end_page_disapprove|active']).toBe(true)
  })

  it('disapprove click does not touch approve div', () => {
    clickHandlers['#end_page_step_1 button.btn-danger']()
    expect(classOps['add|#end_page_approve|active']).toBeUndefined()
  })
})
