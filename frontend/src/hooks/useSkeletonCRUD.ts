import { useState, useCallback } from "react"
import { updateSkeleton } from "../api/client"
import { useProjectContext } from "../context/ProjectContext"
import type { NarrativeSkeleton } from "../types/skeleton"

export function useSkeletonCRUD(projectId: string) {
  const { state } = useProjectContext()
  const [saving, setSaving] = useState(false)

  const save = useCallback(async () => {
    if (!state.project?.skeleton) return
    setSaving(true)
    try {
      await updateSkeleton(projectId, state.project.skeleton)
    } finally {
      setSaving(false)
    }
  }, [projectId, state.project?.skeleton])

  return { save, saving }
}
