import { useState } from "react"
import { useProjectContext } from "../../context/ProjectContext"
import { validateSkeleton } from "../../api/client"
import { AlertCircle, AlertTriangle, Info, ChevronDown, ChevronRight } from "lucide-react"

export default function ValidationView() {
  const { state, dispatch } = useProjectContext()
  const [validating, setValidating] = useState(false)
  const [collapsed, setCollapsed] = useState<Record<string, boolean>>({})
  const issues = state.project?.validation_report ?? []

  async function handleValidate() {
    if (!state.project) return
    setValidating(true)
    try {
      const result = await validateSkeleton(state.project.project_id)
      dispatch({
        type: "UPDATE_SKELETON",
        payload: { key: "validation_report" as any, value: result.issues ?? [] },
      })
    } finally {
      setValidating(false)
    }
  }

  const grouped = {
    high: issues.filter((i) => i.severity === "high"),
    medium: issues.filter((i) => i.severity === "medium"),
    low: issues.filter((i) => i.severity === "low"),
  }

  function toggleGroup(severity: string) {
    setCollapsed((prev) => ({ ...prev, [severity]: !prev[severity] }))
  }

  const severityIcon = (severity: string) => {
    switch (severity) {
      case "high":
        return <AlertCircle className="w-4 h-4 text-red-400" />
      case "medium":
        return <AlertTriangle className="w-4 h-4 text-yellow-400" />
      case "low":
        return <Info className="w-4 h-4 text-blue-400" />
      default:
        return null
    }
  }

  return (
    <div className="p-4 space-y-4 overflow-auto h-full">
      <div className="flex items-center justify-between">
        <span className="text-sm text-gray-300">
          问题: {issues.length}
        </span>
        <button
          onClick={handleValidate}
          disabled={validating}
          className="px-3 py-1.5 bg-blue-600 hover:bg-blue-700 rounded text-sm disabled:opacity-50"
        >
          {validating ? "校验中..." : "重新校验"}
        </button>
      </div>

      {(["high", "medium", "low"] as const).map((severity) => (
        <div key={severity}>
          <button
            onClick={() => toggleGroup(severity)}
            className="flex items-center gap-2 w-full text-left py-2 border-b border-gray-700"
          >
            {collapsed[severity] ? (
              <ChevronRight className="w-4 h-4 text-gray-400" />
            ) : (
              <ChevronDown className="w-4 h-4 text-gray-400" />
            )}
            <span className="text-sm font-medium capitalize">{severity}</span>
            <span className="text-xs text-gray-500">({grouped[severity].length})</span>
          </button>
          {!collapsed[severity] && (
            <div className="space-y-2 mt-2">
              {grouped[severity].map((issue, i) => (
                <div
                  key={i}
                  className="p-3 bg-gray-800 border border-gray-700 rounded"
                >
                  <div className="flex items-start gap-2">
                    {severityIcon(severity)}
                    <div className="flex-1">
                      <p className="text-sm text-gray-200">{issue.description}</p>
                      <div className="flex flex-wrap gap-2 mt-1 text-xs text-gray-500">
                        <span>分类: {issue.category}</span>
                        <span>位置: {issue.location}</span>
                      </div>
                      {issue.suggestion && (
                        <p className="text-xs text-blue-400 mt-1">
                          建议: {issue.suggestion}
                        </p>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      ))}
    </div>
  )
}