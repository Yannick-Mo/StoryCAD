import { readFileSync } from 'node:fs'
import assert from 'node:assert/strict'

// Regression guard for act group interaction layering.
// Keep this in sync with PlotCanvas/ActGroupNode comments. The important rule is:
// never solve group dragging by adding a pointer-enabled full-area group DOM layer.
// React Flow renders node DOM above edge SVGs, so such a layer makes edges inside
// groups impossible to select. Blank-space group drag and resize must remain
// coordinate-based in PlotCanvas.
const actGroupSource = readFileSync(new URL('../src/pages/editor/views/plot/ActGroupNode.tsx', import.meta.url), 'utf8')
const plotCanvasSource = readFileSync(new URL('../src/pages/editor/views/plot/PlotCanvas.tsx', import.meta.url), 'utf8')

// 1. ActGroupNode must NOT use a full-area pointer-events-auto drag overlay
assert.doesNotMatch(
  actGroupSource,
  /act-drag-handle[^`"\n]*absolute[^`"\n]*inset-0[^`"\n]*pointer-events-auto/s,
  'ActGroupNode must not use a full-area pointer-events-auto drag overlay that blocks edge/node clicks'
)

// 2. Act group nodes keep pointer-events none so chapter nodes + edges remain clickable
assert.match(
  plotCanvasSource,
  /style:\s*\{\s*width:\s*w,\s*height:\s*ACT_H,\s*pointerEvents:\s*'none'\s*\}/,
  'Act group React Flow nodes should keep pointerEvents none'
)

// 3. Blank act-group dragging is handled via pane pointer-down capture: isInteractiveFlowTarget skips edges, nodes, handles, resize, inputs
assert.match(
  plotCanvasSource,
  /isInteractiveFlowTarget/,
  'PlotCanvas should guard blank act-group dragging with an interactive-target check'
)

// 4. The interactive guard must skip edges, nodes, handles, edge updater, nodrag, and interactive elements
for (const selector of ['.react-flow__edge', '.react-flow__node', '.react-flow__handle', '.react-flow__edgeupdater', '.nodrag', 'button, input']) {
  assert.ok(
    plotCanvasSource.includes(selector),
    `isInteractiveFlowTarget() should skip clicks on ${selector}`
  )
}

// 5. The pointer-down capture must hit-test act group bounds
assert.match(
  plotCanvasSource,
  /screenToFlowPosition/,
  'Blank act-group dragging should use React Flow coordinates for act group bounds'
)

// 6. The pointer-down capture must move only the matched act group node
assert.match(
  plotCanvasSource,
  /setNodes\(nds\s*=>\s*nds\.map\(\s*n\s*=>\s*n\.id\s*===\s*actNode\.id/s,
  'Blank act-group dragging should move only the matched act group node via setNodes'
)

// 7. The ReactFlow wrapper must have onPointerDownCapture={handleActGroupPanePointerDown}
assert.match(
  plotCanvasSource,
  /onPointerDownCapture=\{handleActGroupPanePointerDown\}/,
  'The ReactFlow wrapper should capture pane pointer-down for blank-area act group dragging'
)

// 8. Resize must be handled by coordinate hit testing, because the group background deliberately does not receive pointer events.
assert.match(
  plotCanvasSource,
  /function isActGroupResizePosition/,
  'Act group resize hit testing should live in a shared coordinate helper'
)
assert.match(
  plotCanvasSource,
  /const isResize = isActGroupResizePosition\(actNode, startFlowPos\)/,
  'Act group pointer down should detect resize from the shared coordinate helper'
)
assert.match(
  plotCanvasSource,
  /width: Math\.max\(300, startWidth \+ nextFlowPos\.x - startFlowPos\.x\)/,
  'Act group resize should update width from pointer movement'
)
assert.match(
  plotCanvasSource,
  /height: Math\.max\(150, startHeight \+ nextFlowPos\.y - startFlowPos\.y\)/,
  'Act group resize should update height from pointer movement'
)

// 9. Cursor feedback must use the same coordinate hit testing instead of pointer-enabled resize DOM.
assert.match(
  plotCanvasSource,
  /const \[paneCursor, setPaneCursor\] = useState<'default' \| 'se-resize'>\('default'\)/,
  'PlotCanvas should track resize cursor state'
)
assert.match(
  plotCanvasSource,
  /handleActGroupPanePointerMove/,
  'PlotCanvas should update resize cursor on pointer move'
)
assert.match(
  plotCanvasSource,
  /setPaneCursor\(actNode && isActGroupResizePosition\(actNode, flowPos\) \? 'se-resize' : 'default'\)/,
  'Resize cursor should use the same bottom-right coordinate hit test'
)
assert.match(
  plotCanvasSource,
  /style=\{\{ cursor: paneCursor \}\}/,
  'The ReactFlow wrapper should apply the computed cursor'
)
assert.match(
  plotCanvasSource,
  /className=\{paneCursor === 'se-resize' \? 'resize-cursor' : undefined\}/,
  'ReactFlow should receive a resize-cursor class when resize cursor is active'
)
assert.match(
  plotCanvasSource,
  /\.resize-cursor \.react-flow__pane[\s\S]*cursor: se-resize !important/,
  'Resize cursor should override React Flow pane cursor styles'
)

console.log('act group interaction layering checks passed')
