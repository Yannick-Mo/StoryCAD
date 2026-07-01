import { useEffect, useRef, type RefObject } from "react"
import cytoscape, { type Core, type EventObject } from "cytoscape"
import dagre from "cytoscape-dagre"
import type { PlotGraph } from "../types/skeleton"

cytoscape.use(dagre)

export function useCytoscape(
  containerRef: RefObject<HTMLDivElement | null>,
  graphData: PlotGraph | undefined,
  onNodeSelect?: (nodeId: string) => void
) {
  const cyRef = useRef<Core | null>(null)

  useEffect(() => {
    if (!containerRef.current || !graphData) return

    const cy = cytoscape({
      container: containerRef.current,
      elements: [
        ...graphData.nodes.map((n) => ({
          data: { id: n.id, description: n.description, emotion_value: n.emotion_value },
        })),
        ...graphData.edges.map((e) => ({
          data: { source: e.source, target: e.target, type: e.type },
        })),
      ],
      style: [
        {
          selector: "node",
          style: {
            label: "data(id)",
            "text-valign": "center",
            "text-halign": "center",
            color: "#fff",
            width: 80,
            height: 80,
            "background-color": (ele) => {
              const v = ele.data("emotion_value") ?? 0
              if (v > 70) return "#ef4444"
              if (v > 40) return "#eab308"
              return "#22c55e"
            },
          },
        },
        {
          selector: "edge",
          style: {
            width: 2,
            "line-color": "#6b7280",
            "target-arrow-color": "#6b7280",
            "target-arrow-shape": "triangle",
            "curve-style": "bezier",
            "line-style": (ele) => {
              const t = ele.data("type")
              if (t === "necessary") return "solid"
              if (t === "possible") return "dashed"
              return "dotted"
            },
          },
        },
      ],
      layout: {
        name: "dagre",
        padding: 50,
      },
      wheelSensitivity: 0.3,
    })

    if (onNodeSelect) {
      cy.on("tap", "node", (evt: EventObject) => {
        onNodeSelect(evt.target.id())
      })
    }

    cyRef.current = cy

    return () => {
      cy.destroy()
      cyRef.current = null
    }
  }, [graphData])

  return cyRef
}