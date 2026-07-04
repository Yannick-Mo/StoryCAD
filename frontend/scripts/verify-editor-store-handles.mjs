import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'

const typesSource = readFileSync(new URL('../src/pages/editor/types.ts', import.meta.url), 'utf8')
const storeSource = readFileSync(new URL('../src/pages/editor/data/editorStore.ts', import.meta.url), 'utf8')

assert.match(typesSource, /sourceHandle\?: string/)
assert.match(typesSource, /targetHandle\?: string/)

assert.match(
  storeSource,
  /const addEdge = useCallback\(\(sourceId: string, targetId: string, type: EdgeType = 'timeline', sourceHandle\?: string, targetHandle\?: string\): EdgeResult =>/
)
assert.match(
  storeSource,
  /const newEdge: ChapterEdge = \{ id: uid\(\), sourceId, targetId, type, sourceHandle, targetHandle \}/
)
assert.match(
  storeSource,
  /const reconnectEdge = useCallback\(\(edgeId: string, newSource\?: string, newTarget\?: string, sourceHandle\?: string, targetHandle\?: string\) =>/
)
assert.match(storeSource, /sourceHandle: sourceHandle \?\? e\.sourceHandle/)
assert.match(storeSource, /targetHandle: targetHandle \?\? e\.targetHandle/)

console.log('editor store handle persistence checks passed')
