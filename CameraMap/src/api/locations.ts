// Locations, floors, and floor-plan images. See concept.md §4.1–4.3 and
// Open API Specifications/grouping_category.yaml.

import { apiGetAll, apiGetObjectUrl } from './client'
import type { Floor, Location, Paginated } from '../types'

export async function listLocations(): Promise<Location[]> {
  return apiGetAll<Location>('/locations')
}

export async function listFloors(locationId: string): Promise<Floor[]> {
  return apiGetAll<Floor>(
    `/locations/${encodeURIComponent(locationId)}/floors?include=floorPlans`,
  )
}

/**
 * Fetch the floor-plan image (auth-protected binary) as an object URL.
 * Picks the best available plan type, preferring raster/vector over PDF.
 * Returns null when the floor has no uploaded plan.
 */
export async function fetchFloorImageUrl(
  locationId: string,
  floor: Floor,
): Promise<{ url: string; type: string } | null> {
  const plans = floor.floorPlans ?? []
  const plan =
    plans.find((p) => p.type === 'png') ??
    plans.find((p) => p.type === 'svg') ??
    plans[0]
  if (!plan) return null

  // Accept defaults to *​/* — EEN's image endpoint 406s on a specific type.
  const url = await apiGetObjectUrl(
    `/locations/${encodeURIComponent(locationId)}/floors/${encodeURIComponent(floor.id)}.${plan.type}`,
  )
  return { url, type: plan.type }
}

// Re-exported for callers that want raw page access.
export type { Paginated }
