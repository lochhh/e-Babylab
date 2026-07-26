import { describe, it, expect, vi, beforeEach } from 'vitest'

describe('captcha-handler.js', () => {
  beforeEach(() => {
    document.body.innerHTML = ''
    delete window.onCaptchaVerified
    delete window.turnstile
  })

  function loadHandler() {
    // Re-import fresh each time (vitest caches modules, so use dynamic import)
    vi.resetModules()
    return import('../../src/experiments/static/experiments/js/captcha-handler.js')
  }

  it('sets onCaptchaVerified on window', async () => {
    document.body.innerHTML = '<form id="subjectForm"></form>'
    await loadHandler()
    expect(typeof window.onCaptchaVerified).toBe('function')
  })

  it('intercepts form submit for turnstile provider', async () => {
    document.body.innerHTML =
      '<form id="subjectForm" data-captcha-provider="turnstile"><button type="submit">Go</button></form>'
    window.turnstile = { execute: vi.fn() }
    await loadHandler()

    const form = document.getElementById('subjectForm')
    const event = new Event('submit', { cancelable: true })
    form.dispatchEvent(event)

    expect(event.defaultPrevented).toBe(true)
    expect(window.turnstile.execute).toHaveBeenCalled()
  })

  it('does not intercept form submit for altcha provider', async () => {
    document.body.innerHTML =
      '<form id="subjectForm" data-captcha-provider="altcha"><button type="submit">Go</button></form>'
    await loadHandler()

    const form = document.getElementById('subjectForm')
    const submitSpy = vi.fn()
    form.addEventListener('submit', submitSpy)

    const event = new Event('submit', { cancelable: true })
    form.dispatchEvent(event)
    // Should not prevent default — altcha widget handles submission
    expect(event.defaultPrevented).toBe(false)
  })

  it('does not intercept form submit for trustsig provider', async () => {
    document.body.innerHTML =
      '<form id="subjectForm" data-captcha-provider="trustsig"><button type="submit">Go</button></form>'
    await loadHandler()

    const event = new Event('submit', { cancelable: true })
    document.getElementById('subjectForm').dispatchEvent(event)
    expect(event.defaultPrevented).toBe(false)
  })

  it('does not intercept form submit when no provider set', async () => {
    document.body.innerHTML = '<form id="subjectForm"><button type="submit">Go</button></form>'
    await loadHandler()

    const event = new Event('submit', { cancelable: true })
    document.getElementById('subjectForm').dispatchEvent(event)
    expect(event.defaultPrevented).toBe(false)
  })
})
