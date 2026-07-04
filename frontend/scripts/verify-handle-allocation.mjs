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

// Source side occupied (same type)
const srcOccupied = [
  { id: 'e1', sourceId: 'source', targetId: 'other', type: 'timeline', sourceHandle: 's-r', targetHandle: 't-l' },
]
assert.equal(
  isHandlePairAvailable('source', 'target', 's-r', 't-l', srcOccupied, [], 'timeline'),
  false
)

// Target side occupied (same type)
const tgtOccupied = [
  { id: 'e1', sourceId: 'other', targetId: 'target', type: 'timeline', sourceHandle: 's-r', targetHandle: 't-l' },
]
assert.equal(
  isHandlePairAvailable('source', 'target', 's-r', 't-l', tgtOccupied, [], 'timeline'),
  false
)

// Different types can share the same physical side
const diffTypeEdges = [
  { id: 'e1', sourceId: 'source', targetId: 'other', type: 'causal', sourceHandle: 's-r', targetHandle: 't-l' },
]
assert.equal(
  isHandlePairAvailable('source', 'target', 's-r', 't-l', diffTypeEdges, [], 'timeline'),
  true,
  'timeline should be able to use s-r side even when causal already uses it'
)

// Same type on same side is blocked
assert.equal(
  isHandlePairAvailable('source', 'target', 's-r', 't-l', diffTypeEdges, [], 'causal'),
  false,
  'second causal edge on same side should be blocked'
)

// Occupied but ignored (for replacement)
assert.equal(
  isHandlePairAvailable('source', 'target', 's-r', 't-l', srcOccupied, ['e1'], 'timeline'),
  true
)

// Invalid handle
assert.equal(
  isHandlePairAvailable('source', 'target', 'invalid', 't-l', []),
  false
)

// buildHandleOccupancy and isSideOccupied
const edges = [
  { id: 'e1', sourceId: 'a', targetId: 'b', type: 'timeline', sourceHandle: 's-r', targetHandle: 't-l' },
]
const occupancy = buildHandleOccupancy(edges)
assert.equal(isSideOccupied(occupancy, 'a', 'right', 'timeline'), true)
assert.equal(isSideOccupied(occupancy, 'a', 'left', 'timeline'), false)
assert.equal(isSideOccupied(occupancy, 'b', 'left', 'timeline'), true)
assert.equal(isSideOccupied(occupancy, 'b', 'right', 'timeline'), false)

// Per-type occupancy isolation
assert.equal(isSideOccupied(occupancy, 'a', 'right', 'causal'), false, 'causal should not be blocked by timeline')
assert.equal(isSideOccupied(occupancy, 'a', 'right'), true, 'without type filter, should see timeline occupancy')

// Multiple types on same side
const multiTypeEdges = [
  { id: 'e1', sourceId: 'a', targetId: 'b', type: 'timeline', sourceHandle: 's-r', targetHandle: 't-l' },
  { id: 'e2', sourceId: 'a', targetId: 'c', type: 'causal', sourceHandle: 's-r', targetHandle: 't-r' },
]
const multiOccupancy = buildHandleOccupancy(multiTypeEdges)
assert.equal(isSideOccupied(multiOccupancy, 'a', 'right', 'timeline'), true)
assert.equal(isSideOccupied(multiOccupancy, 'a', 'right', 'causal'), true)
assert.equal(isSideOccupied(multiOccupancy, 'a', 'right', 'foreshadow'), false)

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
