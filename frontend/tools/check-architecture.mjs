import fs from 'node:fs'
import path from 'node:path'
import ts from 'typescript'

const root = path.resolve('src')
const files = fs
  .readdirSync(root, { recursive: true })
  .filter((name) => /\.tsx?$/.test(name))
  .map((name) => path.join(root, name))
const graph = new Map()
const errors = []
for (const file of files) {
  if (file.includes(`${path.sep}test${path.sep}`)) continue
  const source = ts.createSourceFile(
    file,
    fs.readFileSync(file, 'utf8'),
    ts.ScriptTarget.Latest,
    true,
  )
  const edges = []
  const owner = path.relative(root, file).split(path.sep)
  if (owner[0] === 'types') {
    for (const statement of source.statements) {
      const declaration =
        ts.isInterfaceDeclaration(statement) ||
        ts.isTypeAliasDeclaration(statement) ||
        (ts.isImportDeclaration(statement) && statement.importClause?.isTypeOnly) ||
        (ts.isExportDeclaration(statement) && statement.isTypeOnly)
      if (!declaration)
        errors.push(`${path.relative(root, file)}: types must contain type declarations only`)
    }
  }
  function inspect(node) {
    const isImport = ts.isImportDeclaration(node)
    const isExport = ts.isExportDeclaration(node)
    const isDynamic =
      ts.isCallExpression(node) && node.expression.kind === ts.SyntaxKind.ImportKeyword
    const isTypeImport = ts.isImportTypeNode(node)
    const spec =
      isImport || isExport
        ? node.moduleSpecifier
        : isDynamic
          ? node.arguments[0]
          : isTypeImport && ts.isLiteralTypeNode(node.argument)
            ? node.argument.literal
            : undefined
    if (
      spec &&
      ts.isStringLiteral(spec) &&
      (spec.text.startsWith('.') || spec.text.startsWith('@/'))
    ) {
      const base = spec.text.startsWith('@/')
        ? path.join(root, spec.text.slice(2))
        : path.resolve(path.dirname(file), spec.text)
      const target = [
        base,
        `${base}.ts`,
        `${base}.tsx`,
        `${base}/index.ts`,
        `${base}/index.tsx`,
      ].find((candidate) => fs.existsSync(candidate) && fs.statSync(candidate).isFile())
      if (!target) errors.push(`${path.relative(root, file)}: unresolved ${spec.text}`)
      if (target) {
        const dependency = path.relative(root, target).split(path.sep)
        const atomic = ['atoms', 'molecules', 'organisms', 'templates']
        if (
          owner[0] === 'components' &&
          dependency[0] === 'components' &&
          atomic.indexOf(dependency[1]) > atomic.indexOf(owner[1])
        ) {
          errors.push(`${path.relative(root, file)}: imports higher atomic category ${spec.text}`)
        }
        if (owner[0] === 'components' && dependency[0] === 'app' && dependency[1] !== 'providers') {
          errors.push(
            `${path.relative(root, file)}: reusable UI imports routing/pages ${spec.text}`,
          )
        }
        if (owner[0] === 'types' && dependency[0] !== 'types') {
          errors.push(
            `${path.relative(root, file)}: shared types import an implementation ${spec.text}`,
          )
        }
        if (
          ['types', 'services', 'utils', 'schemas', 'mappers'].includes(owner[0]) &&
          ['api', 'infrastructure', 'app', 'components', 'hooks', 'queries', 'lib'].includes(
            dependency[0],
          )
        ) {
          errors.push(
            `${path.relative(root, file)}: foundational module imports an implementation ${spec.text}`,
          )
        }
        if (
          (owner[0] === 'components' || (owner[0] === 'app' && owner[1] !== 'providers')) &&
          ((dependency[0] === 'infrastructure' &&
            ['storage', 'adapters'].includes(dependency[1])) ||
            (dependency[0] === 'api' &&
              (dependency[1] === 'endpoints' || dependency[2] === 'apiClient.ts')))
        )
          errors.push(
            `${path.relative(root, file)}: UI must use query hooks instead of transport/storage ${spec.text}`,
          )
        if (
          owner[0] === 'components' &&
          owner[1] === 'atoms' &&
          ['queries', 'api', 'app'].includes(dependency[0])
        ) {
          errors.push(
            `${path.relative(root, file)}: atom imports application behavior ${spec.text}`,
          )
        }
      }

      const typeOnly =
        isTypeImport ||
        (isImport &&
          (node.importClause?.isTypeOnly ||
            (node.importClause?.namedBindings &&
              ts.isNamedImports(node.importClause.namedBindings) &&
              !node.importClause.name &&
              node.importClause.namedBindings.elements.length > 0 &&
              node.importClause.namedBindings.elements.every((element) => element.isTypeOnly)))) ||
        (isExport &&
          (node.isTypeOnly ||
            (node.exportClause &&
              ts.isNamedExports(node.exportClause) &&
              node.exportClause.elements.length > 0 &&
              node.exportClause.elements.every((element) => element.isTypeOnly))))
      // Lazy route chunks and type-only references do not form synchronous initialization cycles.
      if (target && !typeOnly && !isDynamic && /\.tsx?$/.test(target)) edges.push(target)
    }
    ts.forEachChild(node, inspect)
  }
  inspect(source)
  graph.set(file, edges)
}
const active = new Set()
const done = new Set()
function visit(file, trail = []) {
  if (active.has(file)) {
    errors.push(
      `Static cycle: ${[...trail.slice(trail.indexOf(file)), file].map((name) => path.relative(root, name)).join(' -> ')}`,
    )
    return
  }
  if (done.has(file)) return
  active.add(file)
  for (const target of graph.get(file) ?? []) visit(target, [...trail, file])
  active.delete(file)
  done.add(file)
}
for (const file of graph.keys()) visit(file)
if (errors.length) {
  console.error(errors.join('\n'))
  process.exitCode = 1
} else
  console.log(
    `Architecture check passed: ${graph.size} production modules; no unresolved local imports, layer violations, or static runtime cycles.`,
  )
