import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'

const source = readFileSync(new URL('../src/pages/editor/views/plot/PlotCanvas.tsx', import.meta.url), 'utf8')

assert.match(source, /import \{ isHandlePairAvailable, getTimelineReplacementEdgeIds \} from '\.\.\/\.\.\/data\/handleAllocation'/)
assert.match(source, /onAddEdge\?: \(sourceId: string, targetId: string, type\?: EdgeType, sourceHandle\?: string, targetHandle\?: string\) => EdgeResult/)
assert.match(source, /onReconnectEdge\?: \(edgeId: string, newSource\?: string, newTarget\?: string, sourceHandle\?: string, targetHandle\?: string\) => void/)
assert.match(source, /const sourceHandle = e\.sourceHandle \?\? getBestHandle\(a, b\)\.sourceHandle/)
assert.match(source, /const targetHandle = e\.targetHandle \?\? getBestHandle\(a, b\)\.targetHandle/)
assert.match(source, /isHandlePairAvailable\(conn\.source, conn\.target, conn\.sourceHandle, conn\.targetHandle, edges, ignoreEdgeIds\)/)
assert.match(source, /isHandlePairAvailable\(newConn\.source, newConn\.target, newConn\.sourceHandle, newConn\.targetHandle, edges, ignoreEdgeIds\)/)
assert.match(source, /该侧连接点已被占用/)
assert.match(source, /conn\.source, conn\.target, 'timeline', conn\.sourceHandle, conn\.targetHandle/)
assert.match(source, /oldEdge\.id, newConn\.source, newConn\.target, newConn\.sourceHandle, newConn\.targetHandle/)

console.log('plot canvas handle integration checks passed')
