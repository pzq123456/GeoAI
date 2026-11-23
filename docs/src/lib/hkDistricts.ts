/** Shared config for the Hong Kong district-boundary demo layer. */
import type { FeatureCollection } from '@/types'
import districtsJson from '../../../data/demo/hk-districts.json'
import districtsMeta from '../../../data/demo/hk-districts.meta.json'

export const hkDistricts = districtsJson as unknown as FeatureCollection

export const HK_DISTRICTS_BBOX = districtsMeta.bbox as [number, number, number, number]
