import { useEffect, useState, useRef } from "react"
import { getProject } from "../api/client"
import { useProjectContext } from "../context/ProjectContext"
import type { Project } from "../types/project"

export function useProject(projectId: string) {
  const { state, dispatch } = useProjectContext()
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const pollingRef = useRef<ReturnType<typeof setInterval>>()

  useEffect(() => {
    let cancelled = false

    async function fetchProject() {
      try {
        setLoading(true)
        const data = await getProject(projectId)
        if (!cancelled) {
          const project = data.project as Project
          dispatch({ type: "SET_PROJECT", payload: project })
          setLoading(false)
          setError(null)
          if (project.status === "pending") {
            startPolling()
          } else {
            stopPolling()
          }
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Failed to load project")
          setLoading(false)
          stopPolling()
        }
      }
    }

    function startPolling() {
      stopPolling()
      pollingRef.current = setInterval(async () => {
        try {
          const data = await getProject(projectId)
          const project = data.project as Project
          dispatch({ type: "SET_PROJECT", payload: project })
          if (project.status !== "pending") {
            stopPolling()
          }
        } catch {
          stopPolling()
        }
      }, 3000)
    }

    function stopPolling() {
      if (pollingRef.current) {
        clearInterval(pollingRef.current)
        pollingRef.current = undefined
      }
    }

    fetchProject()

    return () => {
      cancelled = true
      stopPolling()
    }
  }, [projectId, dispatch])

  return {
    project: state.project,
    loading,
    error,
    refresh: () => {
      // re-mount effect by changing key handled externally
    },
  }
}
