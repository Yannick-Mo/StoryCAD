import { useState, useEffect, useCallback } from "react"
import HomeNavbar from "./HomeNavbar"
import AnnouncementBanner from "./AnnouncementBanner"
import HeroSection from "./HeroSection"
import StatsRow from "./StatsRow"
import ProjectGrid from "./ProjectGrid"
import CreateCards from "./CreateCards"
import CreateProjectDialog from "./CreateProjectDialog"
import TemplateGrid from "./TemplateGrid"
import Footer from "./Footer"
import { listProjects, deleteProject } from "../../api/auth"
import type { ProjectListItem } from "../../types/project"
import ConfirmDialog from "../editor/components/ConfirmDialog"
import { useToast } from "../editor/components/Toast"

export default function ProjectListPage() {
  const [projects, setProjects] = useState<ProjectListItem[]>([])
  const [loading, setLoading] = useState(true)
  const [searchQuery, setSearchQuery] = useState("")
  const [createOpen, setCreateOpen] = useState(false)
  const [deleteTarget, setDeleteTarget] = useState<string | null>(null)
  const { addToast } = useToast()

  const fetchProjects = useCallback(() => {
    setLoading(projects.length === 0)
    listProjects(1, 50, searchQuery)
      .then((data) => setProjects(data.items ?? data))
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [searchQuery])

  useEffect(() => { fetchProjects() }, [fetchProjects])

  const handleConfirmDelete = useCallback(async () => {
    if (!deleteTarget) return
    try {
      await deleteProject(deleteTarget)
      setProjects(prev => prev.filter(p => p.id !== deleteTarget))
    } catch {
      addToast("删除失败，请重试", "error")
    } finally {
      setDeleteTarget(null)
    }
  }, [deleteTarget])

  const handleDelete = useCallback((id: string) => {
    setDeleteTarget(id)
  }, [])

  return (
    <div className="min-h-screen bg-gray-950 text-gray-100">
      <HomeNavbar searchQuery={searchQuery} onSearchChange={setSearchQuery} onCreateClick={() => setCreateOpen(true)} />
      <AnnouncementBanner />
      <div className="max-w-5xl mx-auto px-6 pb-12">
        <HeroSection />
        <CreateCards onCreateClick={() => setCreateOpen(true)} />
        <StatsRow projectCount={projects.length} />
        <ProjectGrid projects={projects} loading={loading} onDeleteProject={handleDelete} />
        <TemplateGrid />
        <Footer />
      </div>
      <CreateProjectDialog open={createOpen} onClose={() => setCreateOpen(false)} />
      <ConfirmDialog
        open={deleteTarget !== null}
        title="删除项目"
        message="确定要删除该项目吗？此操作不可恢复。"
        confirmText="确认删除"
        cancelText="取消"
        onConfirm={handleConfirmDelete}
        onCancel={() => setDeleteTarget(null)}
      />
    </div>
  )
}
