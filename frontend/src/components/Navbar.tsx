import { Save, Download, RotateCcw, FileText, ChevronDown } from "lucide-react"

interface NavbarProps {
  projectId?: string
  onSave?: () => void
  onRegenerate?: () => void
  onExport?: (format: "json" | "markdown") => void
  saving?: boolean
}

export default function Navbar({ projectId, onSave, onRegenerate, onExport, saving }: NavbarProps) {
  return (
    <nav className="flex items-center justify-between bg-gray-800 border-b border-gray-700 px-4 py-2 text-gray-100">
      <div className="flex items-center gap-3">
        <FileText className="w-5 h-5 text-blue-400" />
        <span className="font-bold text-lg">Story-Forge</span>
        {projectId && (
          <span className="text-sm text-gray-400 ml-2">项目: {projectId}</span>
        )}
      </div>
      <div className="flex items-center gap-2">
        {onSave && (
          <button
            onClick={onSave}
            disabled={saving}
            className="flex items-center gap-1 px-3 py-1.5 bg-blue-600 hover:bg-blue-700 rounded text-sm disabled:opacity-50"
          >
            <Save className="w-4 h-4" />
            {saving ? "保存中..." : "保存"}
          </button>
        )}
        {onRegenerate && (
          <button
            onClick={onRegenerate}
            className="flex items-center gap-1 px-3 py-1.5 bg-gray-700 hover:bg-gray-600 rounded text-sm"
          >
            <RotateCcw className="w-4 h-4" />
            重新生成
          </button>
        )}
        {onExport && (
          <div className="relative group">
            <button className="flex items-center gap-1 px-3 py-1.5 bg-gray-700 hover:bg-gray-600 rounded text-sm">
              <Download className="w-4 h-4" />
              导出
              <ChevronDown className="w-3 h-3" />
            </button>
            <div className="absolute right-0 mt-1 w-40 bg-gray-700 border border-gray-600 rounded shadow-lg opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all z-50">
              <button
                onClick={() => onExport("json")}
                className="block w-full text-left px-4 py-2 text-sm hover:bg-gray-600"
              >
                导出 JSON
              </button>
              <button
                onClick={() => onExport("markdown")}
                className="block w-full text-left px-4 py-2 text-sm hover:bg-gray-600"
              >
                导出 Markdown
              </button>
            </div>
          </div>
        )}
      </div>
    </nav>
  )
}
