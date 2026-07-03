import { useState } from "react"
import { useNavigate } from "react-router-dom"
import { Lightbulb, FileText, Upload } from "lucide-react"
import { createProject } from "../../api/client"

const CARDS = [
  { icon: Lightbulb, label: "从脑洞开始", desc: "把零碎的灵感倒进来，AI 帮你梳理成清晰的故事骨架", mode: "brainstorm", primary: true },
  { icon: FileText, label: "从模板开始", desc: "选择经典叙事结构模板，快速搭建专业框架", mode: "template", primary: false },
  { icon: Upload, label: "导入文档", desc: "上传已有大纲或文稿，自动提取关键信息", mode: "import", primary: false },
]

export default function CreateCards() {
  const [creating, setCreating] = useState(false)
  const navigate = useNavigate()

  async function handleClick(mode: string) {
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
    <section>
      <div className="flex items-center gap-2 mt-8 mb-4">
        <h2 className="text-lg font-bold text-gray-100 flex items-center gap-2">
          <span>✨</span> 开始新创作
        </h2>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {CARDS.map((c) => (
          <div
            key={c.mode}
            onClick={() => handleClick(c.mode)}
            className={`rounded-2xl p-6 text-center cursor-pointer transition-all hover:-translate-y-1 active:scale-[0.97] ${
              c.primary
                ? "bg-gradient-to-b from-gray-800 to-gray-900 border-2 border-blue-800/40 hover:border-blue-500/60"
                : "bg-gray-900 border-2 border-dashed border-gray-800 hover:border-gray-600"
            }`}
          >
            <div className={`w-14 h-14 rounded-full flex items-center justify-center mx-auto mb-3 transition-transform group-hover:scale-105 ${
              c.mode === "brainstorm" ? "bg-blue-500/10 text-blue-400" :
              c.mode === "template" ? "bg-yellow-500/10 text-yellow-400" :
              "bg-green-500/10 text-green-400"
            }`}>
              <c.icon className="w-7 h-7" />
            </div>
            <div className="font-bold text-sm text-gray-100 mb-1">{c.label}</div>
            <div className="text-xs text-gray-500 leading-relaxed">{c.desc}</div>
          </div>
        ))}
      </div>
    </section>
  )
}
