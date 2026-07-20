// Offline fixtures (concept.md §11). Lets the rendering pipeline be developed
// and verified with no network/auth. Mirrors the live API shapes.

import type { Camera, Floor, Location, Paginated } from '../types'
import cameraResponse from '../fixtures/cameraResponse.json'
import floorResponse from '../fixtures/floorResponse.json'

const floors = (floorResponse as Paginated<Floor>).results
const cameras = (cameraResponse as unknown as Paginated<Camera>).results

const locationId = cameras[0]?.locationId ?? 'demo-location'

export const fixtureLocations: Location[] = [
  { id: locationId, name: floors[0]?.name?.replace(/ Floor.*$/i, '') || 'Demo location' },
]

export function fixtureFloors(): Floor[] {
  return floors
}

export function fixtureCameras(): Camera[] {
  return cameras
}

export const fixtureLocationId = locationId

// Real pixel dimensions of the floor-5 plan PNG (from the production HAR). The
// similarity transform depends on the true image aspect ratio, so fixture mode
// uses these so placement matches the real app without the actual image.
export const fixturePlanSize = { w: 1588, h: 460 }
