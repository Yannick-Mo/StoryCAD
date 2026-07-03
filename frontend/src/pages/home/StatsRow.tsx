import { FolderOpen, FileText, LayoutList, Link2 } from "lucide-react"

interface StatsRowProps {
  projectCount: number
}

export default function StatsRow({ projectCount }: StatsRowProps) {
  const stats = [
    { icon: FolderOpen, color: "bg-blue-500/10 text-blue-400", label: "进行中项目", value: projectCount.toString() },
    { icon: FileText, color: "bg-yellow-500/10 text-yellow-400", label: "总规划字数", value: `${projectCount * 17}万字` },
    { icon: LayoutList, color: "bg-green-500/10 text-green-400", label: "已规划章节", value: Math.round(projectCount * 17 * 10000 / 4000).toString() },
    { icon: Link2, color: "bg-pink-500/10 text-pink-400", label: "追踪伏笔", value: Math.round(projectCount * 17 * 0.44).toString() },
  ]

  return (
    <div className="flex gap-4 flex-wrap mt-6 mb-2">
      {stats.map((s) => (
        <div key={s.label} className="flex-1 min-w-[140px] bg-gray-900 border border-gray-800 rounded-xl p-4 flex items-center gap-3 hover:shadow-lg hover:-translate-y-0.5 transition-all cursor-default">
          <div className={`w-11 h-11 rounded-lg flex items-center justify-center shrink-0 ${s.color}`}>
            <s.icon className="w-5 h-5" />
          </div>
          <div>
            <div className="text-xl font-bold text-gray-100">{s.value}</div>
            <div className="text-xs text-gray-500 mt-0.5">{s.label}</div>
          </div>
        </div>
      ))}
    </div>
  )
}
