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
  allocateHandles,
  buildHandleOccupancy,
  candidateSidePairs,
  getTimelineReplacementEdgeIds,
  isSideOccupied,
  sideFromHandle,
  sourceHandleForSide,
  targetHandleForSide,
} = await import(pathToFileURL(modulePath).href)

assert.equal(sideFromHandle('s-r'), 'right')
assert.equal(sideFromHandle('t-r'), 'right')
assert.equal(sideFromHandle('s-t'), 'top')
assert.equal(sideFromHandle('t-b'), 'bottom')
assert.equal(sideFromHandle('bad-handle'), null)
assert.equal(sourceHandleForSide('left'), 's-l')
assert.equal(targetHandleForSide('left'), 't-l')

assert.deepEqual(
  candidateSidePairs({ x: 0, y: 0 }, { x: 300, y: 20 })[0],
  { sourceSide: 'right', targetSide: 'left' }
)
assert.deepEqual(
  candidateSidePairs({ x: 300, y: 0 }, { x: 0, y: 20 })[0],
  { sourceSide: 'left', targetSide: 'right' }
)
assert.deepEqual(
  candidateSidePairs({ x: 0, y: 0 }, { x: 20, y: 300 })[0],
  { sourceSide: 'bottom', targetSide: 'top' }
)
assert.deepEqual(
  candidateSidePairs({ x: 0, y: 300 }, { x: 20, y: 0 })[0],
  { sourceSide: 'top', targetSide: 'bottom' }
)

const incomingRight = [
  { id: 'incoming', sourceId: 'other', targetId: 'chapter', sourceHandle: 's-l', targetHandle: 't-r' },
]
const occupancy = buildHandleOccupancy(incomingRight)
assert.equal(isSideOccupied(occupancy, 'chapter', 'right'), true)
assert.equal(isSideOccupied(occupancy, 'chapter', 'left'), false)

assert.deepEqual(
  allocateHandles({
    sourceId: 'chapter',
    targetId: 'next',
    sourcePosition: { x: 0, y: 0 },
    targetPosition: { x: 300, y: 0 },
    edges: incomingRight,
  }),
  { sourceHandle: 's-b', targetHandle: 't-t' }
)

const occupiedIdeal = [
  { id: 'existing', sourceId: 'source', targetId: 'old', sourceHandle: 's-r', targetHandle: 't-l' },
]
assert.deepEqual(
  allocateHandles({
    sourceId: 'source',
    targetId: 'target',
    sourcePosition: { x: 0, y: 0 },
    targetPosition: { x: 300, y: 0 },
    edges: occupiedIdeal,
  }),
  { sourceHandle: 's-b', targetHandle: 't-t' }
)

const fullNode = [
  { id: 'top', sourceId: 'a', targetId: 'full', sourceHandle: 's-r', targetHandle: 't-t' },
  { id: 'right', sourceId: 'b', targetId: 'full', sourceHandle: 's-r', targetHandle: 't-r' },
  { id: 'bottom', sourceId: 'c', targetId: 'full', sourceHandle: 's-r', targetHandle: 't-b' },
  { id: 'left', sourceId: 'd', targetId: 'full', sourceHandle: 's-r', targetHandle: 't-l' },
]
assert.equal(
  allocateHandles({
    sourceId: 'new',
    targetId: 'full',
    sourcePosition: { x: 0, y: 0 },
    targetPosition: { x: 300, y: 0 },
    edges: fullNode,
  }),
  null
)

const replacementEdges = [
  { id: 'old', type: 'timeline', sourceId: 'source', targetId: 'old-target', sourceHandle: 's-r', targetHandle: 't-l' },
  { id: 'other', type: 'causal', sourceId: 'other', targetId: 'source', sourceHandle: 's-b', targetHandle: 't-b' },
]
assert.deepEqual(
  getTimelineReplacementEdgeIds(replacementEdges, 'source', 'new-target'),
  ['old']
)
assert.deepEqual(
  allocateHandles({
    sourceId: 'source',
    targetId: 'new-target',
    sourcePosition: { x: 0, y: 0 },
    targetPosition: { x: 300, y: 0 },
    edges: replacementEdges,
    ignoreEdgeIds: ['old'],
  }),
  { sourceHandle: 's-r', targetHandle: 't-l' }
)

console.log('handle allocation checks passed')
