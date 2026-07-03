import { useState, useCallback } from "react"
import { useProjectContext } from "../context/ProjectContext"

export function useSkeletonCRUD(projectId: string) {
  const { state } = useProjectContext()
  const [saving, setSaving] = useState(false)

  const save = useCallback(async () => {
    if (!state.project?.skeleton) return
    setSaving(true)
    try {
      // save functionality moved
    } finally {
      setSaving(false)
    }
  }, [projectId, state.project?.skeleton])

  return { save, saving }
}
