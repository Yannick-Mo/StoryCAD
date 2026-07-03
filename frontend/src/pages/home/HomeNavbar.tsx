import { useState, useEffect } from "react"
import { useNavigate } from "react-router-dom"
import { Search, Plus } from "lucide-react"
import { createProject } from "../../api/client"

interface HomeNavbarProps {
  searchQuery: string
  onSearchChange: (val: string) => void
}

export default function HomeNavbar({ searchQuery, onSearchChange }: HomeNavbarProps) {
  const [creating, setCreating] = useState(false)
  const navigate = useNavigate()

  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      if ((e.ctrlKey && e.key === "k") || (e.key === "/" && !["INPUT", "TEXTAREA"].includes((e.target as HTMLElement).tagName))) {
        e.preventDefault()
        document.getElementById("homeSearch")?.focus()
      }
    }
    document.addEventListener("keydown", handleKeyDown)
    return () => document.removeEventListener("keydown", handleKeyDown)
  }, [])

  async function handleCreate() {
    if (creating) return
    const title = prompt("请输入项目名称：")
    if (!title?.trim()) return
    setCreating(true)
    try {
      const result = await createProject(title.trim())
      navigate(`/projects/${result.id}`)
    } catch {
      setCreating(false)
    }
  }

  return (
    <nav className="sticky top-0 z-50 bg-gray-900/80 backdrop-blur-xl border-b border-gray-800 px-6 h-14 flex items-center gap-4">
      <a href="/" className="flex items-center gap-2 text-blue-400 font-bold text-lg no-underline shrink-0 hover:opacity-85 transition-opacity">
        <svg viewBox="0 0 24 24" fill="currentColor" className="w-6 h-6">
          <path d="M12 2L2 7v10c0 5.55 3.84 10.74 9 12 5.16-1.26 9-6.45 9-12V7l-10-5zm0 2.18l7 3.5v6.72c0 4.17-2.69 8.08-7 9.08-4.31-1-7-4.91-7-9.08V7.68l7-3.5z"/>
        </svg>
        StoryCAD
      </a>
      <div className="relative flex-1 max-w-xs ml-auto">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500 pointer-events-none" />
        <input
          id="homeSearch"
          type="text"
          value={searchQuery}
          onChange={(e) => onSearchChange(e.target.value)}
          placeholder="搜索项目..."
          className="w-full pl-9 pr-3 py-2 bg-gray-800 border border-gray-700 rounded-full text-sm text-gray-100 placeholder-gray-500 outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 transition-all"
        />
      </div>
      <button
        onClick={handleCreate}
        disabled={creating}
        className="flex items-center gap-1.5 px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white text-sm font-semibold rounded-full transition-all hover:shadow-lg hover:shadow-blue-600/30 active:scale-95"
      >
        <Plus className="w-4 h-4" />
        新建项目
      </button>
      <div className="w-8 h-8 rounded-full bg-gradient-to-br from-purple-400 to-blue-500 flex items-center justify-center text-white text-xs font-bold shrink-0 cursor-pointer hover:scale-105 transition-transform border-2 border-transparent hover:border-blue-400">
        柳
      </div>
    </nav>
  )
}
