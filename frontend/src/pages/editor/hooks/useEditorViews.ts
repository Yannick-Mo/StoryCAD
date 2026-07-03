import { useState, useCallback } from 'react'
import { VIEWS, type ViewDef, type Pillar } from '../types'

export function useEditorViews() {
  const [activePillar, setActivePillar] = useState<Pillar>('narrative')
  const [activeViewId, setActiveViewId] = useState('narrative-plot')
  const [subPanelOpen, setSubPanelOpen] = useState(false)

  const activeView = VIEWS.find(v => v.id === activeViewId) ?? VIEWS[0]
  const pillarViews = VIEWS.filter(v => v.pillar === activePillar)

  const switchPillar = useCallback((pillar: Pillar) => {
    if (activePillar === pillar && subPanelOpen) {
      setSubPanelOpen(false)
      return
    }
    setActivePillar(pillar)
    setSubPanelOpen(true)
  }, [activePillar, subPanelOpen])

  const switchView = useCallback((viewId: string) => {
    setActiveViewId(viewId)
    setSubPanelOpen(false)
  }, [])

  const closeSubPanel = useCallback(() => {
    setSubPanelOpen(false)
  }, [])

  return {
    activePillar,
    activeView,
    activeViewId,
    subPanelOpen,
    pillarViews,
    switchPillar,
    switchView,
    closeSubPanel,
  }
}
