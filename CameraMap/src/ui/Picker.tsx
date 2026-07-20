import type { Floor, Location } from '../types'

interface Props {
  locations: Location[]
  selectedLocationId: string | null
  onSelectLocation: (id: string) => void
  floors: Floor[]
  selectedFloorId: string | null
  onSelectFloor: (id: string) => void
  loadingLocations?: boolean
}

export function Picker({
  locations,
  selectedLocationId,
  onSelectLocation,
  floors,
  selectedFloorId,
  onSelectFloor,
  loadingLocations,
}: Props) {
  return (
    <div className="picker">
      <label className="picker-field">
        <span>Location</span>
        <select
          value={selectedLocationId ?? ''}
          disabled={loadingLocations || locations.length === 0}
          onChange={(e) => onSelectLocation(e.target.value)}
        >
          <option value="" disabled>
            {loadingLocations
              ? 'Loading…'
              : locations.length === 0
                ? 'No locations'
                : 'Select a location…'}
          </option>
          {locations.map((loc) => (
            <option key={loc.id} value={loc.id}>
              {loc.name}
            </option>
          ))}
        </select>
      </label>

      {floors.length > 0 && (
        <label className="picker-field">
          <span>Floor</span>
          <select
            value={selectedFloorId ?? ''}
            onChange={(e) => onSelectFloor(e.target.value)}
          >
            {floors.map((f) => (
              <option key={f.id} value={f.id}>
                {f.name} (level {f.floorLevel})
              </option>
            ))}
          </select>
        </label>
      )}
    </div>
  )
}
