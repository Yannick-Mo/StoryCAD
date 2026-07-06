import { Plus } from "lucide-react"

interface Props {
  onCreateClick: () => void
}

export default function CreateCards({ onCreateClick }: Props) {

  return (
    <section>
      <div className="flex items-center gap-2 mt-8 mb-4">
        <h2 className="text-lg font-bold text-gray-100 flex items-center gap-2">
          <span>✨</span> 开始新创作
        </h2>
      </div>
      <button
        onClick={onCreateClick}
        className="w-full rounded-2xl p-8 border-2 border-dashed border-gray-800 hover:border-blue-500/40 bg-gray-900/50 hover:bg-gray-900 transition-all cursor-pointer group"
      >
        <div className="flex flex-col items-center gap-3">
          <div className="w-16 h-16 rounded-full bg-blue-500/10 text-blue-400 flex items-center justify-center group-hover:scale-110 transition-transform">
            <Plus className="w-8 h-8" />
          </div>
          <div className="font-bold text-lg text-gray-300 group-hover:text-gray-100 transition-colors">创建新项目</div>
          <div className="text-sm text-gray-600">空项目 / 从素材导入</div>
        </div>
      </button>
    </section>
  )
}
