interface ConfirmDialogProps {
  open: boolean
  title: string
  message: string
  confirmText?: string
  cancelText?: string
  onConfirm: () => void
  onCancel: () => void
}

export default function ConfirmDialog({
  open, title, message,
  confirmText = '确认删除',
  cancelText = '取消',
  onConfirm, onCancel,
}: ConfirmDialogProps) {
  if (!open) return null
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm" onClick={onCancel}>
      <div className="bg-gray-800 rounded-xl border border-gray-700 p-6 shadow-2xl w-80" onClick={e => e.stopPropagation()}>
        <h3 className="text-sm font-semibold text-gray-200 mb-2">{title}</h3>
        <p className="text-xs text-gray-400 mb-6">{message}</p>
        <div className="flex justify-end gap-2">
          <button onClick={onCancel} className="px-3 py-1.5 rounded-lg text-xs text-gray-400 hover:bg-gray-700 transition-colors">
            {cancelText}
          </button>
          <button onClick={onConfirm} className="px-3 py-1.5 rounded-lg text-xs text-white bg-red-600 hover:bg-red-500 transition-colors">
            {confirmText}
          </button>
        </div>
      </div>
    </div>
  )
}
