import { computed } from 'vue'
import { useMapStore } from '@/stores/mapStore'
import { useChatStore } from '@/stores/chatStore'
import { toast } from '@/components/ui/useToast'
import type { AgentArtifact } from '@/core'

/**
 * Commands for managing multi-turn cartographic outputs.
 * All scene mutations go through the map store; all model mutations through
 * the artifact reducer in the chat store.
 */
export function useArtifactActions() {
  const mapStore = useMapStore()
  const chatStore = useChatStore()

  const artifacts = computed(() => chatStore.artifacts.items)

  const focus = (id: string) => {
    chatStore.dispatchArtifact({ type: 'focus', id })
  }

  const toggleVisible = (artifact: AgentArtifact) => {
    const next = !artifact.visible
    chatStore.dispatchArtifact({ type: 'setVisible', id: artifact.id, visible: next })
    mapStore.setLayerVisibility(artifact.layerId, next)
  }

  const locate = (artifact: AgentArtifact) => {
    if (!artifact.bbox) {
      toast.error('该产出没有可定位的空间范围')
      return
    }
    const [west, south, east, north] = artifact.bbox
    mapStore.fitBounds(
      [
        [west, south],
        [east, north],
      ],
      { padding: 80, duration: 900 },
    )
    focus(artifact.id)
  }

  const exportGeoJson = (artifact: AgentArtifact) => {
    const blob = new Blob([JSON.stringify(artifact.geojson, null, 2)], {
      type: 'application/geo+json',
    })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${artifact.layerId}.geojson`
    a.click()
    URL.revokeObjectURL(url)
    toast.success('已导出 GeoJSON')
  }

  const remove = (artifact: AgentArtifact) => {
    mapStore.removeLayer(artifact.layerId)
    chatStore.dispatchArtifact({ type: 'remove', id: artifact.id })
    toast.success('已移除产出')
  }

  const rename = (artifact: AgentArtifact, label: string) => {
    chatStore.dispatchArtifact({ type: 'rename', id: artifact.id, label })
  }

  const clearAll = () => {
    for (const artifact of artifacts.value) mapStore.removeLayer(artifact.layerId)
    chatStore.dispatchArtifact({ type: 'clear' })
    toast.success('已清空所有产出')
  }

  return { artifacts, focus, toggleVisible, locate, exportGeoJson, remove, rename, clearAll }
}
