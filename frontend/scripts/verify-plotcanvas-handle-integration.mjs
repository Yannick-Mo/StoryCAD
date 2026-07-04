import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'

const source = readFileSync(new URL('../src/pages/editor/views/plot/PlotCanvas.tsx', import.meta.url), 'utf8')

assert.match(source, /import \{ allocateHandles, getTimelineReplacementEdgeIds \} from '\.\.\/\.\.\/data\/handleAllocation'/)
assert.match(source, /onAddEdge\?: \(sourceId: string, targetId: string, type\?: EdgeType, sourceHandle\?: string, targetHandle\?: string\) => EdgeResult/)
assert.match(source, /onReconnectEdge\?: \(edgeId: string, newSource\?: string, newTarget\?: string, sourceHandle\?: string, targetHandle\?: string\) => void/)
assert.match(source, /const displayEdges: ChapterEdge\[] = \[]/)
assert.match(source, /let sourceHandle = e\.sourceHandle/)
assert.match(source, /let targetHandle = e\.targetHandle/)
assert.match(source, /allocateHandles\(\{[\s\S]*sourceId: e\.sourceId,[\s\S]*targetId: e\.targetId,[\s\S]*edges: displayEdges,[\s\S]*\}\)/)
assert.match(source, /sourceHandle,[\s\S]*targetHandle,[\s\S]*type: 'bezier'/)
assert.match(source, /const ignoreEdgeIds = getTimelineReplacementEdgeIds\(edges, conn\.source, conn\.target\)/)
assert.match(source, /节点连接点已满，无法创建连线/)
assert.match(source, /conn\.source, conn\.target, 'timeline', allocation\.sourceHandle, allocation\.targetHandle/)
assert.match(source, /oldEdge\.id, newConn\.source, newConn\.target, allocation\.sourceHandle, allocation\.targetHandle/)

console.log('plot canvas handle integration checks passed')
