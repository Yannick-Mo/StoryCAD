export type PhysicalSide = 'top' | 'right' | 'bottom' | 'left'

export interface EdgeForHandleAllocation {
  id?: string
  sourceId: string
  targetId: string
  type?: string
  sourceHandle?: string
  targetHandle?: string
}

const SUFFIX_TO_SIDE: Record<string, PhysicalSide> = {
  t: 'top',
  r: 'right',
  b: 'bottom',
  l: 'left',
}

export function sideFromHandle(handleId?: string | null): PhysicalSide | null {
  if (!handleId) return null
  const suffix = handleId.split('-')[1]
  return suffix ? SUFFIX_TO_SIDE[suffix] ?? null : null
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

export function isHandlePairAvailable(
  sourceId: string,
  targetId: string,
  sourceHandle: string,
  targetHandle: string,
  edges: EdgeForHandleAllocation[],
  ignoreEdgeIds: Iterable<string> = []
): boolean {
  const occupancy = buildHandleOccupancy(edges, ignoreEdgeIds)
  const sourceSide = sideFromHandle(sourceHandle)
  const targetSide = sideFromHandle(targetHandle)
  if (!sourceSide || !targetSide) return false
  return !isSideOccupied(occupancy, sourceId, sourceSide) &&
         !isSideOccupied(occupancy, targetId, targetSide)
}
