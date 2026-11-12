/** Generate, never hand-edit: TypeScript contracts plus standalone runtime validators. */
import { readFile, writeFile, mkdir } from 'node:fs/promises'
import { createHash } from 'node:crypto'
import openapiTS, { astToString } from './contracts/node_modules/openapi-typescript/dist/index.mjs'
import Ajv2020 from 'ajv/dist/2020.js'
import addFormats from 'ajv-formats'
import standaloneCode from 'ajv/dist/standalone/index.js'

const root = new URL('../', import.meta.url)
const sources = new URL('../backend/packages/contracts/openapi/', root)
const check = process.argv.includes('--check')
let drift = false
async function output(relative, content) {
  const target = new URL(relative, root)
  if (check) {
    if (await readFile(target, 'utf8').catch(() => '') !== content) {
      process.stderr.write(`Generated contract drift: ${relative}\n`)
      drift = true
    }
  } else {
    await mkdir(new URL('.', target), { recursive: true })
    await writeFile(target, content)
  }
}
const manifest = []
for (const [owner, short] of [['identity-access','identity'], ['network-fleet','network'], ['operations','operations'], ['notifications','notifications']]) {
  const source = new URL(`${owner}-v1.json`, sources)
  const text = await readFile(source, 'utf8')
  const document = JSON.parse(text)
  const hash = createHash('sha256').update(text).digest('hex')
  const header = `/* Generated from ${owner}-v1.json (${hash}). Do not edit. */\n`
  await output(`src/types/generated/${short}.ts`, header + astToString(await openapiTS(document, { defaultNonNullable: false })))
  const ajv = new Ajv2020({ strict: false, allErrors: false, code: { source: true, esm: true }, allowUnionTypes: true })
  addFormats(ajv)
  // Pydantic time represents an outlet's local time-of-day and need not contain a UTC offset.
  ajv.addFormat('time', /^\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:[zZ]|[+-]\d{2}:\d{2})?$/)
  ajv.addFormat('binary', true)
  const id = `https://contracts.waypoint.invalid/${short}`
  const fix = (value) => {
    if (Array.isArray(value)) return value.map(fix)
    if (value && typeof value === 'object') return Object.fromEntries(Object.entries(value).map(([key, entry]) => [key, key === '$ref' ? String(entry).replace('#/components/schemas/', `${id}#/$defs/`) : fix(entry)]))
    return value
  }
  ajv.addSchema({ $id: id, $defs: fix(document.components?.schemas ?? {}) })
  const exports = {}
  const compiled = new Map()
  function validator(schema) {
    const serial = JSON.stringify(schema)
    if (compiled.has(serial)) return compiled.get(serial)
    const name = `v${compiled.size}`
    const schemaId = `${id}/validator/${name}`
    ajv.addSchema({ $id: schemaId, ...fix(schema) })
    exports[name] = schemaId
    compiled.set(serial, name)
    return name
  }
  for (const [path, methods] of Object.entries(document.paths)) {
    for (const [method, operation] of Object.entries(methods)) {
      if (!operation.responses) continue
      const entry = { owner: short, path: path.replace(/^\/api\/v1/, ''), method, responses: {}, parameters: operation.parameters ?? [] }
      for (const [status, response] of Object.entries(operation.responses)) {
        if (!status.startsWith('2')) continue
        const schema = response.content?.['application/json']?.schema
        entry.responses[status] = schema ? validator(schema) : null
      }
      const request = operation.requestBody?.content?.['application/json']?.schema
      if (request) { entry.request = validator(request); entry.bodyRequired = Boolean(operation.requestBody.required) }
      manifest.push(entry)
    }
  }
  const profileName = short === 'identity' ? validator({ $ref: '#/components/schemas/UserProfile' }) : undefined
  // AJV's standalone ESM flag changes exports, but its helper snippets still use CommonJS.
  // Emit browser-native imports so both Vite development and production can execute validators.
  let code = standaloneCode(ajv, exports)
  const hasFormats = code.includes('require("ajv-formats/dist/formats")')
  code = code.replaceAll('require("ajv-formats/dist/formats")', 'ajvFormats')
    .replaceAll('require("ajv/dist/runtime/ucs2length").default', '((value) => Array.from(value).length)')
  if (code.includes('require(')) throw new Error(`Unsupported standalone CommonJS helper in ${short}`)
  await output(`src/api/generated/${short}.mjs`, header +
    (hasFormats ? "import * as ajvFormats from 'ajv-formats/dist/formats.js';\n" : '') +
    code + (profileName ? `\nexport { ${profileName} as userProfile };\n` : '\n'))
  const declarations = Object.keys(exports).map((name) => `export const ${name}: (data: unknown) => boolean;`).join('\n') + (profileName ? '\nexport const userProfile: (data: unknown) => data is import("../../types/generated/identity").components["schemas"]["UserProfile"];' : '')
  await output(`src/api/generated/${short}.d.mts`, header + declarations + '\n')
}
await output('src/api/generated/manifest.json', JSON.stringify(manifest, null, 2) + '\n')
if (drift) process.exitCode = 1
else process.stdout.write(`Contracts ${check ? 'verified' : 'generated'} for four services (${manifest.length} operations).\n`)
