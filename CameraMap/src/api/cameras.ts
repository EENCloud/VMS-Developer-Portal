// Cameras with position + status. See concept.md §4.4 and
// Open API Specifications/devices_category.yaml (listCameras).

import { apiGetAll } from './client'
import type { Camera } from '../types'

export async function listCameras(locationId?: string): Promise<Camera[]> {
  const scope = locationId
    ? `&locationId__in=${encodeURIComponent(locationId)}`
    : ''
  return apiGetAll<Camera>(`/cameras?include=devicePosition,status${scope}`)
}
