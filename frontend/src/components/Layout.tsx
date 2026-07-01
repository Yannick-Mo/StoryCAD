import type { ReactNode } from "react"
import Navbar from "./Navbar"

interface LayoutProps {
  children: ReactNode
  projectId?: string
  onSave?: () => void
  onRegenerate?: () => void
  onExport?: (format: "json" | "markdown") => void
  saving?: boolean
}

export default function Layout({
  children,
  projectId,
  onSave,
  onRegenerate,
  onExport,
  saving,
}: LayoutProps) {
  return (
    <div className="flex flex-col h-screen bg-gray-900 text-gray-100">
      <Navbar
        projectId={projectId}
        onSave={onSave}
        onRegenerate={onRegenerate}
        onExport={onExport}
        saving={saving}
      />
      {children}
    </div>
  )
}
