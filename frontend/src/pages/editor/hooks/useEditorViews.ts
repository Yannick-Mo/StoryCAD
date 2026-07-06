import { useState } from 'react'
import { VIEWS } from '../types'

export function useEditorViews() {
  const [activeViewId, setActiveViewId] = useState('narrative-plot')

  const activeView = VIEWS.find(v => v.id === activeViewId) ?? VIEWS[0]

  return {
    activeView,
    activeViewId,
    switchView: setActiveViewId,
  }
}
