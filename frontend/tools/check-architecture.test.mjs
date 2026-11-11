import assert from 'node:assert/strict'
import { spawnSync } from 'node:child_process'
import fs from 'node:fs'
import os from 'node:os'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import test from 'node:test'

const checker = fileURLToPath(new URL('./check-architecture.mjs', import.meta.url))
function check(files) {
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), 'waypoint-architecture-'))
  try {
    for (const [name, source] of Object.entries(files)) {
      const file = path.join(directory, 'src', name)
      fs.mkdirSync(path.dirname(file), { recursive: true })
      fs.writeFileSync(file, source)
    }
    return spawnSync(process.execPath, [checker], { cwd: directory, encoding: 'utf8' })
  } finally {
    fs.rmSync(directory, { recursive: true, force: true })
  }
}

test('inline type imports cannot hide unresolved dependencies', () => {
  const result = check({ 'types/order.ts': "export type Order = import('./missing').Order" })
  assert.equal(result.status, 1)
  assert.match(result.stderr, /unresolved .\/missing/)
})

test('types cannot depend on implementations through inline imports', () => {
  const result = check({
    'types/order.ts': "export type Order = import('../utils/order').Order",
    'utils/order.ts': 'export type Order = { id: string }',
  })
  assert.equal(result.status, 1)
  assert.match(result.stderr, /shared types import an implementation/)
})

test('type modules reject runtime declarations', () => {
  const result = check({ 'types/order.ts': 'export const status = "pending"' })
  assert.equal(result.status, 1)
  assert.match(result.stderr, /type declarations only/)
})

test('relative imports cannot bypass page transport boundaries', () => {
  const result = check({
    'app/orders/OrdersPage.tsx': "import '../../api/endpoints/orders'",
    'api/endpoints/orders.ts': 'export const orders = []',
  })
  assert.equal(result.status, 1)
  assert.match(result.stderr, /UI must use query hooks/)
})

test('type-only cycles do not count as runtime cycles', () => {
  const result = check({
    'types/a.ts': "import type { B } from './b'; export type A = { b: B }",
    'types/b.ts': "export type B = { a: import('./a').A }",
  })
  assert.equal(result.status, 0, result.stderr)
})

test('a default runtime import stays a runtime edge alongside named type imports', () => {
  const result = check({
    'utils/a.ts': "import b, { type B } from './b'; export default () => b() as B",
    'utils/b.ts': "import a from './a'; export type B = string; export default () => a()",
  })
  assert.equal(result.status, 1)
  assert.match(result.stderr, /Static cycle/)
})
