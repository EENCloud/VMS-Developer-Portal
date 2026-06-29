import type { Camera } from '../types'
import { buildCone, pointsToSvg, projectToPixel, statusColor, type PlanTransform } from './geo'

interface Props {
  camera: Camera
  transform: PlanTransform
  /** Base size unit in plan-pixel space, so markers scale with the image. */
  unit: number
  selected: boolean
  hovered: boolean
  onSelect: (id: string) => void
  onHover: (id: string | null) => void
}

export function CameraMarker({
  camera,
  transform,
  unit,
  selected,
  hovered,
  onSelect,
  onHover,
}: Props) {
  const cone = buildCone(camera, transform)
  if (!cone) return null

  const pos = camera.devicePosition!
  const apex = projectToPixel(transform, pos.latitude!, pos.longitude!)
  const color = statusColor(camera.status?.connectionStatus)
  const active = selected || hovered
  const r = unit * (active ? 1.5 : 1)

  return (
    <g
      className="camera-marker"
      onClick={(e) => {
        e.stopPropagation()
        onSelect(camera.id)
      }}
      onMouseEnter={() => onHover(camera.id)}
      onMouseLeave={() => onHover(null)}
      style={{ cursor: 'pointer' }}
    >
      {/* Field-of-view cone / ring */}
      {!cone.dotOnly && cone.points.length > 0 && (
        <polygon
          points={pointsToSvg(cone.points)}
          fill={color}
          fillOpacity={active ? 0.35 : 0.18}
          stroke={color}
          strokeOpacity={0.7}
          strokeWidth={unit * 0.25}
        />
      )}

      {/* Camera body */}
      <circle
        cx={apex.x}
        cy={apex.y}
        r={r}
        fill={color}
        stroke="#0b1220"
        strokeWidth={unit * 0.3}
      />
      {selected && (
        <circle
          cx={apex.x}
          cy={apex.y}
          r={r + unit * 0.9}
          fill="none"
          stroke={color}
          strokeWidth={unit * 0.35}
        />
      )}

      {/* Label on hover/selection */}
      {active && (
        <g transform={`translate(${apex.x + r + unit * 0.6}, ${apex.y})`}>
          <text
            x={0}
            y={unit * 0.4}
            fontSize={unit * 2.4}
            fill="#f8fafc"
            stroke="#0b1220"
            strokeWidth={unit * 0.4}
            paintOrder="stroke"
            style={{ fontFamily: 'system-ui, sans-serif', fontWeight: 600 }}
          >
            {camera.name}
          </text>
        </g>
      )}
    </g>
  )
}
