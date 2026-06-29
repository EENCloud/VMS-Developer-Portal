// Thin fetch wrapper for the EEN v3 API: prepends the per-account base URL,
// adds the Bearer header, transparently refreshes on 401, and offers a
// pagination helper. See concept.md §3.4 / §4.

import { getAccessToken, getBaseUrl, refresh } from '../auth/oauth'
import type { Paginated } from '../types'

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message)
    this.name = 'ApiError'
  }
}

/** Raised when authentication is unrecoverable; UI should restart login. */
export class AuthExpiredError extends Error {
  constructor() {
    super('Authentication expired — please log in again.')
    this.name = 'AuthExpiredError'
  }
}

async function rawFetch(path: string, accept = 'application/json'): Promise<Response> {
  const base = getBaseUrl()
  if (!base) throw new AuthExpiredError()
  const clean = path.startsWith('/') ? path : `/${path}`
  // Same-origin request routed through the Vite dev proxy; the proxy targets the
  // account-specific host carried in `x-een-host` (see vite.config.ts).
  return fetch(`/api/v3.0${clean}`, {
    headers: {
      Authorization: `Bearer ${getAccessToken()}`,
      Accept: accept,
      'x-een-host': base,
    },
  })
}

/** GET JSON, retrying once after a token refresh on 401. */
export async function apiGet<T>(path: string): Promise<T> {
  let res = await rawFetch(path)
  if (res.status === 401) {
    const ok = await refresh()
    if (!ok) throw new AuthExpiredError()
    res = await rawFetch(path)
    if (res.status === 401) throw new AuthExpiredError()
  }
  if (!res.ok) {
    throw new ApiError(res.status, `GET ${path} failed: ${res.status} ${await res.text()}`)
  }
  return res.json() as Promise<T>
}

/**
 * GET a binary resource (e.g. a floor-plan image) as an object URL.
 * Uses `Accept: *​/*` — EEN's floor-image endpoint returns 406 for a specific
 * type like `image/png` and only honors the wildcard. The response is still
 * checked for a JSON error body so failures surface instead of becoming a
 * broken image.
 */
export async function apiGetObjectUrl(path: string, accept = '*/*'): Promise<string> {
  let res = await rawFetch(path, accept)
  if (res.status === 401) {
    const ok = await refresh()
    if (!ok) throw new AuthExpiredError()
    res = await rawFetch(path, accept)
    if (res.status === 401) throw new AuthExpiredError()
  }
  if (!res.ok) {
    throw new ApiError(res.status, `GET ${path} failed: ${res.status} ${await res.text()}`)
  }
  const contentType = res.headers.get('content-type') ?? ''
  if (contentType.includes('application/json')) {
    throw new ApiError(res.status, `GET ${path} returned JSON, not binary: ${await res.text()}`)
  }
  return URL.createObjectURL(await res.blob())
}

/**
 * Fetch every page of a cursor-paginated list endpoint.
 * `path` may already contain query params; pageToken/pageSize are appended.
 */
export async function apiGetAll<T>(path: string, pageSize = 100): Promise<T[]> {
  const results: T[] = []
  let pageToken = ''
  const sep = path.includes('?') ? '&' : '?'
  do {
    const tokenParam = pageToken ? `&pageToken=${encodeURIComponent(pageToken)}` : ''
    const page = await apiGet<Paginated<T>>(`${path}${sep}pageSize=${pageSize}${tokenParam}`)
    results.push(...page.results)
    pageToken = page.nextPageToken || ''
  } while (pageToken)
  return results
}
