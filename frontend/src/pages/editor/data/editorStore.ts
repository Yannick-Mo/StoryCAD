import { useState, useCallback } from 'react'
import type { Act, Chapter, ChapterEdge, CharacterRelation, EdgeType, EdgeResult, SelectionState } from '../types'
import { MOCK_DATA } from './mockData'
import { topologicalSort, wouldCreateCycle, hasIncomingTimeline, hasOutgoingTimeline, getOutgoingTimeline } from './orderUtils'

let _nextId = 100
function uid() { return `mock-${_nextId++}` }

const COLORS = ['#f97316', '#8b5cf6', '#06b6d4', '#ec4899', '#10b981', '#eab308']

export function useEditorStore(initialData = MOCK_DATA) {
  const [data, setData] = useState(initialData)
  const [selection, setSelection] = useState<SelectionState>({ type: null, id: null })

  const selectNode = useCallback((type: 'act' | 'chapter', id: string) => {
    setSelection({ type, id })
  }, [])

  const selectEdge = useCallback((edgeId: string) => {
    setSelection({ type: 'edge', id: edgeId })
  }, [])

  const clearSelection = useCallback(() => {
    setSelection({ type: null, id: null })
  }, [])

  const reSort = useCallback((chapters: Chapter[], edges: ChapterEdge[]) => {
    const ordered = topologicalSort(chapters, edges)
    const map = new Map(chapters.map(c => [c.id, c]))
    return ordered.map(id => map.get(id)!).filter(Boolean)
  }, [])

  const addAct = useCallback((name?: string) => {
    const newAct: Act = { id: uid(), name: name ?? `第 ${data.acts.length + 1} 幕`, order: data.acts.length + 1, color: COLORS[data.acts.length % 6] }
    setData(d => ({ ...d, acts: [...d.acts, newAct] }))
    return newAct
  }, [data.acts.length])

  const addChapter = useCallback((actId: string) => {
    const newCh: Chapter = { id: uid(), actId, title: `第 ${data.chapters.filter(c => c.actId === actId).length + 1} 章`, goal: '', wordCount: 0, status: 'draft', scenes: [] }
    setData(d => ({ ...d, chapters: [...d.chapters, newCh] }))
    return newCh
  }, [data.chapters])

  const deleteAct = useCallback((actId: string) => {
    setData(d => {
      const chapterIds = new Set(d.chapters.filter(c => c.actId === actId).map(c => c.id))
      return {
        ...d,
        acts: d.acts.filter(a => a.id !== actId),
        chapters: d.chapters.filter(c => c.actId !== actId),
        edges: d.edges.filter(e => !chapterIds.has(e.sourceId) && !chapterIds.has(e.targetId)),
      }
    })
    setSelection({ type: null, id: null })
  }, [])

  const deleteChapter = useCallback((chapterId: string) => {
    setData(d => ({
      ...d,
      chapters: d.chapters.filter(c => c.id !== chapterId),
      edges: d.edges.filter(e => e.sourceId !== chapterId && e.targetId !== chapterId),
    }))
    if (selection.type === 'chapter' && selection.id === chapterId) {
      setSelection({ type: null, id: null })
    }
  }, [selection])

  const addEdge = useCallback((sourceId: string, targetId: string, type: EdgeType = 'timeline', sourceHandle?: string, targetHandle?: string): EdgeResult => {
    let result: EdgeResult = { edge: null }
    setData(d => {
      if (type === 'timeline') {
        if (wouldCreateCycle(d.edges, sourceId, targetId)) {
          result = { edge: null, cycle: true }
          return d
        }
        // Remove existing outgoing from source and incoming to target
        const filtered = d.edges.filter(e =>
          !(e.type === 'timeline' && (e.sourceId === sourceId || e.targetId === targetId))
        )
        const newEdge: ChapterEdge = { id: uid(), sourceId, targetId, type, sourceHandle, targetHandle }
        result = { edge: newEdge }
        return { ...d, edges: [...filtered, newEdge], chapters: reSort(d.chapters, [...filtered, newEdge]) }
      }
      const newEdge: ChapterEdge = { id: uid(), sourceId, targetId, type, sourceHandle, targetHandle }
      result = { edge: newEdge }
      return { ...d, edges: [...d.edges, newEdge] }
    })
    return result
  }, [reSort])

  const deleteEdge = useCallback((edgeId: string) => {
    setData(d => {
      const edge = d.edges.find(e => e.id === edgeId)
      if (!edge) return d
      const newEdges = d.edges.filter(e => e.id !== edgeId)
      if (edge.type === 'timeline') return { ...d, edges: newEdges, chapters: reSort(d.chapters, newEdges) }
      return { ...d, edges: newEdges }
    })
  }, [reSort])

  const changeEdgeType = useCallback((edgeId: string, newType: EdgeType): boolean => {
    let blocked = false
    setData(d => {
      const edge = d.edges.find(e => e.id === edgeId)
      if (!edge) return d
      if (newType === 'timeline' && edge.type !== 'timeline') {
        const sourceOk = !hasOutgoingTimeline(d.edges, edge.sourceId)
        const targetOk = !hasIncomingTimeline(d.edges, edge.targetId)
        if (!sourceOk || !targetOk) { blocked = true; return d }
      }
      return { ...d, edges: d.edges.map(e => e.id === edgeId ? { ...e, type: newType } : e) }
    })
    return !blocked
  }, [])

  const reconnectEdge = useCallback((edgeId: string, newSource?: string, newTarget?: string, sourceHandle?: string, targetHandle?: string) => {
    setData(d => {
      const edge = d.edges.find(e => e.id === edgeId)
      if (!edge) return d
      const source = newSource ?? edge.sourceId
      const target = newTarget ?? edge.targetId
      if (edge.type === 'timeline') {
        if (wouldCreateCycle(d.edges.filter(e => e.id !== edgeId), source, target)) return d
        // Replace outgoing from new source and incoming to new target
        const filtered = d.edges.filter(e =>
          e.id === edgeId ||
          !(e.type === 'timeline' && (e.sourceId === source || e.targetId === target))
        )
        const newEdges = filtered.map(e => e.id === edgeId ? {
          ...e,
          sourceId: source,
          targetId: target,
          sourceHandle: sourceHandle ?? e.sourceHandle,
          targetHandle: targetHandle ?? e.targetHandle,
        } : e)
        return { ...d, edges: newEdges, chapters: reSort(d.chapters, newEdges) }
      }
      return {
        ...d,
        edges: d.edges.map(e => e.id === edgeId ? {
          ...e,
          sourceId: source,
          targetId: target,
          sourceHandle: sourceHandle ?? e.sourceHandle,
          targetHandle: targetHandle ?? e.targetHandle,
        } : e),
      }
    })
  }, [reSort])

  const resizeAct = useCallback((actId: string, width: number, height: number) => {
    setData(d => ({
      ...d,
      acts: d.acts.map(a => a.id === actId ? { ...a, width, height } : a),
    }))
  }, [])

  const addCharacter = useCallback((name?: string) => {
    const newChar = {
      id: uid(), name: name ?? `新角色 ${data.characters.length + 1}`, role: 'ally',
      personality: '', appearance: '', background: '', motivation: '', relations: [],
    }
    setData(d => ({ ...d, characters: [...d.characters, newChar] }))
    return newChar
  }, [data.characters.length])

  const deleteCharacter = useCallback((charId: string) => {
    setData(d => ({
      ...d,
      characters: d.characters.filter(c => c.id !== charId).map(c => ({
        ...c,
        relations: c.relations.filter(r => r.targetId !== charId),
      })),
    }))
    setSelection({ type: null, id: null })
  }, [])

  const addRelation = useCallback((sourceId: string, targetId: string) => {
    const newRel: CharacterRelation = { id: uid(), targetId, type: '关联', description: '' }
    setData(d => ({
      ...d,
      characters: d.characters.map(c =>
        c.id === sourceId ? { ...c, relations: [...c.relations, newRel] } : c
      ),
    }))
    return newRel
  }, [])

  const deleteRelation = useCallback((characterId: string, relationId: string) => {
    setData(d => ({
      ...d,
      characters: d.characters.map(c =>
        c.id === characterId ? { ...c, relations: c.relations.filter(r => r.id !== relationId) } : c
      ),
    }))
    setSelection({ type: null, id: null })
  }, [])

  const saveRegion = useCallback((region: import('../types').Region) => {
    setData(d => ({
      ...d,
      world: { ...d.world, regions: d.world.regions.map(r => r.id === region.id ? region : r) },
    }))
  }, [])

  const saveFaction = useCallback((faction: import('../types').Faction) => {
    setData(d => ({
      ...d,
      world: { ...d.world, factions: d.world.factions.map(f => f.id === faction.id ? faction : f) },
    }))
  }, [])

  const addFactionRelation = useCallback((sourceId: string, targetId: string, type: string) => {
    const newRel: import('../types').FactionRelation = { id: uid(), sourceId, targetId, type: type as any, description: '' }
    setData(d => ({
      ...d,
      world: { ...d.world, factionRelations: [...d.world.factionRelations, newRel] },
    }))
  }, [])

  const deleteFactionRelation = useCallback((id: string) => {
    setData(d => ({
      ...d,
      world: { ...d.world, factionRelations: d.world.factionRelations.filter(r => r.id !== id) },
    }))
  }, [])

  return {
    data, setData,
    selection, selectNode, selectEdge, clearSelection,
    addAct, addChapter, deleteAct, deleteChapter,
    addEdge, deleteEdge, changeEdgeType, reconnectEdge,
    resizeAct,
    addCharacter, deleteCharacter, addRelation, deleteRelation,
    saveRegion, saveFaction, addFactionRelation, deleteFactionRelation,
  }
}
