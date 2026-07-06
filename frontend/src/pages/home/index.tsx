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

export default function ProjectListPage() {
  const [projects, setProjects] = useState<ProjectListItem[]>([])
  const [loading, setLoading] = useState(true)
  const [searchQuery, setSearchQuery] = useState("")
  const [createOpen, setCreateOpen] = useState(false)

  const fetchProjects = useCallback(() => {
    setLoading(projects.length === 0)
    listProjects()
      .then((data) => setProjects(data))
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => { fetchProjects() }, [fetchProjects])

  const handleDelete = useCallback(async (id: string) => {
    if (!window.confirm("确定要删除该项目吗？此操作不可恢复。")) return
    try {
      await deleteProject(id)
      setProjects(prev => prev.filter(p => p.id !== id))
    } catch {
      alert("删除失败，请重试")
    }
  }, [])

  return (
    <div className="min-h-screen bg-gray-950 text-gray-100">
      <HomeNavbar searchQuery={searchQuery} onSearchChange={setSearchQuery} onCreateClick={() => setCreateOpen(true)} />
      <AnnouncementBanner />
      <div className="max-w-5xl mx-auto px-6 pb-12">
        <HeroSection />
        <StatsRow projectCount={projects.length} />
        <ProjectGrid projects={projects} searchQuery={searchQuery} loading={loading} onDeleteProject={handleDelete} />
        <CreateCards onCreateClick={() => setCreateOpen(true)} />
        <TemplateGrid />
        <Footer />
      </div>
      <CreateProjectDialog open={createOpen} onClose={() => setCreateOpen(false)} />
    </div>
  )
}
