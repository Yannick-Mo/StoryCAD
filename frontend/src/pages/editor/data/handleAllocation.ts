export type PhysicalSide = 'top' | 'right' | 'bottom' | 'left'

export interface Point {
  x: number
  y: number
}

export interface SidePair {
  sourceSide: PhysicalSide
  targetSide: PhysicalSide
}

export interface HandlePair {
  sourceHandle: string
  targetHandle: string
}

export interface EdgeForHandleAllocation {
  id?: string
  sourceId: string
  targetId: string
  type?: string
  sourceHandle?: string
  targetHandle?: string
}

export interface AllocateHandlesArgs {
  sourceId: string
  targetId: string
  sourcePosition: Point
  targetPosition: Point
  edges: EdgeForHandleAllocation[]
  ignoreEdgeIds?: Iterable<string>
}

const SIDE_TO_SUFFIX: Record<PhysicalSide, string> = {
  top: 't',
  right: 'r',
  bottom: 'b',
  left: 'l',
}

const SUFFIX_TO_SIDE: Record<string, PhysicalSide> = {
  t: 'top',
  r: 'right',
  b: 'bottom',
  l: 'left',
}

const OPPOSING_SIDE_PAIRS: SidePair[] = [
  { sourceSide: 'right', targetSide: 'left' },
  { sourceSide: 'bottom', targetSide: 'top' },
  { sourceSide: 'top', targetSide: 'bottom' },
  { sourceSide: 'left', targetSide: 'right' },
]

export function sideFromHandle(handleId?: string | null): PhysicalSide | null {
  if (!handleId) return null
  const suffix = handleId.split('-')[1]
  return suffix ? SUFFIX_TO_SIDE[suffix] ?? null : null
}

export function sourceHandleForSide(side: PhysicalSide): string {
  return `s-${SIDE_TO_SUFFIX[side]}`
}

export function targetHandleForSide(side: PhysicalSide): string {
  return `t-${SIDE_TO_SUFFIX[side]}`
}

function dedupeSidePairs(pairs: SidePair[]): SidePair[] {
  const seen = new Set<string>()
  const result: SidePair[] = []
  for (const pair of pairs) {
    const key = `${pair.sourceSide}:${pair.targetSide}`
    if (seen.has(key)) continue
    seen.add(key)
    result.push(pair)
  }
  return result
}

export function candidateSidePairs(sourcePosition: Point, targetPosition: Point): SidePair[] {
  const dx = targetPosition.x - sourcePosition.x
  const dy = targetPosition.y - sourcePosition.y
  const absDx = Math.abs(dx)
  const absDy = Math.abs(dy)

  let preferred: SidePair
  if (absDx >= absDy && dx > 0) {
    preferred = { sourceSide: 'right', targetSide: 'left' }
  } else if (absDx >= absDy && dx <= 0) {
    preferred = { sourceSide: 'left', targetSide: 'right' }
  } else if (dy > 0) {
    preferred = { sourceSide: 'bottom', targetSide: 'top' }
  } else {
    preferred = { sourceSide: 'top', targetSide: 'bottom' }
  }

  return dedupeSidePairs([preferred, ...OPPOSING_SIDE_PAIRS])
}

function addSide(
  occupancy: Map<string, Set<PhysicalSide>>,
  nodeId: string,
  handleId?: string
) {
  const side = sideFromHandle(handleId)
  if (!side) return
  const sides = occupancy.get(nodeId) ?? new Set<PhysicalSide>()
  sides.add(side)
  occupancy.set(nodeId, sides)
}

export function buildHandleOccupancy(
  edges: EdgeForHandleAllocation[],
  ignoreEdgeIds: Iterable<string> = []
): Map<string, Set<PhysicalSide>> {
  const ignored = new Set(ignoreEdgeIds)
  const occupancy = new Map<string, Set<PhysicalSide>>()

  for (const edge of edges) {
    if (edge.id && ignored.has(edge.id)) continue
    addSide(occupancy, edge.sourceId, edge.sourceHandle)
    addSide(occupancy, edge.targetId, edge.targetHandle)
  }

  return occupancy
}

export function isSideOccupied(
  occupancy: Map<string, Set<PhysicalSide>>,
  nodeId: string,
  side: PhysicalSide
): boolean {
  return occupancy.get(nodeId)?.has(side) ?? false
}

export function getTimelineReplacementEdgeIds(
  edges: EdgeForHandleAllocation[],
  sourceId: string,
  targetId: string,
  replacingEdgeId?: string
): string[] {
  return edges
    .filter(edge =>
      edge.id &&
      edge.id !== replacingEdgeId &&
      edge.type === 'timeline' &&
      (edge.sourceId === sourceId || edge.targetId === targetId)
    )
    .map(edge => edge.id!)
}

export function allocateHandles({
  sourceId,
  targetId,
  sourcePosition,
  targetPosition,
  edges,
  ignoreEdgeIds = [],
}: AllocateHandlesArgs): HandlePair | null {
  const occupancy = buildHandleOccupancy(edges, ignoreEdgeIds)

  for (const pair of candidateSidePairs(sourcePosition, targetPosition)) {
    if (isSideOccupied(occupancy, sourceId, pair.sourceSide)) continue
    if (isSideOccupied(occupancy, targetId, pair.targetSide)) continue
    return {
      sourceHandle: sourceHandleForSide(pair.sourceSide),
      targetHandle: targetHandleForSide(pair.targetSide),
    }
  }

  return null
}
