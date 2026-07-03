import type { Chapter, ChapterEdge } from '../types'

export function topologicalSort(chapters: { id: string }[], edges: ChapterEdge[]): string[] {
  const timelineEdges = edges.filter(e => e.type === 'timeline')
  const adj = new Map<string, string[]>()
  const inDeg = new Map<string, number>()
  const allIds = new Set(chapters.map(c => c.id))

  for (const id of allIds) {
    adj.set(id, [])
    inDeg.set(id, 0)
  }

  for (const e of timelineEdges) {
    if (!allIds.has(e.sourceId) || !allIds.has(e.targetId)) continue
    adj.get(e.sourceId)!.push(e.targetId)
    inDeg.set(e.targetId, (inDeg.get(e.targetId) ?? 0) + 1)
  }

  const queue: string[] = []
  for (const [id, deg] of inDeg) {
    if (deg === 0) queue.push(id)
  }

  const result: string[] = []
  while (queue.length > 0) {
    const id = queue.shift()!
    result.push(id)
    for (const next of adj.get(id) ?? []) {
      const nd = (inDeg.get(next) ?? 1) - 1
      inDeg.set(next, nd)
      if (nd === 0) queue.push(next)
    }
  }

  for (const id of allIds) {
    if (!result.includes(id)) result.push(id)
  }

  return result
}

export function wouldCreateCycle(edges: ChapterEdge[], sourceId: string, targetId: string): boolean {
  if (sourceId === targetId) return true
  const adj = new Map<string, string[]>()
  const allIds = new Set<string>()
  for (const e of edges) {
    if (e.sourceId === sourceId && e.targetId === targetId) continue
    if (!adj.has(e.sourceId)) adj.set(e.sourceId, [])
    adj.get(e.sourceId)!.push(e.targetId)
    allIds.add(e.sourceId)
    allIds.add(e.targetId)
  }
  allIds.add(sourceId)
  allIds.add(targetId)
  if (!adj.has(sourceId)) adj.set(sourceId, [])
  adj.get(sourceId)!.push(targetId)

  const visited = new Set<string>()
  const stack = [targetId]
  while (stack.length > 0) {
    const id = stack.pop()!
    if (id === sourceId) return true
    if (visited.has(id)) continue
    visited.add(id)
    for (const next of adj.get(id) ?? []) {
      stack.push(next)
    }
  }
  return false
}

export function isEdgeLocked(edge: ChapterEdge, chapters: Chapter[]): boolean {
  if (edge.type !== 'timeline') return false
  const target = chapters.find(c => c.id === edge.targetId)
  return target ? target.wordCount > 0 : false
}
