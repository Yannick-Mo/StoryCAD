import assert from 'node:assert/strict'
import { readFileSync, mkdtempSync, writeFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import { pathToFileURL } from 'node:url'
import ts from 'typescript'

const helperSource = readFileSync(
  new URL('../src/pages/editor/data/handleAllocation.ts', import.meta.url),
  'utf8'
)

const output = ts.transpileModule(helperSource, {
  compilerOptions: {
    module: ts.ModuleKind.ES2022,
    target: ts.ScriptTarget.ES2022,
    strict: true,
  },
}).outputText

const tempDir = mkdtempSync(join(tmpdir(), 'storycad-handle-allocation-'))
const modulePath = join(tempDir, 'handleAllocation.mjs')
writeFileSync(modulePath, output)

const {
  isHandlePairAvailable,
  buildHandleOccupancy,
  getTimelineReplacementEdgeIds,
  isSideOccupied,
  sideFromHandle,
} = await import(pathToFileURL(modulePath).href)

assert.equal(sideFromHandle('s-r'), 'right')
assert.equal(sideFromHandle('t-r'), 'right')
assert.equal(sideFromHandle('s-t'), 'top')
assert.equal(sideFromHandle('t-b'), 'bottom')
assert.equal(sideFromHandle('bad-handle'), null)

// Free pair returns true
assert.equal(
  isHandlePairAvailable('source', 'target', 's-r', 't-l', []),
  true
)

// Source side occupied
const srcOccupied = [
  { id: 'e1', sourceId: 'source', targetId: 'other', sourceHandle: 's-r', targetHandle: 't-l' },
]
assert.equal(
  isHandlePairAvailable('source', 'target', 's-r', 't-l', srcOccupied),
  false
)

// Target side occupied
const tgtOccupied = [
  { id: 'e1', sourceId: 'other', targetId: 'target', sourceHandle: 's-r', targetHandle: 't-l' },
]
assert.equal(
  isHandlePairAvailable('source', 'target', 's-r', 't-l', tgtOccupied),
  false
)

// Occupied but ignored
assert.equal(
  isHandlePairAvailable('source', 'target', 's-r', 't-l', srcOccupied, ['e1']),
  true
)

// Invalid handle
assert.equal(
  isHandlePairAvailable('source', 'target', 'invalid', 't-l', []),
  false
)

// buildHandleOccupancy and isSideOccupied
const edges = [
  { id: 'e1', sourceId: 'a', targetId: 'b', sourceHandle: 's-r', targetHandle: 't-l' },
]
const occupancy = buildHandleOccupancy(edges)
assert.equal(isSideOccupied(occupancy, 'a', 'right'), true)
assert.equal(isSideOccupied(occupancy, 'a', 'left'), false)
assert.equal(isSideOccupied(occupancy, 'b', 'left'), true)
assert.equal(isSideOccupied(occupancy, 'b', 'right'), false)

// getTimelineReplacementEdgeIds
const replacementEdges = [
  { id: 'old', type: 'timeline', sourceId: 'source', targetId: 'old-target', sourceHandle: 's-r', targetHandle: 't-l' },
  { id: 'other', type: 'causal', sourceId: 'other', targetId: 'source', sourceHandle: 's-b', targetHandle: 't-b' },
]
assert.deepEqual(
  getTimelineReplacementEdgeIds(replacementEdges, 'source', 'new-target'),
  ['old']
)

console.log('handle allocation checks passed')
