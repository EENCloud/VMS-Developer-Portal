import { useEffect, useMemo, useState } from 'react'
import type { Camera, Floor, Location } from './types'
import { AuthExpiredError } from './api/client'
import { fetchFloorImageUrl, listFloors, listLocations } from './api/locations'
import { listCameras } from './api/cameras'
import {
  fixtureCameras,
  fixtureFloors,
  fixtureLocationId,
  fixtureLocations,
  fixturePlanSize,
} from './api/fixtures'
import { isOnFloor, isPlaced } from './map/geo'
import { FloorStage } from './map/FloorStage'
import { CameraDetail } from './ui/CameraDetail'
import { Picker } from './ui/Picker'

interface Props {
  demo: boolean
  onLogout: () => void
  onAuthExpired: () => void
}

/** Prefer a floor with an uploaded plan; otherwise the first floor. */
function pickFloor(floors: Floor[]): Floor | undefined {
  return floors.find((f) => (f.floorPlans?.length ?? 0) > 0) ?? floors[0]
}

export function MapView({ demo, onLogout, onAuthExpired }: Props) {
  const [locations, setLocations] = useState<Location[]>([])
  const [locationId, setLocationId] = useState<string | null>(null)
  const [cameras, setCameras] = useState<Camera[]>([])
  const [floors, setFloors] = useState<Floor[]>([])
  const [floorId, setFloorId] = useState<string | null>(null)
  const [imageUrl, setImageUrl] = useState<string | null>(null)
  const [selectedCameraId, setSelectedCameraId] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loadingLocations, setLoadingLocations] = useState(true)
  const [loadingFloor, setLoadingFloor] = useState(false)

  const handleError = (e: unknown) => {
    if (e instanceof AuthExpiredError) {
      onAuthExpired()
      return
    }
    setError(e instanceof Error ? e.message : String(e))
  }

  // 1. On login, load all locations. Do NOT auto-select — the user picks.
  useEffect(() => {
    let cancelled = false
    setLoadingLocations(true)
    setError(null)
    const load = async () => {
      try {
        const locs = demo ? fixtureLocations : await listLocations()
        if (cancelled) return
        locs.sort((a, b) => a.name.localeCompare(b.name))
        setLocations(locs)
        console.info(`[CameraMap] locations=${locs.length}`)
        // Demo has a single location — select it for convenience.
        if (demo) setLocationId(fixtureLocationId)
        else if (locs.length === 0) {
          setError(
            'No locations found. Location-based grouping (floors/plans) requires a ' +
              'professional or enterprise edition account.',
          )
        }
      } catch (e) {
        if (!cancelled) handleError(e)
      } finally {
        if (!cancelled) setLoadingLocations(false)
      }
    }
    load()
    return () => {
      cancelled = true
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [demo])

  // 2. When a location is selected, load its floors and cameras.
  useEffect(() => {
    if (!locationId) {
      setFloors([])
      setFloorId(null)
      setCameras([])
      return
    }
    let cancelled = false
    setLoadingFloor(true)
    setError(null)
    setSelectedCameraId(null)
    const load = async () => {
      try {
        const [flrs, cams] = await Promise.all([
          demo ? Promise.resolve(fixtureFloors()) : listFloors(locationId),
          demo ? Promise.resolve(fixtureCameras()) : listCameras(locationId),
        ])
        if (cancelled) return
        setFloors(flrs)
        setCameras(cams)
        setFloorId(pickFloor(flrs)?.id ?? null)
        console.info(
          `[CameraMap] location=${locationId} floors=${flrs.length} ` +
            `withPlan=${flrs.filter((f) => (f.floorPlans?.length ?? 0) > 0).length} ` +
            `cameras=${cams.length} placed=${cams.filter(isPlaced).length}`,
        )
        if (flrs.length === 0) {
          setError('This location has no floors. Pick another location.')
        }
      } catch (e) {
        if (!cancelled) handleError(e)
      } finally {
        if (!cancelled) setLoadingFloor(false)
      }
    }
    load()
    return () => {
      cancelled = true
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [locationId, demo])

  const floor = useMemo(() => floors.find((f) => f.id === floorId) ?? null, [floors, floorId])

  // 3. When the floor changes, fetch its plan image (revoking the previous one).
  useEffect(() => {
    if (!floor || !locationId) {
      setImageUrl(null)
      return
    }
    if (demo) {
      // Bundled sample plan served from public/ (matches the fixture floor).
      setImageUrl('/floor-plan.png')
      return
    }
    let cancelled = false
    let createdUrl: string | null = null
    setImageUrl(null)
    const load = async () => {
      try {
        const result = await fetchFloorImageUrl(locationId, floor)
        if (cancelled) {
          if (result) URL.revokeObjectURL(result.url)
          return
        }
        if (result) {
          createdUrl = result.url
          setImageUrl(result.url)
        }
      } catch (e) {
        if (!cancelled) handleError(e)
      }
    }
    load()
    return () => {
      cancelled = true
      if (createdUrl) URL.revokeObjectURL(createdUrl)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [floor, locationId, demo])

  const onFloor = useMemo(
    () => (floor ? cameras.filter((c) => isOnFloor(c, floor)) : []),
    [cameras, floor],
  )
  const placedCount = onFloor.filter(isPlaced).length
  const unplaced = onFloor.filter((c) => !isPlaced(c))
  const selectedCamera = useMemo(
    () => cameras.find((c) => c.id === selectedCameraId) ?? null,
    [cameras, selectedCameraId],
  )

  return (
    <div className="app">
      <header className="topbar">
        <div className="topbar-title">
          <strong>Camera Map</strong>
          {demo && <span className="badge">demo data</span>}
        </div>
        <Picker
          locations={locations}
          selectedLocationId={locationId}
          onSelectLocation={setLocationId}
          floors={floors}
          selectedFloorId={floorId}
          onSelectFloor={setFloorId}
          loadingLocations={loadingLocations}
        />
        <button className="link-btn" onClick={onLogout}>
          {demo ? 'Exit demo' : 'Log out'}
        </button>
      </header>

      {error && <div className="banner error">{error}</div>}

      <main className="layout">
        <section className="stage-pane">
          {loadingFloor && <div className="banner">Loading…</div>}

          {!locationId ? (
            !loadingLocations &&
            locations.length > 0 && (
              <div className="banner">
                Select a location to view its floor plan ({locations.length} available).
              </div>
            )
          ) : floor ? (
            <>
              <div className="stage-meta">
                {floor.name} · {placedCount} placed camera{placedCount === 1 ? '' : 's'}
                {unplaced.length > 0 && ` · ${unplaced.length} unplaced`}
              </div>
              <FloorStage
                floor={floor}
                imageUrl={imageUrl}
                cameras={cameras}
                selectedId={selectedCameraId}
                onSelect={setSelectedCameraId}
                placeholderSize={demo ? fixturePlanSize : undefined}
              />
            </>
          ) : (
            !loadingFloor && (
              <div className="banner">No floor with a plan was found for this location.</div>
            )
          )}

          {unplaced.length > 0 && (
            <details className="unplaced">
              <summary>{unplaced.length} camera(s) on this floor without a position</summary>
              <ul>
                {unplaced.map((c) => (
                  <li key={c.id}>
                    <button className="link-btn" onClick={() => setSelectedCameraId(c.id)}>
                      {c.name}
                    </button>
                  </li>
                ))}
              </ul>
            </details>
          )}
        </section>

        <CameraDetail camera={selectedCamera} livePreview={!demo} />
      </main>
    </div>
  )
}
