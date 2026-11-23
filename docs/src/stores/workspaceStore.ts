import { defineStore } from 'pinia'
import { reactive } from 'vue'

export type PanelId = 'layers' | 'chat'

/**
 * Pure UI state for the map-first workspace. Kept separate from domain state
 * so panels can be collapsed without touching the map or the agent session.
 */
export const useWorkspaceStore = defineStore('workspace', () => {
  const panels = reactive<Record<PanelId, boolean>>({
    layers: true,
    chat: true,
  })

  const togglePanel = (id: PanelId) => {
    panels[id] = !panels[id]
  }

  const showPanel = (id: PanelId, visible = true) => {
    panels[id] = visible
  }

  return { panels, togglePanel, showPanel }
})
