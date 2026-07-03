import React, { createContext, useContext, useReducer, type ReactNode } from "react"
import type { NarrativeSkeleton } from "../types/skeleton"

export interface ProjectData {
  id: string
  title: string
  description?: string
  status: string
  workflow_stage?: string
  created_at: string
  updated_at?: string
  skeleton?: NarrativeSkeleton | null
  validation_report?: any[] | null
}

interface State {
  project: ProjectData | null
  loading: boolean
  error: string | null
}

type Action =
  | { type: "SET_PROJECT"; payload: ProjectData }
  | { type: "SET_LOADING"; payload: boolean }
  | { type: "SET_ERROR"; payload: string | null }
  | { type: "UPDATE_SKELETON"; payload: { key: keyof NarrativeSkeleton; value: any } }

function reducer(state: State, action: Action): State {
  switch (action.type) {
    case "SET_PROJECT":
      return { ...state, project: action.payload, loading: false, error: null }
    case "SET_LOADING":
      return { ...state, loading: action.payload }
    case "SET_ERROR":
      return { ...state, error: action.payload, loading: false }
    case "UPDATE_SKELETON": {
      if (!state.project?.skeleton) return state
      return {
        ...state,
        project: {
          ...state.project,
          skeleton: {
            ...state.project.skeleton,
            [action.payload.key]: action.payload.value,
          },
        },
      }
    }
    default:
      return state
  }
}

const ProjectContext = createContext<{
  state: State
  dispatch: React.Dispatch<Action>
} | null>(null)

export function ProjectProvider({ children }: { children: ReactNode }) {
  const [state, dispatch] = useReducer(reducer, { project: null, loading: false, error: null })
  return (
    <ProjectContext.Provider value={{ state, dispatch }}>
      {children}
    </ProjectContext.Provider>
  )
}

export function useProjectContext() {
  const ctx = useContext(ProjectContext)
  if (!ctx) throw new Error("useProjectContext must be used within ProjectProvider")
  return ctx
}
