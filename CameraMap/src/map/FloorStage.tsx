import { useEffect, useMemo, useState } from 'react'
import type { Camera, Floor } from '../types'
import { isOnFloor, isPlaced, planMeters, planTransform } from './geo'
import { CameraMarker } from './CameraMarker'

interface Dims {
  w: number
  h: number
}

interface Props {
  floor: Floor
  /** Object URL of the plan image, or null to render a placeholder. */
  imageUrl: string | null
  cameras: Camera[]
  selectedId: string | null
  onSelect: (id: string | null) => void
  /**
   * Image pixel size to use when there is no real image (fixture mode). The
   * similarity transform depends on the true image aspect ratio, so this should
   * match the real plan's dimensions for placement to look correct.
   */
  placeholderSize?: Dims
}

/** Fallback placeholder dimensions from the plan's geo aspect (last resort). */
function geoAspectDims(floor: Floor): Dims {
  const m = planMeters(floor)
  const aspect = m.height > 0 ? m.width / m.height : 1
  const h = 1000
  return { w: Math.max(60, Math.round(h * aspect)), h }
}

export function FloorStage({
  floor,
  imageUrl,
  cameras,
  selectedId,
  onSelect,
  placeholderSize,
}: Props) {
  const [dims, setDims] = useState<Dims | null>(null)
  const [hoveredId, setHoveredId] = useState<string | null>(null)

  useEffect(() => {
    if (!imageUrl) {
      setDims(placeholderSize ?? geoAspectDims(floor))
      return
    }
    setDims(null)
    const img = new Image()
    img.onload = () => setDims({ w: img.naturalWidth, h: img.naturalHeight })
    img.onerror = () => setDims(placeholderSize ?? geoAspectDims(floor))
    img.src = imageUrl
  }, [imageUrl, floor, placeholderSize])

  const placed = useMemo(
    () => cameras.filter((c) => isPlaced(c) && isOnFloor(c, floor)),
    [cameras, floor],
  )

  const transform = useMemo(
    () => (dims ? planTransform(floor, dims.w, dims.h) : null),
    [floor, dims],
  )

  if (!dims || !transform) {
    return <div className="stage-loading">Loading floor plan…</div>
  }

  const unit = (Math.hypot(dims.w, dims.h) / 150) * 0.8

  return (
    <div className="stage-scroll">
      <svg
        className="stage-svg"
        width={dims.w}
        height={dims.h}
        viewBox={`0 0 ${dims.w} ${dims.h}`}
        preserveAspectRatio="xMidYMid meet"
        onClick={() => onSelect(null)}
        role="img"
        aria-label={`Floor plan: ${floor.name}`}
      >
        {imageUrl ? (
          <image href={imageUrl} x={0} y={0} width={dims.w} height={dims.h} />
        ) : (
          <PlaceholderPlan w={dims.w} h={dims.h} />
        )}

        {placed.map((cam) => (
          <CameraMarker
            key={cam.id}
            camera={cam}
            transform={transform}
            unit={unit}
            selected={cam.id === selectedId}
            hovered={cam.id === hoveredId}
            onSelect={onSelect}
            onHover={setHoveredId}
          />
        ))}
      </svg>
    </div>
  )
}

function PlaceholderPlan({ w, h }: Dims) {
  const step = Math.max(w, h) / 20
  const lines: JSX.Element[] = []
  for (let x = step; x < w; x += step) {
    lines.push(<line key={`v${x}`} x1={x} y1={0} x2={x} y2={h} stroke="#1e293b" strokeWidth={1} />)
  }
  for (let y = step; y < h; y += step) {
    lines.push(<line key={`h${y}`} x1={0} y1={y} x2={w} y2={y} stroke="#1e293b" strokeWidth={1} />)
  }
  return (
    <g>
      <rect x={0} y={0} width={w} height={h} fill="#0f172a" stroke="#334155" strokeWidth={2} />
      {lines}
      <text
        x={w / 2}
        y={h / 2}
        textAnchor="middle"
        fill="#475569"
        fontSize={Math.max(w, h) / 28}
        style={{ fontFamily: 'system-ui, sans-serif' }}
      >
        floor-plan placeholder
      </text>
    </g>
  )
}
