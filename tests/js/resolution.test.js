import { describe, it, expect } from 'vitest'
import { setResolution } from '../../src/experiments/static/experiments/js/resolution.js'

describe('resolution.js', () => {
  function run(width, height) {
    document.body.innerHTML = `
      <input name="resolution_w" />
      <input name="resolution_h" />
    `
    Object.defineProperty(window, 'screen', {
      value: { width, height },
      writable: true,
      configurable: true,
    })
    setResolution()
    return {
      w: document.querySelector("input[name='resolution_w']").value,
      h: document.querySelector("input[name='resolution_h']").value,
    }
  }

  it('sets resolution_w input to screen.width', () => {
    expect(run(1920, 1080).w).toBe('1920')
  })

  it('sets resolution_h input to screen.height', () => {
    expect(run(1920, 1080).h).toBe('1080')
  })

  it('uses exact pixel values for non-standard resolution', () => {
    const { w, h } = run(800, 600)
    expect(w).toBe('800')
    expect(h).toBe('600')
  })

  it('does not throw when inputs are absent', () => {
    document.body.innerHTML = ''
    expect(() => setResolution()).not.toThrow()
  })
})
