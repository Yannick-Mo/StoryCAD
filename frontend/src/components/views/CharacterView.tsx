import { useState } from "react"
import { useProjectContext } from "../../context/ProjectContext"
import { Plus, Trash2 } from "lucide-react"

export default function CharacterView() {
  const { state, dispatch } = useProjectContext()
  const characters = state.project?.skeleton?.characters ?? []
  const [selectedIndex, setSelectedIndex] = useState<number | null>(null)
  const selectedChar = selectedIndex !== null ? characters[selectedIndex] : null

  function updateChar(field: string, value: any) {
    if (selectedIndex === null) return
    const updated = characters.map((c, i) =>
      i === selectedIndex ? { ...c, [field]: value } : c
    )
    dispatch({ type: "UPDATE_SKELETON", payload: { key: "characters", value: updated } })
  }

  function updateDesire(field: string, value: string) {
    if (!selectedChar) return
    updateChar("desire_topology", {
      ...selectedChar.desire_topology,
      [field]: value,
    })
  }

  function updateRelationship(name: string, field: string, value: number) {
    if (!selectedChar) return
    const rels = { ...selectedChar.relationships }
    rels[name] = { ...(rels[name] ?? { 信任: 0, 威胁: 0, 吸引力: 0 }), [field]: value }
    updateChar("relationships", rels)
  }

  function addLanguageGene() {
    if (!selectedChar) return
    updateChar("language_genes", [...selectedChar.language_genes, ""])
  }

  function updateLanguageGene(index: number, value: string) {
    if (!selectedChar) return
    const genes = [...selectedChar.language_genes]
    genes[index] = value
    updateChar("language_genes", genes)
  }

  function removeLanguageGene(index: number) {
    if (!selectedChar) return
    const genes = selectedChar.language_genes.filter((_, i) => i !== index)
    updateChar("language_genes", genes)
  }

  function addCharacter() {
    const newChar = {
      name: "New Character",
      desire_topology: { 表层欲望: "", 深层需求: "", 核心恐惧: "" },
      bottom_line: "",
      vulnerability: "",
      language_genes: [],
      relationships: {},
      growth_arc: "",
    }
    dispatch({
      type: "UPDATE_SKELETON",
      payload: { key: "characters", value: [...characters, newChar] },
    })
    setSelectedIndex(characters.length)
  }

  return (
    <div className="flex h-full">
      <div className="w-48 border-r border-gray-700 overflow-auto">
        <div className="p-2 border-b border-gray-700">
          <button
            onClick={addCharacter}
            className="flex items-center gap-1 px-3 py-1.5 bg-blue-600 hover:bg-blue-700 rounded text-xs w-full justify-center"
          >
            <Plus className="w-3 h-3" /> Add
          </button>
        </div>
        {characters.map((c, i) => (
          <button
            key={i}
            onClick={() => setSelectedIndex(i)}
            className={`w-full text-left px-3 py-2 text-sm border-b border-gray-700 ${
              i === selectedIndex ? "bg-gray-700 text-blue-400" : "text-gray-300 hover:bg-gray-800"
            }`}
          >
            {c.name || "Unnamed"}
          </button>
        ))}
      </div>
      <div className="flex-1 overflow-auto p-4 space-y-4">
        {selectedChar ? (
          <>
            <div>
              <label className="block text-xs text-gray-400 mb-1">Name</label>
              <input
                value={selectedChar.name}
                onChange={(e) => updateChar("name", e.target.value)}
                className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-sm"
              />
            </div>
            <div>
              <label className="block text-xs text-gray-400 mb-1">表层欲望</label>
              <input
                value={selectedChar.desire_topology.表层欲望}
                onChange={(e) => updateDesire("表层欲望", e.target.value)}
                className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-sm"
              />
            </div>
            <div>
              <label className="block text-xs text-gray-400 mb-1">深层需求</label>
              <input
                value={selectedChar.desire_topology.深层需求}
                onChange={(e) => updateDesire("深层需求", e.target.value)}
                className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-sm"
              />
            </div>
            <div>
              <label className="block text-xs text-gray-400 mb-1">核心恐惧</label>
              <input
                value={selectedChar.desire_topology.核心恐惧}
                onChange={(e) => updateDesire("核心恐惧", e.target.value)}
                className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-sm"
              />
            </div>
            <div>
              <label className="block text-xs text-gray-400 mb-1">Bottom Line</label>
              <input
                value={selectedChar.bottom_line}
                onChange={(e) => updateChar("bottom_line", e.target.value)}
                className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-sm"
              />
            </div>
            <div>
              <label className="block text-xs text-gray-400 mb-1">Vulnerability</label>
              <input
                value={selectedChar.vulnerability}
                onChange={(e) => updateChar("vulnerability", e.target.value)}
                className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-sm"
              />
            </div>
            <div>
              <label className="block text-xs text-gray-400 mb-1">Language Genes</label>
              {selectedChar.language_genes.map((gene, gi) => (
                <div key={gi} className="flex gap-2 mb-1">
                  <input
                    value={gene}
                    onChange={(e) => updateLanguageGene(gi, e.target.value)}
                    className="flex-1 bg-gray-700 border border-gray-600 rounded px-3 py-2 text-sm"
                  />
                  <button onClick={() => removeLanguageGene(gi)} className="text-red-400 hover:text-red-300">
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              ))}
              <button
                onClick={addLanguageGene}
                className="text-xs text-blue-400 hover:text-blue-300 mt-1"
              >
                + Add gene
              </button>
            </div>
            <div>
              <label className="block text-xs text-gray-400 mb-1">Growth Arc</label>
              <textarea
                value={selectedChar.growth_arc}
                onChange={(e) => updateChar("growth_arc", e.target.value)}
                className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-sm resize-none"
                rows={4}
              />
            </div>
            <div>
              <label className="block text-xs text-gray-400 mb-1">Relationships</label>
              {Object.entries(selectedChar.relationships).map(([name, rel]) => (
                <div key={name} className="mb-2 p-2 bg-gray-750 rounded border border-gray-600">
                  <span className="text-sm text-gray-300">{name}</span>
                  <div className="grid grid-cols-3 gap-2 mt-1">
                    <div>
                      <span className="text-xs text-gray-500">信任</span>
                      <input
                        type="range" min={0} max={100}
                        value={rel.信任}
                        onChange={(e) => updateRelationship(name, "信任", Number(e.target.value))}
                        className="w-full accent-blue-500"
                      />
                    </div>
                    <div>
                      <span className="text-xs text-gray-500">威胁</span>
                      <input
                        type="range" min={0} max={100}
                        value={rel.威胁}
                        onChange={(e) => updateRelationship(name, "威胁", Number(e.target.value))}
                        className="w-full accent-blue-500"
                      />
                    </div>
                    <div>
                      <span className="text-xs text-gray-500">吸引力</span>
                      <input
                        type="range" min={0} max={100}
                        value={rel.吸引力}
                        onChange={(e) => updateRelationship(name, "吸引力", Number(e.target.value))}
                        className="w-full accent-blue-500"
                      />
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </>
        ) : (
          <div className="text-gray-500 text-sm">Select a character to edit</div>
        )}
      </div>
    </div>
  )
}