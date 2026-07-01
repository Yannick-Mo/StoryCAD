import type { NarrativeSkeleton, ValidationIssue } from "./skeleton"

export interface Project {
  project_id: string
  status: "pending" | "completed" | "failed"
  skeleton: NarrativeSkeleton | null
  validation_report: ValidationIssue[] | null
}

export interface SkeletonVersion {
  version: number
  skeleton: NarrativeSkeleton
  validation_report: ValidationIssue[] | null
  created_at: string
}

export interface ProjectListItem {
  project_id: string
  status: "pending" | "completed" | "failed"
  created_at: string
}
