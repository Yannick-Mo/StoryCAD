import { useState, useEffect } from "react"
import HomeNavbar from "./HomeNavbar"
import AnnouncementBanner from "./AnnouncementBanner"
import HeroSection from "./HeroSection"
import StatsRow from "./StatsRow"
import ProjectGrid from "./ProjectGrid"
import CreateCards from "./CreateCards"
import TemplateGrid from "./TemplateGrid"
import Footer from "./Footer"
import { listProjects } from "../../api/client"
import type { ProjectListItem } from "../../types/project"

export default function ProjectListPage() {
  const [projects, setProjects] = useState<ProjectListItem[]>([])
  const [loading, setLoading] = useState(true)
  const [searchQuery, setSearchQuery] = useState("")

  useEffect(() => {
    listProjects()
      .then((data) => setProjects(data))
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  return (
    <div className="min-h-screen bg-gray-950 text-gray-100">
      <HomeNavbar searchQuery={searchQuery} onSearchChange={setSearchQuery} />
      <AnnouncementBanner />
      <div className="max-w-5xl mx-auto px-6 pb-12">
        <HeroSection />
        <StatsRow projectCount={projects.length} />
        <ProjectGrid projects={projects} searchQuery={searchQuery} loading={loading} />
        <CreateCards />
        <TemplateGrid />
        <Footer />
      </div>
    </div>
  )
}
