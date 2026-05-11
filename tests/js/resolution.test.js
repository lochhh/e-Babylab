import { describe, it, expect } from 'vitest'
import { resolve, dirname } from 'path'
import { fileURLToPath } from 'url'
import { loadScript } from './helpers/load-script.js'

const __dirname = dirname(fileURLToPath(import.meta.url))
const SRC = resolve(__dirname, '../../src/experiments/static/experiments/js/resolution.js')

describe('resolution.js', () => {
  function run(width, height) {
    const calls = {}
    const jq = (sel) => ({ val: (v) => { calls[sel] = v } })
    const $ = (arg) => { if (typeof arg === 'function') { arg(); return } return jq(arg) }
    loadScript(SRC, [], { $, window: { screen: { width, height } } })
    return calls
  }

  it('sets resolution_w input to screen.width', () => {
    expect(run(1920, 1080)["input[name='resolution_w']"]).toBe(1920)
  })

  it('sets resolution_h input to screen.height', () => {
    expect(run(1920, 1080)["input[name='resolution_h']"]).toBe(1080)
  })

  it('uses exact pixel values for non-standard resolution', () => {
    const calls = run(800, 600)
    expect(calls["input[name='resolution_w']"]).toBe(800)
    expect(calls["input[name='resolution_h']"]).toBe(600)
  })
})
