import { useEffect, useState } from 'react'
import type { Camera } from '../types'
import { statusColor, statusLabel } from '../map/geo'
import { getPreviewUrl } from '../api/feeds'

interface Props {
  camera: Camera | null
  /** Live preview is only attempted when not in fixture/demo mode. */
  livePreview: boolean
}

function fmt(n: number | null | undefined, digits = 2, suffix = ''): string {
  return n == null ? '—' : `${n.toFixed(digits)}${suffix}`
}

export function CameraDetail({ camera, livePreview }: Props) {
  const [previewUrl, setPreviewUrl] = useState<string | null>(null)
  const [previewState, setPreviewState] = useState<'idle' | 'loading' | 'none' | 'error'>('idle')

  useEffect(() => {
    setPreviewUrl(null)
    setPreviewState('idle')
    if (!camera || !livePreview) return
    if (camera.status?.connectionStatus !== 'online') {
      setPreviewState('none')
      return
    }
    let cancelled = false
    setPreviewState('loading')
    getPreviewUrl(camera.id)
      .then((url) => {
        if (cancelled) return
        if (url) {
          setPreviewUrl(url)
          setPreviewState('idle')
        } else {
          setPreviewState('none')
        }
      })
      .catch(() => !cancelled && setPreviewState('error'))
    return () => {
      cancelled = true
    }
  }, [camera, livePreview])

  if (!camera) {
    return (
      <aside className="detail detail-empty">
        <p>Select a camera on the plan to see its details.</p>
      </aside>
    )
  }

  const pos = camera.devicePosition
  const status = camera.status?.connectionStatus

  return (
    <aside className="detail">
      <header className="detail-header">
        <span className="status-dot" style={{ background: statusColor(status) }} />
        <h2>{camera.name}</h2>
      </header>

      {livePreview && (
        <div className="detail-preview">
          {previewUrl && <img src={previewUrl} alt={`${camera.name} preview`} />}
          {previewState === 'loading' && <div className="preview-msg">Loading preview…</div>}
          {previewState === 'none' && <div className="preview-msg">No live preview available</div>}
          {previewState === 'error' && <div className="preview-msg">Preview failed to load</div>}
        </div>
      )}

      <dl className="detail-grid">
        <dt>Status</dt>
        <dd>{statusLabel(status)}</dd>
        <dt>Camera ID</dt>
        <dd>{camera.id}</dd>
        <dt>Floor level</dt>
        <dd>{pos?.floor ?? '—'}</dd>
        <dt>Latitude</dt>
        <dd>{fmt(pos?.latitude, 6)}</dd>
        <dt>Longitude</dt>
        <dd>{fmt(pos?.longitude, 6)}</dd>
        <dt>Azimuth</dt>
        <dd>{fmt(pos?.azimuth, 1, '°')}</dd>
        <dt>Field of view</dt>
        <dd>{fmt(pos?.fieldOfView, 1, '°')}</dd>
        <dt>Range</dt>
        <dd>{fmt(pos?.rangeInMeters, 1, ' m')}</dd>
      </dl>
    </aside>
  )
}
