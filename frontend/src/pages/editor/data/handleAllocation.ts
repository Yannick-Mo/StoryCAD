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

type OccupancyMap = Map<string, Map<PhysicalSide, Set<string>>>

function addSide(
  occupancy: OccupancyMap,
  nodeId: string,
  handleId?: string,
  type?: string,
) {
  if (!type) return
  const side = sideFromHandle(handleId)
  if (!side) return
  let sides = occupancy.get(nodeId)
  if (!sides) {
    sides = new Map()
    occupancy.set(nodeId, sides)
  }
  let types = sides.get(side)
  if (!types) {
    types = new Set()
    sides.set(side, types)
  }
  types.add(type)
}

export function buildHandleOccupancy(
  edges: EdgeForHandleAllocation[],
  ignoreEdgeIds: Iterable<string> = []
): OccupancyMap {
  const ignored = new Set(ignoreEdgeIds)
  const occupancy: OccupancyMap = new Map()

  for (const edge of edges) {
    if (edge.id && ignored.has(edge.id)) continue
    addSide(occupancy, edge.sourceId, edge.sourceHandle, edge.type)
    addSide(occupancy, edge.targetId, edge.targetHandle, edge.type)
  }

  return occupancy
}

export function isSideOccupied(
  occupancy: OccupancyMap,
  nodeId: string,
  side: PhysicalSide,
  type?: string,
): boolean {
  const sides = occupancy.get(nodeId)
  if (!sides) return false
  const types = sides.get(side)
  if (!types) return false
  if (type) return types.has(type)
  return types.size > 0
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
  ignoreEdgeIds: Iterable<string> = [],
  type?: string,
): boolean {
  const occupancy = buildHandleOccupancy(edges, ignoreEdgeIds)
  const sourceSide = sideFromHandle(sourceHandle)
  const targetSide = sideFromHandle(targetHandle)
  if (!sourceSide || !targetSide) return false
  return !isSideOccupied(occupancy, sourceId, sourceSide, type) &&
         !isSideOccupied(occupancy, targetId, targetSide, type)
}
