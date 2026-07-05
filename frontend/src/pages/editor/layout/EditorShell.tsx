import { useState, useCallback } from 'react'
import BottomNav from './BottomNav'
import LeftDrawer from './LeftDrawer'
import ActionButtons from './ActionButtons'
import PlotCanvas from '../views/plot/PlotCanvas'
import PlotToolbar from '../views/plot/PlotToolbar'
import ChapterDetail from '../views/plot/ChapterDetail'
import ActDetail from '../views/plot/ActDetail'
import EdgeDetail from '../views/plot/EdgeDetail'
import CharCanvas from '../views/character/CharCanvas'
import CharacterDetail from '../views/character/CharacterDetail'
import CharacterEdgeDetail from '../views/character/CharacterEdgeDetail'
import RhythmCanvas from '../views/rhythm/RhythmCanvas'
import RhythmDetail from '../views/rhythm/RhythmDetail'
import ThemeCanvas from '../views/theme/ThemeCanvas'
import { MapView, RulesView, HistoryView, InfoControlView, PovView, InspirationView, KanbanView, ChangelogView } from '../views/info/InfoViews'
import PreviewModal from '../modals/PreviewModal'
import SceneEditor from '../modals/SceneEditor'
import { useEditorViews } from '../hooks/useEditorViews'
import { useEditorStore } from '../data/editorStore'
import { ToastProvider } from '../components/Toast'
import ConfirmDialog from '../components/ConfirmDialog'
import type { Chapter, Scene, EdgeType } from '../types'
import { getCompletedChain } from '../data/orderUtils'

export default function EditorShell() {
  const views = useEditorViews()
  const [drawerOpen, setDrawerOpen] = useState(false)
  const [previewOpen, setPreviewOpen] = useState(false)
  const [selectedActId, setSelectedActId] = useState<string | null>(null)
  const [selectedChapter, setSelectedChapter] = useState<Chapter | null>(null)
  const [connectionMode, setConnectionMode] = useState<'all' | EdgeType>('all')
  const [editingScene, setEditingScene] = useState<Scene | null>(null)
  const [confirmDelete, setConfirmDelete] = useState<{ type: 'act' | 'chapter'; id: string } | null>(null)
  const [selectedCharacterId, setSelectedCharacterId] = useState<string | null>(null)
  const [selectedRelation, setSelectedRelation] = useState<{ sourceId: string; relationId: string } | null>(null)
  const [selectedRhythmIndex, setSelectedRhythmIndex] = useState<number | null>(null)

  const store = useEditorStore()
  const data = store.data

  const selectedEdge = store.selection.type === 'edge'
    ? data.edges.find(edge => edge.id === store.selection.id) ?? null
    : null

  const renderCanvas = () => {
    switch (views.activeViewId) {
      case 'narrative-plot':
        return (
          <PlotCanvas
            chapters={data.chapters}
            acts={data.acts}
            edges={data.edges}
            onChapterClick={handleChapterClick}
            onActClick={handleActClick}
            onAddEdge={store.addEdge}
            onDeleteEdge={store.deleteEdge}
            onChangeEdgeType={store.changeEdgeType}
            onReconnectEdge={store.reconnectEdge}
            onAddChapter={store.addChapter}
            onDeleteChapter={(id) => setConfirmDelete({ type: 'chapter', id })}
            onAddAct={store.addAct}
            onDeleteAct={(id) => setConfirmDelete({ type: 'act', id })}
            onActResize={store.resizeAct}
            selection={store.selection}
            onSelectNode={store.selectNode}
            onSelectEdge={(edgeId: string) => {
              setSelectedActId(null)
              setSelectedChapter(null)
              store.selectEdge(edgeId)
            }}
            onClearSelection={store.clearSelection}
            connectionMode={connectionMode}
          />
        )
      case 'narrative-char':
        return (
          <CharCanvas
            characters={data.characters}
            selection={{ type: selectedCharacterId ? 'character' : selectedRelation ? 'relation' : null, id: selectedCharacterId ?? (selectedRelation ? `${selectedRelation.sourceId}|${selectedRelation.relationId}` : null) }}
            onSelectCharacter={(id) => { setSelectedCharacterId(id); setSelectedRelation(null) }}
            onSelectRelation={(sourceId, relationId) => { setSelectedRelation({ sourceId, relationId }); setSelectedCharacterId(null) }}
            onClearSelection={() => { setSelectedCharacterId(null); setSelectedRelation(null) }}
            onAddCharacter={() => { const ch = store.addCharacter(); setSelectedCharacterId(ch.id) }}
            onDeleteCharacter={(id) => { store.deleteCharacter(id); setSelectedCharacterId(null) }}
            onAddRelation={(sourceId, targetId) => { store.addRelation(sourceId, targetId) }}
            onDeleteRelation={(characterId, relationId) => { store.deleteRelation(characterId, relationId); setSelectedRelation(null) }}
          />
        )
      case 'narrative-rhythm':
        return <RhythmCanvas rhythms={data.rhythms} chapters={data.chapters} acts={data.acts} selectedIndex={selectedRhythmIndex} onSelectChapter={setSelectedRhythmIndex} />
      case 'narrative-theme':
        return <ThemeCanvas themes={data.themes} />
      default:
        return renderInfoView()
    }
  }

  const renderInfoView = () => {
    switch (views.activeViewId) {
      case 'world-map': return <MapView data={data.world} />
      case 'world-rules': return <RulesView data={data.rules} />
      case 'world-history': return <HistoryView data={data.history} />
      case 'experience-info': return <InfoControlView data={data.infoControls} />
      case 'experience-pov': return <PovView data={data.pov} />
      case 'creation-inspo': return <InspirationView data={data.inspirations} />
      case 'creation-kanban': return <KanbanView data={data.kanban} />
      case 'creation-log': return <ChangelogView data={data.changelog} />
      default: return <div className="flex items-center justify-center h-full text-gray-500">选择视图</div>
    }
  }

  const handleExport = () => {
    const completed = getCompletedChain(data.chapters, data.edges, data.acts)
    const text = completed.map(ch => {
      const scenes = ch.scenes.filter(s => s.content).map(s => s.content).join('\n\n')
      return `${ch.title}\n${ch.goal}\n\n${scenes}\n\n${'-'.repeat(16)}\n\n`
    }).join('')
    const blob = new Blob([text], { type: 'text/plain' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = '小说已完成内容.txt'
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  }

  const handleActClick = useCallback((actId: string) => {
    if (!actId) { setSelectedActId(null); store.clearSelection(); return }
    setSelectedActId(actId)
    setSelectedChapter(null)
    store.selectNode('act', actId)
  }, [store])

  const handleChapterClick = useCallback((chapterId: string) => {
    const ch = data.chapters.find(c => c.id === chapterId)
    if (!ch) return
    setSelectedChapter(ch)
    setSelectedActId(null)
    store.selectNode('chapter', chapterId)
  }, [data.chapters, store])

  const handleSceneSave = useCallback((chapterId: string, sceneId: string, content: string) => {
    store.setData(d => {
      const ch = d.chapters.find(c => c.id === chapterId)
      if (!ch) return d
      const sc = ch.scenes.find(s => s.id === sceneId)
      if (!sc) return d
      const newSc = { ...sc, content, wordCount: content.replace(/\s/g, '').length }
      const newScenes = ch.scenes.map(s => s.id === sceneId ? newSc : s)
      const newCh = { ...ch, scenes: newScenes, wordCount: newScenes.reduce((s, sc) => s + sc.wordCount, 0) }
      return { ...d, chapters: d.chapters.map(c => c.id === chapterId ? newCh : c) }
    })
    // Refresh selected chapter display
    const updated = data.chapters.find(c => c.id === chapterId)
    if (updated) setSelectedChapter({ ...updated })
    setEditingScene(null)
  }, [store, data.chapters])

  const handleChapterGoalSave = useCallback((chapterId: string, goal: string) => {
    store.setData(d => ({
      ...d,
      chapters: d.chapters.map(c => c.id === chapterId ? { ...c, goal } : c),
    }))
    if (selectedChapter?.id === chapterId) setSelectedChapter({ ...selectedChapter, goal })
  }, [store, selectedChapter])

  const handleOpenSceneEditor = useCallback((scene: Scene) => {
    setEditingScene(scene)
  }, [])

  return (
    <ToastProvider>
      <div className="h-screen flex flex-col bg-gray-950 text-gray-100 overflow-hidden select-none">
        {/* Top bar */}
        <div className="h-12 flex items-center justify-between px-4 border-b border-gray-800 bg-gray-900/50 shrink-0">
          <button
            onClick={() => setDrawerOpen(true)}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs text-gray-400 hover:text-gray-200 bg-gray-800/50 hover:bg-gray-700 transition-colors"
          >
            ☰ 大纲
          </button>
          <div className="text-xs text-gray-500 bg-gray-800/50 px-3 py-1 rounded-full">
            {views.activeView.label}
          </div>
        </div>

      {/* Canvas area */}
      <div className="flex-1 relative">
        {renderCanvas()}

        {views.activeViewId === 'narrative-plot' && (
          <PlotToolbar
            selection={store.selection}
            selectedActId={selectedActId}
            connectionMode={connectionMode}
            onConnectionModeChange={setConnectionMode}
            onAddAct={() => store.addAct()}
            onAddChapter={() => selectedActId && store.addChapter(selectedActId)}
            onDeleteSelected={() => {
              const sel = store.selection
              if (sel.type === 'act') setConfirmDelete({ type: 'act', id: sel.id! })
              if (sel.type === 'chapter') store.deleteChapter(sel.id!)
              if (sel.type === 'edge') store.deleteEdge(sel.id!)
              store.clearSelection()
            }}
            onRenameAct={() => {
              if (store.selection.type === 'act') {
                const act = data.acts.find(a => a.id === store.selection.id)
                const name = prompt('重命名幕：', act?.name)
                if (name && act) { act.name = name; store.setData({ ...data }) }
              }
              store.clearSelection()
            }}
            onEditChapterGoal={() => {
              if (store.selection.type === 'chapter') {
                const ch = data.chapters.find(c => c.id === store.selection.id)
                if (ch) { setSelectedChapter({ ...ch }); store.clearSelection() }
              }
            }}
            onLayout={() => {}}
            onExport={handleExport}
          />
        )}

        {/* Chapter/Act/Edge detail panel */}
        {views.activeViewId === 'narrative-plot' && (
          selectedActId ? (
            <ActDetail
              act={data.acts.find(a => a.id === selectedActId)!}
              chapters={data.chapters.filter(c => c.actId === selectedActId)}
              onClose={() => setSelectedActId(null)}
              onSelectChapter={(chId) => {
                setSelectedActId(null)
                setSelectedChapter(data.chapters.find(c => c.id === chId) ?? null)
              }}
              onSceneSave={handleSceneSave}
              onOpenSceneEditor={(scene) => setEditingScene(scene)}
            />
          ) : selectedChapter ? (
            <ChapterDetail
              chapter={selectedChapter}
              onClose={() => setSelectedChapter(null)}
              onSceneSave={handleSceneSave}
              onChapterSave={handleChapterGoalSave}
              onOpenSceneEditor={(scene) => setEditingScene(scene)}
            />
          ) : selectedEdge && selectedEdge.type !== 'timeline' ? (
            <EdgeDetail
              edge={selectedEdge}
              chapters={data.chapters}
              acts={data.acts}
              onClose={store.clearSelection}
              onChangeType={(edgeId, newType) => {
                const changed = store.changeEdgeType(edgeId, newType)
                if (changed && newType === 'timeline') store.clearSelection()
              }}
              onDelete={(edgeId) => {
                store.deleteEdge(edgeId)
                store.clearSelection()
              }}
            />
          ) : null
        )}

        {/* Character detail panels */}
        {views.activeViewId === 'narrative-char' && (
          selectedCharacterId ? (
            <CharacterDetail
              character={data.characters.find(c => c.id === selectedCharacterId)!}
              onClose={() => setSelectedCharacterId(null)}
            />
          ) : selectedRelation ? (
            (() => {
              const srcChar = data.characters.find(c => c.id === selectedRelation.sourceId)
              const rel = srcChar?.relations.find(r => r.id === selectedRelation.relationId)
              const tgtChar = rel ? data.characters.find(c => c.id === rel.targetId) : undefined
              if (!srcChar || !rel || !tgtChar) return null
              return (
                <CharacterEdgeDetail
                  source={srcChar}
                  target={tgtChar}
                  relation={rel}
                  onClose={() => setSelectedRelation(null)}
                  onDelete={() => { store.deleteRelation(selectedRelation.sourceId, selectedRelation.relationId); setSelectedRelation(null) }}
                />
              )
            })()
          ) : null
        )}

        {/* Rhythm detail panel */}
        {views.activeViewId === 'narrative-rhythm' && selectedRhythmIndex !== null && (
          (() => {
            const point = data.rhythms[selectedRhythmIndex]
            if (!point) return null
            const ch = data.chapters[point.chapterIndex]
            const act = ch ? data.acts.find(a => a.id === ch.actId) : undefined
            return (
              <RhythmDetail
                point={point}
                chapter={ch}
                act={act}
                wordCount={ch?.wordCount ?? 0}
                onClose={() => setSelectedRhythmIndex(null)}
              />
            )
          })()
        )}

        <ActionButtons
          onPreview={() => setPreviewOpen(true)}
          onExport={handleExport}
          onGlobalSetting={() => alert('📜 全局设定 (宪法)\n\n世界基石：人·魔·妖·神共存\n普适规则：万物皆可修炼\n核心冲突：资源与理念之争')}
        />
      </div>

      {/* Drawer */}
      <LeftDrawer
        open={drawerOpen}
        acts={data.acts}
        chapters={data.chapters}
        onClose={() => setDrawerOpen(false)}
        onSelectChapter={handleChapterClick}
      />

      {/* Modals */}
      <PreviewModal open={previewOpen} chapters={getCompletedChain(data.chapters, data.edges, data.acts)} onClose={() => setPreviewOpen(false)} />

      {editingScene && (
        <SceneEditor
          scene={editingScene}
          chapterTitle={data.chapters.find(c => c.scenes.some(s => s.id === editingScene.id))?.title ?? ''}
          onClose={() => setEditingScene(null)}
          onSave={(sceneId, content) => {
            const ch = data.chapters.find(c => c.scenes.some(s => s.id === sceneId))
            if (ch) handleSceneSave(ch.id, sceneId, content)
          }}
        />
      )}

      {/* Bottom nav */}
      <BottomNav
        activePillar={views.activePillar}
        activeViewId={views.activeViewId}
        subPanelOpen={views.subPanelOpen}
        pillarViews={views.pillarViews}
        onSwitchPillar={views.switchPillar}
        onSwitchView={views.switchView}
        onCloseSubPanel={views.closeSubPanel}
      />
    </div>
      <ConfirmDialog
        open={confirmDelete !== null}
        title={confirmDelete?.type === 'act' ? '删除幕' : '删除章'}
        message={
          confirmDelete?.type === 'act'
            ? "确定要删除「" + (data.acts.find(a => a.id === confirmDelete.id)?.name ?? '') + "」吗？该幕下的所有章节和连线将一并删除。"
            : "确定要删除「" + (data.chapters.find(c => c.id === confirmDelete?.id)?.title ?? '') + "」吗？"
        }
        onConfirm={() => {
          if (!confirmDelete) return
          if (confirmDelete.type === 'act') store.deleteAct(confirmDelete.id)
          else store.deleteChapter(confirmDelete.id)
          setConfirmDelete(null)
        }}
        onCancel={() => setConfirmDelete(null)}
      />
    </ToastProvider>
  )
}
