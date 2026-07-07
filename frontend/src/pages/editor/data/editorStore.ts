import { useState, useCallback, useRef, useEffect } from 'react'
import type { EditorMockData, Act, Chapter, ChapterEdge, CharacterRelation, EdgeType, EdgeResult, SelectionState, Scene, Character } from '../types'
import { loadEditorData, syncEditorData, type SyncPayload } from '../../../api/editor'
import { topologicalSort, wouldCreateCycle, hasIncomingTimeline, hasOutgoingTimeline } from './orderUtils'

const COLORS = ['#f97316', '#8b5cf6', '#06b6d4', '#ec4899', '#10b981', '#eab308']

function uid(): string {
  return crypto.randomUUID()
}

interface ChangeEntry {
  entity: string
  op: 'create' | 'update' | 'delete'
  id?: string
  data?: Record<string, unknown>
}

export function useEditorStore(projectId: string) {
  const [data, setData] = useState<EditorMockData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [selection, setSelection] = useState<SelectionState>({ type: null, id: null })
  const [dirty, setDirty] = useState(false)
  const [version, setVersion] = useState(0)
  const [saving, setSaving] = useState(false)
  const changesRef = useRef<ChangeEntry[]>([])
  const timerRef = useRef<ReturnType<typeof setTimeout>>()

  // Load data from API on mount
  useEffect(() => {
    let cancelled = false
    setLoading(true)
    loadEditorData(projectId)
      .then(d => { if (!cancelled) { setData(d); setLoading(false) } })
      .catch(e => { if (!cancelled) { setError(e.message); setLoading(false) } })
    return () => { cancelled = true }
  }, [projectId])

  const enqueueChange = useCallback((change: ChangeEntry) => {
    changesRef.current.push(change)
    setDirty(true)
  }, [])

  // Auto-save with debounce
  const flushChanges = useCallback(async () => {
    if (changesRef.current.length === 0) return
    setSaving(true)
    const entries = changesRef.current
    changesRef.current = []
    setDirty(false)

    const payload: SyncPayload = {}
    for (const entry of entries) {
      if (!payload[entry.entity]) payload[entry.entity] = { created: [], updated: [], deleted: [] }
      if (entry.op === 'create' && entry.data) payload[entry.entity].created!.push(entry.data)
      if (entry.op === 'update' && entry.data) payload[entry.entity].updated!.push(entry.data)
      if (entry.op === 'delete' && entry.id) payload[entry.entity].deleted!.push(entry.id)
    }

    try {
      const result = await syncEditorData(projectId, payload)
      setVersion(result.version)
    } catch {
      changesRef.current = [...entries, ...changesRef.current]
      setDirty(true)
    } finally {
      setSaving(false)
    }
  }, [projectId])

  useEffect(() => {
    if (!dirty) return
    if (timerRef.current) clearTimeout(timerRef.current)
    timerRef.current = setTimeout(flushChanges, 3000)
    return () => { if (timerRef.current) clearTimeout(timerRef.current) }
  }, [dirty, flushChanges])

  // ============================================================
  // Selection
  // ============================================================

  const selectNode = useCallback((type: 'act' | 'chapter', id: string) => {
    setSelection({ type, id })
  }, [])

  const selectEdge = useCallback((edgeId: string) => {
    setSelection({ type: 'edge', id: edgeId })
  }, [])

  const clearSelection = useCallback(() => {
    setSelection({ type: null, id: null })
  }, [])

  // ============================================================
  // Acts
  // ============================================================

  const addAct = useCallback((name?: string) => {
    if (!data) throw new Error("Store not initialized")
    const id = uid()
    const newAct: Act = { id, name: name ?? `第 ${data.acts.length + 1} 幕`, order: data.acts.length + 1, color: COLORS[data.acts.length % COLORS.length] }
    setData(d => d ? { ...d, acts: [...d.acts, newAct] } : d)
    enqueueChange({ entity: 'acts', op: 'create', data: { id, project_id: projectId, name: newAct.name, sort_order: newAct.order, color: newAct.color } })
    return newAct
  }, [data, projectId, enqueueChange])

  const deleteAct = useCallback((actId: string) => {
    if (!data) return
    setData(d => {
      if (!d) return d
      const chapterIds = new Set(d.chapters.filter(c => c.actId === actId).map(c => c.id))
      return { ...d, acts: d.acts.filter(a => a.id !== actId), chapters: d.chapters.filter(c => c.actId !== actId), edges: d.edges.filter(e => !chapterIds.has(e.sourceId) && !chapterIds.has(e.targetId)) }
    })
    enqueueChange({ entity: 'acts', op: 'delete', id: actId })
    setSelection({ type: null, id: null })
  }, [data, enqueueChange])

  // ============================================================
  // Chapters
  // ============================================================

  const addChapter = useCallback((actId: string) => {
    if (!data) throw new Error("Store not initialized")
    const id = uid()
    const newCh: Chapter = { id, actId, title: `第 ${data.chapters.filter(c => c.actId === actId).length + 1} 章`, goal: '', wordCount: 0, status: 'draft', scenes: [] }
    setData(d => d ? { ...d, chapters: [...d.chapters, newCh] } : d)
    enqueueChange({ entity: 'chapters', op: 'create', data: { id, project_id: projectId, act_id: actId, title: newCh.title, sort_order: data.chapters.filter(c => c.actId === actId).length } })
    return newCh
  }, [data, projectId, enqueueChange])

  const deleteChapter = useCallback((chapterId: string) => {
    if (!data) return
    const ch = data.chapters.find(c => c.id === chapterId)
    if (ch) {
      for (const scene of ch.scenes) {
        enqueueChange({ entity: 'scenes', op: 'delete', id: scene.id })
      }
    }
    setData(d => d ? { ...d, chapters: d.chapters.filter(c => c.id !== chapterId), edges: d.edges.filter(e => e.sourceId !== chapterId && e.targetId !== chapterId) } : d)
    enqueueChange({ entity: 'chapters', op: 'delete', id: chapterId })
    if (selection.type === 'chapter' && selection.id === chapterId) setSelection({ type: null, id: null })
  }, [data, selection, enqueueChange])

  // ============================================================
  // Scenes
  // ============================================================

  const addScene = useCallback((chapterId: string) => {
    if (!data) throw new Error("Store not initialized")
    const id = uid()
    const ch = data.chapters.find(c => c.id === chapterId)
    const order = ch ? ch.scenes.length + 1 : 1
    const newScene: Scene = { id, chapter_id: chapterId, title: `场景 ${order}`, povCharacter: '', setting: '', time: '', summary: '', content: '', wordCount: 0 }
    setData(d => d ? {
      ...d,
      chapters: d.chapters.map(ch => ch.id === chapterId ? { ...ch, scenes: [...ch.scenes, newScene] } : ch)
    } : d)
    enqueueChange({ entity: 'scenes', op: 'create', data: { id, project_id: projectId, chapter_id: chapterId, title: newScene.title, sort_order: order } })
    return newScene
  }, [data, projectId, enqueueChange])

  const deleteScene = useCallback((chapterId: string, sceneId: string) => {
    if (!data) return
    setData(d => d ? {
      ...d,
      chapters: d.chapters.map(ch => ch.id === chapterId ? {
        ...ch,
        scenes: ch.scenes.filter(s => s.id !== sceneId)
      } : ch)
    } : d)
    enqueueChange({ entity: 'scenes', op: 'delete', id: sceneId })
  }, [data, enqueueChange])

  // ============================================================
  // Edges
  // ============================================================

  const reSort = useCallback((chapters: Chapter[], edges: ChapterEdge[]) => {
    const ordered = topologicalSort(chapters, edges)
    const map = new Map(chapters.map(c => [c.id, c]))
    return ordered.map(id => map.get(id)!).filter(Boolean)
  }, [])

  const addEdge = useCallback((sourceId: string, targetId: string, type: EdgeType = 'timeline', sourceHandle?: string, targetHandle?: string): EdgeResult => {
    if (!data) return { edge: null }
    let result: EdgeResult = { edge: null }
    setData(d => {
      if (!d) return d
      if (type === 'timeline') {
        if (wouldCreateCycle(d.edges, sourceId, targetId)) { result = { edge: null, cycle: true }; return d }
        const filtered = d.edges.filter(e => !(e.type === 'timeline' && (e.sourceId === sourceId || e.targetId === targetId)))
        const newEdge: ChapterEdge = { id: uid(), sourceId, targetId, type, sourceHandle, targetHandle }
        result = { edge: newEdge }
        return { ...d, edges: [...filtered, newEdge], chapters: reSort(d.chapters, [...filtered, newEdge]) }
      }
      const newEdge: ChapterEdge = { id: uid(), sourceId, targetId, type, sourceHandle, targetHandle }
      result = { edge: newEdge }
      return { ...d, edges: [...d.edges, newEdge] }
    })
    if (result.edge) {
      enqueueChange({ entity: 'edges', op: 'create', data: { id: result.edge.id, project_id: projectId, source_id: sourceId, target_id: targetId, edge_type: type, source_handle: sourceHandle || '', target_handle: targetHandle || '' } })
    }
    return result
  }, [data, projectId, reSort, enqueueChange])

  const deleteEdge = useCallback((edgeId: string) => {
    if (!data) return
    setData(d => {
      if (!d) return d
      const edge = d.edges.find(e => e.id === edgeId)
      if (!edge) return d
      const newEdges = d.edges.filter(e => e.id !== edgeId)
      if (edge.type === 'timeline') return { ...d, edges: newEdges, chapters: reSort(d.chapters, newEdges) }
      return { ...d, edges: newEdges }
    })
    enqueueChange({ entity: 'edges', op: 'delete', id: edgeId })
  }, [data, reSort, enqueueChange])

  const changeEdgeType = useCallback((edgeId: string, newType: EdgeType): boolean => {
    if (!data) return false
    let blocked = false
    setData(d => {
      if (!d) return d
      const edge = d.edges.find(e => e.id === edgeId)
      if (!edge) return d
      if (newType === 'timeline' && edge.type !== 'timeline') {
        if (hasOutgoingTimeline(d.edges, edge.sourceId) || hasIncomingTimeline(d.edges, edge.targetId)) { blocked = true; return d }
      }
      return { ...d, edges: d.edges.map(e => e.id === edgeId ? { ...e, type: newType } : e) }
    })
    if (!blocked) enqueueChange({ entity: 'edges', op: 'update', data: { id: edgeId, edge_type: newType } })
    return !blocked
  }, [data, enqueueChange])

  const reconnectEdge = useCallback((edgeId: string, newSource?: string, newTarget?: string, sourceHandle?: string, targetHandle?: string) => {
    if (!data) return
    setData(d => {
      if (!d) return d
      const edge = d.edges.find(e => e.id === edgeId)
      if (!edge) return d
      const source = newSource ?? edge.sourceId; const target = newTarget ?? edge.targetId
      if (edge.type === 'timeline') {
        if (wouldCreateCycle(d.edges.filter(e => e.id !== edgeId), source, target)) return d
        const filtered = d.edges.filter(e => e.id === edgeId || !(e.type === 'timeline' && (e.sourceId === source || e.targetId === target)))
        return { ...d, edges: filtered.map(e => e.id === edgeId ? { ...e, sourceId: source, targetId: target, sourceHandle: sourceHandle ?? e.sourceHandle, targetHandle: targetHandle ?? e.targetHandle } : e), chapters: reSort(d.chapters, filtered.map(e => e.id === edgeId ? { ...e, sourceId: source, targetId: target } : e)) }
      }
      return { ...d, edges: d.edges.map(e => e.id === edgeId ? { ...e, sourceId: source, targetId: target, sourceHandle: sourceHandle ?? e.sourceHandle, targetHandle: targetHandle ?? e.targetHandle } : e) }
    })
    const updates: Record<string, unknown> = { id: edgeId }
    if (newSource) updates.source_id = newSource
    if (newTarget) updates.target_id = newTarget
    if (sourceHandle) updates.source_handle = sourceHandle
    if (targetHandle) updates.target_handle = targetHandle
    enqueueChange({ entity: 'edges', op: 'update', data: updates })
  }, [data, reSort, enqueueChange])

  const resizeAct = useCallback((actId: string, width: number, height: number) => {
    setData(d => d ? { ...d, acts: d.acts.map(a => a.id === actId ? { ...a, width, height } : a) } : d)
  }, [])

  // ============================================================
  // Characters
  // ============================================================

  const addCharacter = useCallback((name?: string) => {
    if (!data) throw new Error("Store not initialized")
    const id = uid()
    const newChar = { id, name: name ?? `新角色 ${data.characters.length + 1}`, role: 'ally', personality: '', appearance: '', background: '', motivation: '', relations: [] }
    setData(d => d ? { ...d, characters: [...d.characters, newChar] } : d)
    enqueueChange({ entity: 'characters', op: 'create', data: { id, project_id: projectId, name: newChar.name, role: newChar.role } })
    return newChar
  }, [data, projectId, enqueueChange])

  const deleteCharacter = useCallback((charId: string) => {
    if (!data) return
    setData(d => d ? { ...d, characters: d.characters.filter(c => c.id !== charId).map(c => ({ ...c, relations: c.relations.filter(r => r.targetId !== charId) })) } : d)
    enqueueChange({ entity: 'characters', op: 'delete', id: charId })
    setSelection({ type: null, id: null })
  }, [data, enqueueChange])

  const addRelation = useCallback((sourceId: string, targetId: string) => {
    if (!data) return
    const id = uid()
    const newRel = { id, targetId, type: '关联', label: '', description: '' }
    setData(d => d ? { ...d, characters: d.characters.map(c => c.id === sourceId ? { ...c, relations: [...c.relations, newRel] } : c) } : d)
    enqueueChange({ entity: 'character_relations', op: 'create', data: { id, project_id: projectId, character_id: sourceId, target_id: targetId, rel_type: '关联' } })
    return newRel
  }, [data, projectId, enqueueChange])

  const deleteRelation = useCallback((characterId: string, relationId: string) => {
    if (!data) return
    setData(d => d ? { ...d, characters: d.characters.map(c => c.id === characterId ? { ...c, relations: c.relations.filter(r => r.id !== relationId) } : c) } : d)
    enqueueChange({ entity: 'character_relations', op: 'delete', id: relationId })
    setSelection({ type: null, id: null })
  }, [data, enqueueChange])

  // ============================================================
  // Global Settings
  // ============================================================

  const saveGlobalSettings = useCallback((text: string) => {
    setData(d => d ? { ...d, globalSettings: text } : d)
    enqueueChange({ entity: 'projects', op: 'update', data: { id: projectId, global_settings: text } })
  }, [projectId, enqueueChange])

  const hasPendingChanges = useCallback(() => {
    return changesRef.current.length > 0
  }, [])

  // ============================================================
  // Entity updates (partial field updates)
  // ============================================================

  const updateAct = useCallback((id: string, updates: Partial<Pick<Act, 'name' | 'color'>>) => {
    setData(d => d ? { ...d, acts: d.acts.map(a => a.id === id ? { ...a, ...updates } : a) } : d)
    enqueueChange({ entity: 'acts', op: 'update', data: { id, ...updates } })
  }, [enqueueChange])

  const updateChapter = useCallback((id: string, updates: Partial<Pick<Chapter, 'title' | 'goal' | 'status'>>) => {
    setData(d => d ? { ...d, chapters: d.chapters.map(c => c.id === id ? { ...c, ...updates } : c) } : d)
    enqueueChange({ entity: 'chapters', op: 'update', data: { id, ...updates } })
  }, [enqueueChange])

  const updateScene = useCallback((chapterId: string, sceneId: string, updates: Partial<Pick<Scene, 'title' | 'povCharacter' | 'setting' | 'time' | 'summary'>>) => {
    setData(d => d ? {
      ...d,
      chapters: d.chapters.map(ch => ch.id === chapterId ? {
        ...ch,
        scenes: ch.scenes.map(s => s.id === sceneId ? { ...s, ...updates } : s)
      } : ch)
    } : d)
    const backendData: Record<string, unknown> = { id: sceneId }
    if (updates.title !== undefined) backendData.title = updates.title
    if (updates.povCharacter !== undefined) backendData.pov_character = updates.povCharacter
    if (updates.setting !== undefined) backendData.setting = updates.setting
    if (updates.time !== undefined) backendData.scene_time = updates.time
    if (updates.summary !== undefined) backendData.summary = updates.summary
    enqueueChange({ entity: 'scenes', op: 'update', data: backendData })
  }, [enqueueChange])

  const updateEdge = useCallback((id: string, updates: Partial<Pick<ChapterEdge, 'label'>>) => {
    setData(d => d ? { ...d, edges: d.edges.map(e => e.id === id ? { ...e, ...updates } : e) } : d)
    enqueueChange({ entity: 'edges', op: 'update', data: { id, ...updates } })
  }, [enqueueChange])

  const updateCharacter = useCallback((id: string, updates: Partial<Pick<Character, 'name' | 'role' | 'personality' | 'appearance' | 'background' | 'motivation'>>) => {
    setData(d => d ? { ...d, characters: d.characters.map(c => c.id === id ? { ...c, ...updates } : c) } : d)
    const backendData: Record<string, unknown> = { id }
    if (updates.name !== undefined) backendData.name = updates.name
    if (updates.role !== undefined) backendData.role = updates.role
    if (updates.personality !== undefined) backendData.personality = updates.personality
    if (updates.appearance !== undefined) backendData.appearance = updates.appearance
    if (updates.background !== undefined) backendData.background = updates.background
    if (updates.motivation !== undefined) backendData.motivation = updates.motivation
    enqueueChange({ entity: 'characters', op: 'update', data: backendData })
  }, [enqueueChange])

  const updateRelation = useCallback((id: string, updates: Partial<Pick<CharacterRelation, 'type' | 'label' | 'description'>>) => {
    setData(d => d ? {
      ...d,
      characters: d.characters.map(ch => ({
        ...ch,
        relations: ch.relations.map(r => r.id === id ? { ...r, ...updates } : r)
      }))
    } : d)
    const backendData: Record<string, unknown> = { id }
    if (updates.type !== undefined) backendData.rel_type = updates.type
    if (updates.label !== undefined) backendData.label = updates.label
    if (updates.description !== undefined) backendData.description = updates.description
    enqueueChange({ entity: 'character_relations', op: 'update', data: backendData })
  }, [enqueueChange])

  const setDataDirect = useCallback((updater: EditorMockData | ((prev: EditorMockData | null) => EditorMockData | null)) => {
    setData(updater)
  }, [])

  return {
    data, loading, error, saving, version, dirty,
    setData: setDataDirect,
    selection, selectNode, selectEdge, clearSelection,
    addAct, addChapter, deleteAct, deleteChapter,
    addScene, deleteScene, addEdge, deleteEdge, changeEdgeType, reconnectEdge,
    resizeAct,
    addCharacter, deleteCharacter, addRelation, deleteRelation,
    saveGlobalSettings,
    updateAct, updateChapter, updateScene, updateEdge,
    updateCharacter, updateRelation,
    flushChanges, hasPendingChanges,
    enqueueChange,
  }
}
