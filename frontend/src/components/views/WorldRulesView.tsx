import { useProjectContext } from "../../context/ProjectContext"
import type { WorldRules } from "../../types/skeleton"
import { Plus, Trash2 } from "lucide-react"

export default function WorldRulesView() {
  const { state, dispatch } = useProjectContext()
  const worldRules = state.project?.skeleton?.world_rules
  const rules = worldRules?.rules ?? []

  function updateRules(value: WorldRules) {
    if (!state.project?.skeleton) return
    dispatch({ type: "UPDATE_SKELETON", payload: { key: "world_rules", value } })
  }

  function setHistory(history: string) {
    if (!worldRules) return
    updateRules({ ...worldRules, history })
  }

  function setForbiddenEvents(events: string[]) {
    if (!worldRules) return
    updateRules({ ...worldRules, forbidden_events: events })
  }

  function updateRule(index: number, field: string, val: string) {
    if (!worldRules) return
    const updated = [...rules]
    updated[index] = { ...updated[index], [field]: val }
    updateRules({ ...worldRules, rules: updated })
  }

  function addRule() {
    if (!worldRules) return
    updateRules({
      ...worldRules,
      rules: [...rules, { category: "", description: "", limitation: "" }],
    })
  }

  function removeRule(index: number) {
    if (!worldRules) return
    updateRules({ ...worldRules, rules: rules.filter((_, i) => i !== index) })
  }

  return (
    <div className="p-4 space-y-6 overflow-auto h-full">
      <div>
        <label className="block text-xs text-gray-400 mb-1">World History</label>
        <textarea
          value={worldRules?.history ?? ""}
          onChange={(e) => setHistory(e.target.value)}
          className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-sm resize-none"
          rows={4}
        />
      </div>
      <div>
        <div className="flex items-center justify-between mb-2">
          <span className="text-xs text-gray-400">Rules</span>
          <button
            onClick={addRule}
            className="flex items-center gap-1 px-2 py-1 bg-blue-600 hover:bg-blue-700 rounded text-xs"
          >
            <Plus className="w-3 h-3" /> Add Rule
          </button>
        </div>
        {rules.map((rule, i) => (
          <div key={i} className="mb-4 p-3 bg-gray-800 border border-gray-700 rounded space-y-2">
            <div className="flex justify-between">
              <span className="text-xs text-gray-500">Rule {i + 1}</span>
              <button onClick={() => removeRule(i)} className="text-red-400 hover:text-red-300">
                <Trash2 className="w-3 h-3" />
              </button>
            </div>
            <div>
              <label className="block text-xs text-gray-500 mb-1">Category</label>
              <select
                value={rule.category}
                onChange={(e) => updateRule(i, "category", e.target.value)}
                className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-sm"
              >
                <option value="">Select...</option>
                <option value="physics">Physics</option>
                <option value="magic">Magic</option>
                <option value="society">Society</option>
                <option value="character">Character</option>
              </select>
            </div>
            <div>
              <label className="block text-xs text-gray-500 mb-1">Description</label>
              <textarea
                value={rule.description}
                onChange={(e) => updateRule(i, "description", e.target.value)}
                className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-sm resize-none"
                rows={2}
              />
            </div>
            <div>
              <label className="block text-xs text-gray-500 mb-1">Limitation</label>
              <textarea
                value={rule.limitation}
                onChange={(e) => updateRule(i, "limitation", e.target.value)}
                className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-sm resize-none"
                rows={2}
              />
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}