import { useState, useRef } from "react"
import { useProjectContext } from "../../context/ProjectContext"
import { useCytoscape } from "../../hooks/useCytoscape"
import NodePropertyEditor from "../panels/NodePropertyEditor"
import { X } from "lucide-react"

export default function PlotGraphView() {
  const { state, dispatch } = useProjectContext()
  const graph = state.project?.skeleton?.graph
  const [selectedNode, setSelectedNode] = useState<string | null>(null)
  const containerRef = useRef<HTMLDivElement | null>(null)

  useCytoscape(
    containerRef,
    graph,
    (nodeId) => setSelectedNode(nodeId)
  )

  const selectedNodeData = graph?.nodes.find((n) => n.id === selectedNode)

  function handleNodeUpdate(field: string, value: string | number) {
    if (!selectedNode || !graph) return
    const updatedNodes = graph.nodes.map((n) =>
      n.id === selectedNode ? { ...n, [field]: value } : n
    )
    dispatch({
      type: "UPDATE_SKELETON",
      payload: { key: "graph", value: { ...graph, nodes: updatedNodes } },
    })
  }

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center justify-between px-4 py-2 bg-gray-800 border-b border-gray-700">
        <span className="text-sm text-gray-300">
          节点: {graph?.nodes.length ?? 0} | 边: {graph?.edges.length ?? 0}
        </span>
      </div>
      <div ref={containerRef} className="flex-1" />
      {selectedNode && selectedNodeData && (
        <div className="border-t border-gray-700">
          <div className="flex items-center justify-between px-4 py-2 bg-gray-800">
            <span className="text-sm font-medium">节点: {selectedNode}</span>
            <button
              onClick={() => setSelectedNode(null)}
              className="text-gray-400 hover:text-gray-200"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
          <NodePropertyEditor
            node={selectedNodeData}
            onUpdate={handleNodeUpdate}
          />
        </div>
      )}
    </div>
  )
}