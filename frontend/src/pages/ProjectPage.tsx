import { useParams, useNavigate } from "react-router-dom"
import { useState, useCallback } from "react"
import { useProject } from "../hooks/useProject"
import { useSkeletonCRUD } from "../hooks/useSkeletonCRUD"
import { exportJSON, exportMarkdown } from "../api/client"
import Layout from "../components/Layout"
import DockLayout from "../components/DockLayout"
import PlotGraphView from "../components/views/PlotGraphView"
import CharacterView from "../components/views/CharacterView"
import WorldRulesView from "../components/views/WorldRulesView"
import BranchForeshadowView from "../components/views/BranchForeshadowView"
import ValidationView from "../components/views/ValidationView"

export default function ProjectPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const { project, loading, error } = useProject(id!)
  const { save, saving } = useSkeletonCRUD(id!)
  const [activeTab, setActiveTab] = useState("characters")

  const handleExport = useCallback(
    async (format: "json" | "markdown") => {
      try {
        const blob = format === "json" ? await exportJSON(id!) : await exportMarkdown(id!)
        const url = URL.createObjectURL(blob)
        const a = document.createElement("a")
        a.href = url
        a.download = `project-${id}.${format === "json" ? "json" : "md"}`
        a.click()
        URL.revokeObjectURL(url)
      } catch {
        // handle error silently
      }
    },
    [id]
  )

  if (loading) {
    return (
      <div className="h-screen bg-gray-900 text-gray-100 flex items-center justify-center">
        <p className="text-gray-400">加载项目中...</p>
      </div>
    )
  }

  if (error || !project) {
    return (
      <div className="h-screen bg-gray-900 text-gray-100 flex items-center justify-center">
        <div className="text-center">
          <p className="text-red-400 mb-2">{error || "项目未找到"}</p>
          <button
            onClick={() => navigate("/")}
            className="text-blue-400 hover:text-blue-300 text-sm"
          >
            返回项目列表
          </button>
        </div>
      </div>
    )
  }

  if (project.status === "pending" || !project.skeleton) {
    return (
      <Layout projectId={id} saving={saving}>
        <div className="flex-1 flex items-center justify-center bg-gray-900">
          <div className="text-center space-y-4">
            <div className="w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full animate-spin mx-auto" />
            <p className="text-gray-400 text-sm">正在生成故事骨架...</p>
            <p className="text-gray-600 text-xs">这大约需要 1-2 分钟</p>
          </div>
        </div>
      </Layout>
    )
  }

  const tabs = [
    { id: "characters", label: "\u89D2\u8272", content: <CharacterView /> },
    { id: "world-rules", label: "\u4E16\u754C\u89C2", content: <WorldRulesView /> },
    { id: "branches", label: "\u5206\u652F\u4F0F\u7B14", content: <BranchForeshadowView /> },
    { id: "validation", label: "\u6821\u9A8C", content: <ValidationView /> },
  ]

  return (
    <Layout
      projectId={id}
      onSave={save}
      onExport={handleExport}
      saving={saving}
    >
      <DockLayout
        mainView={<PlotGraphView />}
        rightTabs={tabs}
        activeTab={activeTab}
        onTabChange={setActiveTab}
        bottomPanel={
          <div className="p-4 text-sm text-gray-500 flex items-center justify-center h-full">
            底部面板 - 输出日志、AI 建议等
          </div>
        }
      />
    </Layout>
  )
}