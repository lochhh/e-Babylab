import { readFileSync } from 'fs'
import { runInNewContext } from 'vm'

/**
 * Load a browser global script into a vm context and return captured exports.
 *
 * `capture` is a list of variable names declared with `let` in the script.
 * They aren't properties of the sandbox by default, but they ARE in scope
 * for code appended to the same script string — so we exploit that.
 *
 * `var` / function declarations are returned on the context object directly
 * (e.g. Queue), so those don't need to be listed in `capture`.
 *
 * @param {string} absolutePath - path to the JS source file
 * @param {string[]} capture - names of `let`-declared variables to extract
 * @param {object} globals - extra globals to inject (e.g. mocks)
 * @returns {object} - captured exports merged with the sandbox context
 */
export function loadScript(absolutePath, capture = [], globals = {}) {
  const src = readFileSync(absolutePath, 'utf8')
  const __exports__ = {}
  const sandbox = { __exports__, ...globals }

  const captureCode = capture.length
    ? `\nObject.assign(__exports__, { ${capture.join(', ')} });`
    : ''

  runInNewContext(src + captureCode, sandbox)

  return { ...sandbox, ...__exports__ }
}
