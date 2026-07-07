import { useState } from 'react'
import { checkConsistency, type ConsistencyReport } from '../../../api/consistency'

interface Props {
  projectId: string
  onClose: () => void
  onNavigate?: (location: { entity_id?: string; chapter_id?: string }) => void
}

export default function ConsistencyCheckModal({ projectId, onClose, onNavigate }: Props) {
  const [loading, setLoading] = useState(false)
  const [report, setReport] = useState<ConsistencyReport | null>(null)

  const handleCheck = async () => {
    setLoading(true)
    try {
      const result = await checkConsistency(projectId)
      setReport(result)
    } catch (e) {
      console.error('Consistency check failed:', e)
    } finally {
      setLoading(false)
    }
  }

  const severityIcon = (s: string) => {
    if (s === 'high' || s === 'critical') return '🔴'
    if (s === 'medium' || s === 'warning') return '🟡'
    return '🟢'
  }

  return (
    <div className="fixed inset-0 bg-gray-950/80 backdrop-blur-sm z-50 flex items-center justify-center" onClick={onClose}>
      <div className="bg-gray-900 border border-gray-700 rounded-2xl w-[520px] max-h-[80vh] overflow-y-auto shadow-2xl" onClick={e => e.stopPropagation()}>
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-700">
          <h2 className="text-lg font-semibold text-white">✅ 一致性检查</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-white text-xl leading-none">&times;</button>
        </div>

        <div className="p-6">
          {!report && !loading && (
            <div className="text-center py-8">
              <p className="text-sm text-gray-400 mb-4">检查角色一致性、时间线逻辑、世界观冲突</p>
              <button
                onClick={handleCheck}
                className="px-6 py-2 rounded-full text-sm bg-gradient-to-r from-amber-700/80 to-amber-600/80 border border-amber-500/50 text-white hover:from-amber-600 hover:to-amber-500 transition-all"
              >
                开始检查
              </button>
            </div>
          )}

          {loading && (
            <div className="text-center py-8">
              <div className="inline-block w-6 h-6 border-2 border-amber-500 border-t-transparent rounded-full animate-spin mb-3" />
              <p className="text-sm text-gray-400">正在检查...</p>
            </div>
          )}

          {report && (
            <>
              <div className="mb-4 p-3 rounded-lg bg-gray-800/60">
                <p className="text-sm text-gray-300">{report.summary}</p>
              </div>
              <div className="space-y-2">
                {report.issues.map((issue, i) => {
                  const loc = issue.chapter_id ? { chapter_id: issue.chapter_id } : issue.entity_id ? { entity_id: issue.entity_id } : null
                  return (
                    <div key={i} className="p-3 rounded-lg bg-gray-800/40 border border-gray-700/50">
                      <div className="flex items-start gap-2">
                        <span className="text-sm mt-0.5">{severityIcon(issue.severity)}</span>
                        <div className="flex-1 min-w-0">
                          <p className="text-sm font-medium text-gray-200">
                            [{issue.check_type}] {issue.entity_type}: {issue.description}
                          </p>
                          {issue.suggestion && (
                            <p className="text-xs text-gray-400 mt-0.5">💡 {issue.suggestion}</p>
                          )}
                        </div>
                        {loc && onNavigate && (
                          <button
                            onClick={() => onNavigate(loc!)}
                            className="text-xs text-amber-500 hover:text-amber-400 whitespace-nowrap"
                          >
                            定位到
                          </button>
                        )}
                      </div>
                    </div>
                  )
                })}
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  )
}
