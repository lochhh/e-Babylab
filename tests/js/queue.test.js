import { describe, it, expect, beforeEach } from 'vitest'
import { resolve, dirname } from 'path'
import { fileURLToPath } from 'url'
import { loadScript } from './helpers/load-script.js'

const __dirname = dirname(fileURLToPath(import.meta.url))
const SRC = resolve(__dirname, '../../src/experiments/static/experiments/js/queue.src.js')

// Queue is a function declaration (var-hoisted), so it lands on the context object directly.
let Queue
beforeEach(() => {
  Queue = loadScript(SRC).Queue
})

describe('Queue', () => {
  it('starts empty', () => {
    const q = new Queue()
    expect(q.getLength()).toBe(0)
    expect(q.isEmpty()).toBe(true)
  })

  it('enqueue increases length', () => {
    const q = new Queue()
    q.enqueue('a')
    expect(q.getLength()).toBe(1)
    expect(q.isEmpty()).toBe(false)
  })

  it('peek returns front without removing', () => {
    const q = new Queue()
    q.enqueue('first')
    q.enqueue('second')
    expect(q.peek()).toBe('first')
    expect(q.getLength()).toBe(2)
  })

  it('dequeue returns and removes front item', () => {
    const q = new Queue()
    q.enqueue('a')
    q.enqueue('b')
    expect(q.dequeue()).toBe('a')
    expect(q.getLength()).toBe(1)
    expect(q.peek()).toBe('b')
  })

  it('dequeue on empty returns undefined', () => {
    const q = new Queue()
    expect(q.dequeue()).toBeUndefined()
  })

  it('FIFO order across many items', () => {
    const q = new Queue()
    ;[1, 2, 3, 4, 5].forEach(i => q.enqueue(i))
    const result = []
    while (q.getLength() > 0) result.push(q.dequeue())
    expect(result).toEqual([1, 2, 3, 4, 5])
  })

  it('length stays correct after mixed operations', () => {
    const q = new Queue()
    q.enqueue('a')
    q.enqueue('b')
    q.dequeue()
    q.enqueue('c')
    expect(q.getLength()).toBe(2)
    expect(q.peek()).toBe('b')
  })
})
