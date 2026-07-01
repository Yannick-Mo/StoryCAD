import { useProjectContext } from "../../context/ProjectContext"
import BranchTree from "../panels/BranchTree"
import { Clock, CheckCircle, AlertTriangle } from "lucide-react"

export default function BranchForeshadowView() {
  const { state } = useProjectContext()
  const skeleton = state.project?.skeleton
  const branches = skeleton?.branches ?? []
  const foreshadows = skeleton?.foreshadows ?? []

  return (
    <div className="p-4 space-y-6 overflow-auto h-full">
      <div>
        <h3 className="text-sm font-medium text-gray-300 mb-3">Branches</h3>
        {branches.length === 0 ? (
          <p className="text-xs text-gray-500">No branches defined</p>
        ) : (
          branches.map((branch, i) => (
            <div key={i} className="mb-3">
              <span className="text-xs text-gray-500 block mb-1">Branch {i + 1}</span>
              <BranchTree branch={branch} />
            </div>
          ))
        )}
      </div>
      <div>
        <h3 className="text-sm font-medium text-gray-300 mb-3">Foreshadows</h3>
        {foreshadows.length === 0 ? (
          <p className="text-xs text-gray-500">No foreshadows defined</p>
        ) : (
          foreshadows.map((f) => (
            <div
              key={f.id}
              className="p-3 bg-gray-800 border border-gray-700 rounded mb-2"
            >
              <div className="flex items-center justify-between mb-1">
                <span className="text-xs font-mono text-gray-400">{f.id}</span>
                <span
                  className={`text-xs px-2 py-0.5 rounded ${
                    f.status === "pending"
                      ? "bg-yellow-900 text-yellow-300"
                      : "bg-green-900 text-green-300"
                  }`}
                >
                  {f.status === "pending" ? (
                    <Clock className="w-3 h-3 inline mr-1" />
                  ) : (
                    <CheckCircle className="w-3 h-3 inline mr-1" />
                  )}
                  {f.status}
                </span>
              </div>
              <p className="text-sm text-gray-200 mb-1">{f.content}</p>
              <div className="flex gap-4 text-xs text-gray-500">
                <span>Planted: {f.planted_at}</span>
                <span>Recycle: {f.planned_recycle_interval}s</span>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  )
}
