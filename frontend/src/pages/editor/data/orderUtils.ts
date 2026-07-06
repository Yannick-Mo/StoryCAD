import type { Chapter, ChapterEdge, Act } from '../types'

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
  let idx = 0
  while (idx < queue.length) {
    const id = queue[idx]
    idx++
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

export function hasIncomingTimeline(edges: ChapterEdge[], nodeId: string): boolean {
  return edges.some(e => e.type === 'timeline' && e.targetId === nodeId)
}

export function hasOutgoingTimeline(edges: ChapterEdge[], nodeId: string): boolean {
  return edges.some(e => e.type === 'timeline' && e.sourceId === nodeId)
}

export function getOutgoingTimeline(edges: ChapterEdge[], nodeId: string): ChapterEdge | undefined {
  return edges.find(e => e.type === 'timeline' && e.sourceId === nodeId)
}

export function getIncomingTimeline(edges: ChapterEdge[], nodeId: string): ChapterEdge | undefined {
  return edges.find(e => e.type === 'timeline' && e.targetId === nodeId)
}

export function getCompletedChain(chapters: Chapter[], edges: ChapterEdge[], acts: Act[]): Chapter[][] {
  const sortedActs = [...acts].sort((a, b) => a.order - b.order)
  if (sortedActs.length === 0) return []

  const ordered = topologicalSort(chapters, edges)
  const chMap = new Map(chapters.map(c => [c.id, c]))
  const heads = ordered.filter(id => chMap.has(id) && !hasIncomingTimeline(edges, id))
  if (heads.length === 0) return []

  const outgoingMap = new Map<string, ChapterEdge>()
  for (const e of edges) {
    if (e.type === 'timeline') outgoingMap.set(e.sourceId, e)
  }

  const chains: Chapter[][] = []
  for (const head of heads) {
    const chain: Chapter[] = []
    let currentId: string | undefined = head
    while (currentId && chMap.has(currentId)) {
      chain.push(chMap.get(currentId)!)
      const edge = outgoingMap.get(currentId)
      currentId = edge?.targetId
    }
    chains.push(chain)
  }
  return chains
}
