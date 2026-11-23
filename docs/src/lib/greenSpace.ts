/** Shared config for the Hong Kong green-space demo layer. */
import type { FeatureCollection } from '@/types'
import greenJson from '../../../data/demo/hk-green-space.json'
import greenMeta from '../../../data/demo/hk-green-space.meta.json'

export const hkGreenSpace = greenJson as unknown as FeatureCollection

export const HK_GREEN_BBOX = greenMeta.bbox as [number, number, number, number]

export const HK_GREEN_COLORS: Record<string, [number, number, number, number]> = {
  park: [46, 160, 67, 225],
  open_space: [243, 166, 35, 225],
  country_park: [26, 110, 62, 235],
}

export const HK_GREEN_LEGEND = [
  { category: 'park', label: 'Parks 公园', color: 'rgb(46, 160, 67)' },
  { category: 'open_space', label: 'Open space 休憩用地', color: 'rgb(243, 166, 35)' },
  { category: 'country_park', label: 'Country parks 郊野公园', color: 'rgb(26, 110, 62)' },
]
