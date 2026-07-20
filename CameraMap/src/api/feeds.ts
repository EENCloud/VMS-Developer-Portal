// Optional live preview (concept.md §6.4). Establishes the media-session cookie
// then returns a preview multipartUrl that plays in a plain <img> (no player
// library). See een-api skill 04-get-live-feed.md.

import { getAccessToken, getBaseUrl } from '../auth/oauth'
import { apiGet } from './client'
import type { Paginated } from '../types'

interface Feed {
  id: string
  type: string
  deviceId: string
  multipartUrl?: string
}

let sessionEstablished = false

/**
 * Two-step media-session cookie setup. Must complete before any stream URL is
 * loaded, or the media server returns 403. Idempotent within a page session.
 */
export async function ensureMediaSession(): Promise<void> {
  if (sessionEstablished) return
  const base = getBaseUrl()
  const token = getAccessToken()
  // Routed through the dev proxy like the rest of /api.
  const res = await fetch(`/api/v3.0/media/session`, {
    headers: { Authorization: `Bearer ${token}`, 'x-een-host': base },
    credentials: 'include',
  })
  if (!res.ok) throw new Error(`media/session failed: ${res.status}`)
  const { url } = (await res.json()) as { url: string }
  // NOTE: this returns an absolute media.cXXX host and will hit CORS in the
  // browser; live preview is best-effort in dev and may require a media proxy.
  await fetch(url, {
    headers: { Authorization: `Bearer ${token}` },
    credentials: 'include',
  })
  sessionEstablished = true
}

/**
 * Returns a preview MJPEG URL for the camera, or null if the camera is offline
 * (the API returns an empty results array for offline cameras).
 */
export async function getPreviewUrl(deviceId: string): Promise<string | null> {
  await ensureMediaSession()
  const data = await apiGet<Paginated<Feed>>(
    `/feeds?deviceId=${encodeURIComponent(deviceId)}&type=preview&include=multipartUrl`,
  )
  return data.results[0]?.multipartUrl ?? null
}
