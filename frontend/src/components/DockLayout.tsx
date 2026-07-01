import { Panel, PanelGroup, PanelResizeHandle } from "react-resizable-panels"
import type { ReactNode } from "react"

export interface Tab {
  id: string
  label: string
  content: ReactNode
}

interface DockLayoutProps {
  mainView: ReactNode
  rightTabs: Tab[]
  bottomPanel?: ReactNode
  activeTab?: string
  onTabChange?: (tabId: string) => void
}

export default function DockLayout({
  mainView,
  rightTabs,
  bottomPanel,
  activeTab,
  onTabChange,
}: DockLayoutProps) {
  const currentTab = rightTabs.find((t) => t.id === activeTab) ?? rightTabs[0]

  return (
    <PanelGroup direction="horizontal" className="flex-1">
      <Panel defaultSize={60} minSize={30}>
        {mainView}
      </Panel>
      <PanelResizeHandle className="w-1 bg-gray-700 hover:bg-blue-500 transition-colors cursor-col-resize" />
      <Panel defaultSize={40} minSize={20}>
        <PanelGroup direction="vertical">
          <Panel>
            <div className="flex flex-col h-full">
              <div className="flex border-b border-gray-700 bg-gray-800">
                {rightTabs.map((tab) => (
                  <button
                    key={tab.id}
                    onClick={() => onTabChange?.(tab.id)}
                    className={`px-4 py-2 text-sm border-b-2 transition-colors ${
                      tab.id === currentTab.id
                        ? "border-blue-500 text-blue-400"
                        : "border-transparent text-gray-400 hover:text-gray-200"
                    }`}
                  >
                    {tab.label}
                  </button>
                ))}
              </div>
              <div className="flex-1 overflow-auto">
                {currentTab.content}
              </div>
            </div>
          </Panel>
          {bottomPanel && (
            <>
              <PanelResizeHandle className="h-1 bg-gray-700 hover:bg-blue-500 transition-colors cursor-row-resize" />
              <Panel defaultSize={30} minSize={10}>
                {bottomPanel}
              </Panel>
            </>
          )}
        </PanelGroup>
      </Panel>
    </PanelGroup>
  )
}
