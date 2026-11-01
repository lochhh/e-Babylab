import { describe, it, expect, afterEach, vi } from 'vitest'
import { initWebgazer } from '../../src/experiments/static/experiments/js/webgazer-calibration.js'

/** Chainable webgazer stub that records the order of its calls. */
function stubWebgazer() {
  const calls = []
  const wg = { params: {}, pause: vi.fn() }
  for (const name of ['setRegression', 'setGazeListener', 'saveDataAcrossSessions',
                      'removeMouseEventListeners', 'showVideoPreview',
                      'showPredictionPoints', 'applyKalmanFilter']) {
    wg[name] = vi.fn(() => { calls.push(name); return wg })
  }
  wg.begin = vi.fn(() => { calls.push('begin'); return Promise.resolve(wg) })
  vi.stubGlobal('webgazer', wg)
  return calls
}

afterEach(() => vi.unstubAllGlobals())

describe('initWebgazer', () => {
  it('removes mouse training listeners after begin(), which adds them', async () => {
    document.body.innerHTML = `
      <canvas id="plotting_canvas"></canvas>
      <div id="webgazer-init"><div class="col"></div><button disabled></button></div>`
    const calls = stubWebgazer()
    const done = initWebgazer()
    await vi.waitFor(() => expect(calls).toContain('applyKalmanFilter'))
    const button = document.querySelector('#webgazer-init button')
    button.disabled = false // enabled by face detection in the real flow
    button.click()
    await done
    // Mouse moves and clicks must never train the gaze model, or an
    // uncalibrated tracker (e.g. after resuming) just follows the mouse
    expect(calls.lastIndexOf('removeMouseEventListeners')).toBeGreaterThan(calls.indexOf('begin'))
  })
})
