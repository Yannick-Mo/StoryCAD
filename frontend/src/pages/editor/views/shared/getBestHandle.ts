// Determine best source/target handle sides based on relative node positions
export function getBestHandle(
  source: { x: number; y: number },
  target: { x: number; y: number }
): { sourceHandle: string; targetHandle: string } {
  const dx = target.x - source.x
  const dy = target.y - source.y
  const absDx = Math.abs(dx)
  const absDy = Math.abs(dy)

  if (absDx >= absDy && dx > 0) return { sourceHandle: 's-r', targetHandle: 't-l' }
  if (absDx >= absDy && dx <= 0) return { sourceHandle: 's-l', targetHandle: 't-r' }
  if (dy > 0) return { sourceHandle: 's-b', targetHandle: 't-t' }
  return { sourceHandle: 's-t', targetHandle: 't-b' }
}

// Approximate center of a node given its top-left position and size
export function nodeCenter(
  pos: { x: number; y: number },
  w: number = 176,
  h: number = 90
): { x: number; y: number } {
  return { x: pos.x + w / 2, y: pos.y + h / 2 }
}
