import { useState, useEffect } from "react"
import { useNavigate } from "react-router-dom"
import { listProjects, createProject } from "../api/client"
import type { ProjectListItem } from "../types/project"
import { FileText, Plus, Loader2 } from "lucide-react"

export default function ProjectListPage() {
  const [input, setInput] = useState("")
  const [projects, setProjects] = useState<ProjectListItem[]>([])
  const [loading, setLoading] = useState(true)
  const [creating, setCreating] = useState(false)
  const navigate = useNavigate()

  useEffect(() => {
    async function fetchProjects() {
      try {
        const data = await listProjects()
        setProjects(data as ProjectListItem[])
      } catch {
        // ignore
      } finally {
        setLoading(false)
      }
    }
    fetchProjects()
  }, [])

  async function handleCreate() {
    if (!input.trim() || creating) return
    setCreating(true)
    try {
      const result = await createProject(input)
      navigate(`/projects/${result.project_id}`)
    } catch {
      setCreating(false)
    }
  }

  return (
    <div className="min-h-screen bg-gray-900 text-gray-100 flex flex-col items-center justify-center p-8">
      <div className="max-w-lg w-full space-y-8">
        <div className="text-center">
          <FileText className="w-12 h-12 text-blue-400 mx-auto mb-4" />
          <h1 className="text-3xl font-bold">Story-Forge</h1>
          <p className="text-gray-400 mt-2">从你的创意生成故事骨架</p>
        </div>

        <div className="space-y-3">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="输入你的故事创意..."
            className="w-full h-32 bg-gray-800 border border-gray-700 rounded-lg px-4 py-3 text-sm resize-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
          />
          <button
            onClick={handleCreate}
            disabled={!input.trim() || creating}
            className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-blue-600 hover:bg-blue-700 rounded-lg text-sm font-medium disabled:opacity-50 transition-colors"
          >
            {creating ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Plus className="w-4 h-4" />
            )}
            {creating ? "生成中..." : "开始生成"}
          </button>
        </div>

        <div>
          <h2 className="text-sm font-medium text-gray-400 mb-3">已有项目</h2>
          {loading ? (
            <div className="flex justify-center py-8">
              <Loader2 className="w-6 h-6 animate-spin text-gray-400" />
            </div>
          ) : projects.length === 0 ? (
            <p className="text-sm text-gray-500 text-center py-8">暂无项目</p>
          ) : (
            <div className="space-y-2">
              {projects.map((p) => (
                <button
                  key={p.project_id}
                  onClick={() => navigate(`/projects/${p.project_id}`)}
                  className="w-full flex items-center justify-between px-4 py-3 bg-gray-800 hover:bg-gray-750 rounded-lg border border-gray-700 transition-colors"
                >
                  <span className="text-sm font-mono">{p.project_id.slice(0, 8)}...</span>
                  <div className="flex items-center gap-2">
                    <span
                      className={`text-xs px-2 py-0.5 rounded ${
                        p.status === "completed"
                          ? "bg-green-900 text-green-300"
                          : p.status === "pending"
                          ? "bg-yellow-900 text-yellow-300"
                          : "bg-red-900 text-red-300"
                      }`}
                    >
                      {p.status}
                    </span>
                    <span className="text-xs text-gray-500">{new Date(p.created_at).toLocaleDateString()}</span>
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}