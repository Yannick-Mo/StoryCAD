import type { Branch } from "../../types/skeleton"

interface BranchTreeProps {
  branch: Branch
}

export default function BranchTree({ branch }: BranchTreeProps) {
  return (
    <div className="p-3 bg-gray-800 border border-gray-700 rounded text-sm space-y-2">
      <div>
        <span className="text-xs text-gray-500">Divergence Point:</span>
        <p className="text-gray-200">{branch.divergence_point}</p>
      </div>
      <div>
        <span className="text-xs text-gray-500">Paths:</span>
        {branch.paths.map((path, pi) => (
          <div key={pi} className="ml-2 mt-1 text-gray-300">
            <span className="text-xs text-blue-400">Path {pi + 1}:</span>{" "}
            {path.join(" ? ")}
          </div>
        ))}
      </div>
      {branch.convergence_point && (
        <div>
          <span className="text-xs text-gray-500">Convergence Point:</span>
          <p className="text-gray-200">{branch.convergence_point}</p>
        </div>
      )}
    </div>
  )
}
