import { useState } from "react"
import { useNavigate } from "react-router-dom"
import type { ProjectListItem, HomeProject } from "../../types/project"
import { COVER_GRADIENTS, PROGRESS_CLASSES } from "../../types/project"

const STAGE_MAP: Record<string, { label: string; type: "progress" | "done" }> = {
  init: { label: "结构设计中", type: "progress" },
  draft: { label: "情节填充中", type: "progress" },
  revising: { label: "校验中", type: "progress" },
  final: { label: "已完成", type: "done" },
}

const TEMPLATES = ["三幕式", "四幕结构", "英雄之旅", "救猫咪", "网文爽文节奏"]

function enrichProject(p: ProjectListItem, index: number): HomeProject {
  const stage = STAGE_MAP[p.status] ?? STAGE_MAP.init
  return {
    ...p,
    coverClass: COVER_GRADIENTS[index % COVER_GRADIENTS.length],
    coverChar: p.title.charAt(0),
    words: "—",
    template: TEMPLATES[index % TEMPLATES.length],
    time: index === 0 ? "刚刚" : `${index + 1}天前`,
    stage: stage.label,
    stageType: stage.type,
    progress: p.status === "final" ? 100 : p.status === "revising" ? 75 : p.status === "draft" ? 40 : 10,
    progressClass: PROGRESS_CLASSES[index % PROGRESS_CLASSES.length],
    updated: new Date(Date.now() - index * 24 * 60 * 60 * 1000),
  }
}

interface ProjectGridProps {
  projects: ProjectListItem[]
  searchQuery: string
  loading: boolean
  onDeleteProject: (id: string) => void
}

export default function ProjectGrid({ projects, searchQuery, loading, onDeleteProject }: ProjectGridProps) {
  const [activeFilter, setActiveFilter] = useState("all")
  const [deleting, setDeleting] = useState<string | null>(null)
  const navigate = useNavigate()

  const enriched = projects.map((p, i) => enrichProject(p, i))

  const filtered = enriched.filter((p) => {
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase()
      if (!p.title.toLowerCase().includes(q) && !p.template.toLowerCase().includes(q) && !p.stage.toLowerCase().includes(q)) return false
    }
    if (activeFilter === "progress") return p.stageType === "progress"
    if (activeFilter === "done") return p.stageType === "done"
    if (activeFilter === "recent") {
      const diff = Date.now() - p.updated.getTime()
      return diff / (1000 * 60 * 60 * 24) <= 7
    }
    return true
  })

  const filters = [
    { key: "all", label: "全部" },
    { key: "progress", label: "进行中" },
    { key: "done", label: "已完成" },
    { key: "recent", label: "最近一周" },
  ]

  return (
    <section>
      <div className="flex items-center justify-between flex-wrap gap-3 mt-8 mb-4">
        <h2 className="text-lg font-bold text-gray-100 flex items-center gap-2">
          <span>📂</span> 继续创作
        </h2>
        <div className="flex items-center gap-2">
          <div className="flex gap-1.5">
            {filters.map((f) => (
              <button
                key={f.key}
                onClick={() => setActiveFilter(f.key)}
                className={`px-3.5 py-1.5 rounded-full text-xs font-medium border transition-all ${
                  activeFilter === f.key
                    ? "bg-blue-600 border-blue-600 text-white"
                    : "bg-gray-800 border-gray-700 text-gray-400 hover:border-gray-600 hover:text-gray-200"
                }`}
              >
                {f.label}
              </button>
            ))}
          </div>
          <span className="text-xs text-blue-400 ml-2 opacity-50">
            全部项目
          </span>
        </div>
      </div>

      {loading ? (
        <div className="text-center py-12 text-gray-500">加载中...</div>
      ) : filtered.length === 0 ? (
        <div className="text-center py-12 bg-gray-900 rounded-2xl border-2 border-dashed border-gray-800">
          <div className="text-4xl mb-2 opacity-70">📭</div>
          <div className="text-sm text-gray-400 font-medium">没有找到匹配的项目</div>
          <div className="text-xs text-gray-500 mt-1">试试调整搜索词或筛选条件</div>
        </div>
      ) : (
        <div className="grid grid-cols-[repeat(auto-fill,minmax(270px,1fr))] gap-4">
          {filtered.map((proj, i) => (
              <div
                key={proj.id}
                onClick={() => navigate(`/projects/${proj.id}`)}
                className="relative bg-gray-900 border border-gray-800 rounded-2xl cursor-pointer overflow-hidden transition-all hover:shadow-xl hover:-translate-y-1 active:scale-[0.98] group"
                style={{ animation: `fadeInUp 0.5s ease ${i * 0.06}s forwards`, opacity: 0 }}
              >
                <div className={`h-24 flex items-center justify-center text-white text-3xl font-bold relative overflow-hidden ${proj.coverClass}`}>
                  {proj.coverChar}
                  <span className={`absolute top-3 right-3 text-[10px] font-semibold px-2 py-0.5 rounded-full backdrop-blur-sm ${
                    proj.stageType === "done" ? "bg-green-500/80" : "bg-blue-500/80"
                  }`}>
                    {proj.stage}
                  </span>
                </div>
                <button
                  onClick={(e) => { e.stopPropagation(); onDeleteProject(proj.id) }}
                  className="absolute top-1 left-1 w-6 h-6 flex items-center justify-center rounded-full bg-black/50 text-white/0 group-hover:text-white/70 hover:!text-red-400 text-xs transition-all opacity-0 group-hover:opacity-100"
                  title="删除项目"
                >
                  ✕
                </button>
                <div className="p-4 flex flex-col gap-1.5">
                  <div className="font-bold text-sm text-gray-100">《{proj.title}》</div>
                  <div className="flex gap-3 text-xs text-gray-500">
                    <span>📏 {proj.words}</span>
                    <span>📐 {proj.template}</span>
                    <span>🕐 {proj.time}</span>
                  </div>
                  <div className="h-1 bg-gray-800 rounded-full mt-1 overflow-hidden">
                    <div className={`h-full rounded-full transition-all duration-500 ${proj.progressClass === "purple" ? "bg-purple-400" : proj.progressClass === "blue" ? "bg-blue-400" : proj.progressClass === "pink" ? "bg-pink-400" : proj.progressClass === "gold" ? "bg-yellow-400" : "bg-green-400"}`}
                      style={{ width: `${proj.progress}%` }}
                    />
                  </div>
                </div>
              </div>
          ))}
        </div>
      )}
      <style>{`
        @keyframes fadeInUp { from { opacity: 0; transform: translateY(16px); } to { opacity: 1; transform: translateY(0); } }
      `}</style>
    </section>
  )
}
