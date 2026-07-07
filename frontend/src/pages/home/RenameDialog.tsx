import { useState, useEffect, useRef } from "react"

interface RenameDialogProps {
  open: boolean
  currentTitle: string
  onConfirm: (title: string) => void
  onCancel: () => void
}

export default function RenameDialog({ open, currentTitle, onConfirm, onCancel }: RenameDialogProps) {
  const [value, setValue] = useState(currentTitle)
  const inputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    if (open) {
      setValue(currentTitle)
      setTimeout(() => inputRef.current?.select(), 0)
    }
  }, [open, currentTitle])

  if (!open) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm" onClick={onCancel}>
      <div className="bg-gray-800 rounded-xl border border-gray-700 p-6 shadow-2xl w-80" onClick={e => e.stopPropagation()}>
        <h3 className="text-sm font-semibold text-gray-200 mb-4">重命名项目</h3>
        <input
          ref={inputRef}
          autoFocus
          value={value}
          onChange={e => setValue(e.target.value)}
          onKeyDown={e => { if (e.key === "Enter" && value.trim()) onConfirm(value.trim()) }}
          placeholder="输入项目名称..."
          className="w-full px-3 py-2 rounded-lg bg-gray-700 border border-gray-600 text-sm text-gray-100 placeholder-gray-500 outline-none focus:border-blue-500/50 mb-6"
        />
        <div className="flex justify-end gap-2">
          <button onClick={onCancel} className="px-3 py-1.5 rounded-lg text-xs text-gray-400 hover:bg-gray-700 transition-colors">取消</button>
          <button
            onClick={() => onConfirm(value.trim())}
            disabled={!value.trim()}
            className="px-3 py-1.5 rounded-lg text-xs text-white bg-blue-600 hover:bg-blue-500 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
          >保存</button>
        </div>
      </div>
    </div>
  )
}
