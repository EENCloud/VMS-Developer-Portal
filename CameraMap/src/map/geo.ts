// Core positioning math: map WGS-84 geo coordinates onto floor-plan pixels.
// See concept.md §5.
//
// A floor plan is georeferenced by TWO opposite corner coordinates
// (topLeftCoordinates -> pixel (0,0), bottomRightCoordinates -> pixel (W,H))
// PLUS the image's pixel dimensions. The plan is a uniformly-scaled, rotated
// (and y-flipped) drawing of the floor, so the correct mapping is a SIMILARITY
// transform (uniform scale + rotation + reflection), not an axis-aligned
// independent-x/y stretch.
//
// Why a similarity and not a per-axis stretch: the geo box aspect ratio usually
// differs wildly from the image aspect ratio (e.g. a 21 m x 108 m box on a
// 1588 x 460 landscape image). An axis-aligned stretch would smear cameras
// across the wrong axis. The two corners form a diagonal; combined with the
// image aspect ratio they determine the rotation. A reflection is always
// required because image pixels are y-down (left-handed) while geo is
// north-up (right-handed). This matches what the production EEN VMS does.

import type { Camera, ConnectionStatus, Floor } from '../types'

export interface Point {
  x: number
  y: number
}

const M_PER_DEG_LAT = 111320

const DEFAULT_RANGE_M = 8
const DEFAULT_FOV_DEG = 60
/** Below this we still draw a thin wedge so direction is visible. */
const MIN_FOV_DEG = 8

/**
 * The similarity transform for a floor plan, precomputed from its corners and
 * the plan image's pixel dimensions. Maps geo (lat/lng) -> plan pixel.
 *
 * Local planar model: meters east/north relative to topLeft, then
 *   [E]   [ a  b ] [px]
 *   [N] = [ b -a ] [py]   (reflection + uniform scale + rotation)
 * inverted to get pixel from meters.
 */
export interface PlanTransform {
  a: number
  b: number
  s2: number // a^2 + b^2 = scale^2 (meters per pixel, squared)
  tlLat: number
  tlLng: number
  mPerLat: number
  mPerLng: number
  pxPerMeter: number
}

export function planTransform(floor: Floor, imgW: number, imgH: number): PlanTransform {
  const tl = floor.topLeftCoordinates
  const br = floor.bottomRightCoordinates
  const midLat = ((tl.latitude + br.latitude) / 2) * (Math.PI / 180)
  const mPerLat = M_PER_DEG_LAT
  const mPerLng = M_PER_DEG_LAT * Math.cos(midLat)

  // bottomRight in local meters relative to topLeft.
  const eBr = (br.longitude - tl.longitude) * mPerLng
  const nBr = (br.latitude - tl.latitude) * mPerLat

  // Solve the reflection-similarity that maps pixel (W,H) -> (eBr, nBr),
  // with pixel (0,0) -> (0,0).
  const den = imgW * imgW + imgH * imgH || 1
  const a = (imgW * eBr - imgH * nBr) / den
  const b = (imgH * eBr + imgW * nBr) / den
  const s2 = a * a + b * b || 1

  return {
    a,
    b,
    s2,
    tlLat: tl.latitude,
    tlLng: tl.longitude,
    mPerLat,
    mPerLng,
    pxPerMeter: 1 / Math.sqrt(s2),
  }
}

/** Map a geo coordinate to a plan pixel via the similarity transform. */
export function projectToPixel(t: PlanTransform, lat: number, lng: number): Point {
  const E = (lng - t.tlLng) * t.mPerLng
  const N = (lat - t.tlLat) * t.mPerLat
  // Inverse of [[a,b],[b,-a]]: (1/(a^2+b^2)) * [[a,b],[b,-a]]
  return {
    x: (t.a * E + t.b * N) / t.s2,
    y: (t.b * E - t.a * N) / t.s2,
  }
}

export interface ConeGeometry {
  apex: Point
  /** Polygon vertices (apex + arc) in plan pixel space. */
  points: Point[]
  /** True when the camera is a full 360° fisheye (drawn as a ring). */
  isRing: boolean
  /** True when there is no usable azimuth (drawn as a plain dot). */
  dotOnly: boolean
}

/**
 * Build a symmetric field-of-view wedge (or ring) for a camera, in plan pixel
 * space. Direction and scale come from the plan transform, so the cone is
 * oriented and sized consistently with the camera positions.
 */
export function buildCone(cam: Camera, t: PlanTransform): ConeGeometry | null {
  const pos = cam.devicePosition
  if (!pos || pos.latitude == null || pos.longitude == null) return null

  const apex = projectToPixel(t, pos.latitude, pos.longitude)
  if (pos.azimuth == null) {
    return { apex, points: [], isRing: false, dotOnly: true }
  }

  const range = pos.rangeInMeters && pos.rangeInMeters > 0 ? pos.rangeInMeters : DEFAULT_RANGE_M
  const radius = range * t.pxPerMeter

  // Heading: a unit step along the compass azimuth (east=sin, north=cos),
  // run through the same linear map so rotation + reflection are applied.
  const theta = (pos.azimuth * Math.PI) / 180
  const dE = Math.sin(theta)
  const dN = Math.cos(theta)
  const hx = t.a * dE + t.b * dN
  const hy = t.b * dE - t.a * dN
  const phi = Math.atan2(hy, hx)

  const arc = (angle: number): Point => ({
    x: apex.x + radius * Math.cos(angle),
    y: apex.y + radius * Math.sin(angle),
  })

  // Fisheye / panoramic: closed ring around the apex.
  if (pos.fieldOfView != null && pos.fieldOfView >= 360) {
    const steps = 48
    const points: Point[] = []
    for (let i = 0; i < steps; i++) points.push(arc((2 * Math.PI * i) / steps))
    return { apex, points, isRing: true, dotOnly: false }
  }

  const fov = pos.fieldOfView != null && pos.fieldOfView > 0 ? pos.fieldOfView : DEFAULT_FOV_DEG
  const half = (Math.max(fov, MIN_FOV_DEG) / 2) * (Math.PI / 180)
  const steps = Math.max(2, Math.ceil((half * 2) / (6 * (Math.PI / 180))))
  const points: Point[] = [apex]
  for (let i = 0; i <= steps; i++) {
    points.push(arc(phi - half + (2 * half * i) / steps))
  }
  return { apex, points, isRing: false, dotOnly: false }
}

export function pointsToSvg(points: Point[]): string {
  return points.map((p) => `${p.x.toFixed(2)},${p.y.toFixed(2)}`).join(' ')
}

/**
 * Approximate dimensions (meters) of the plan's geo box. Used only for the
 * fixture-mode placeholder aspect ratio when no real image is available.
 */
export function planMeters(floor: Floor): { width: number; height: number } {
  const tl = floor.topLeftCoordinates
  const br = floor.bottomRightCoordinates
  const midLat = ((tl.latitude + br.latitude) / 2) * (Math.PI / 180)
  const width = Math.abs(br.longitude - tl.longitude) * M_PER_DEG_LAT * Math.cos(midLat)
  const height = Math.abs(br.latitude - tl.latitude) * M_PER_DEG_LAT
  return { width, height }
}

const STATUS_COLORS: Record<ConnectionStatus, string> = {
  online: '#22c55e',
  off: '#9ca3af',
  deviceOffline: '#ef4444',
  bridgeOffline: '#f59e0b',
  invalidCredentials: '#f59e0b',
  error: '#ef4444',
  unknown: '#9ca3af',
}

export function statusColor(status?: ConnectionStatus): string {
  if (!status) return STATUS_COLORS.unknown
  return STATUS_COLORS[status] ?? STATUS_COLORS.unknown
}

export function statusLabel(status?: ConnectionStatus): string {
  switch (status) {
    case 'online':
      return 'Online'
    case 'off':
      return 'Turned off'
    case 'deviceOffline':
      return 'Device offline'
    case 'bridgeOffline':
      return 'Bridge offline'
    case 'invalidCredentials':
      return 'Invalid credentials'
    case 'error':
      return 'Error'
    default:
      return 'Unknown'
  }
}

/** A camera can be plotted only if it has a lat/lng. */
export function isPlaced(cam: Camera): boolean {
  const p = cam.devicePosition
  return !!p && p.latitude != null && p.longitude != null
}

export function isOnFloor(cam: Camera, floor: Floor): boolean {
  return cam.devicePosition?.floor === floor.floorLevel
}
