// OAuth 2.0 authorization-code flow against Eagle Eye Networks.
// Mirrors the existing Live Video Angular demo: confidential-client exchange in
// the browser, credentials from Vite env vars, tokens in localStorage.
// See concept.md §3.

const CLIENT_ID = import.meta.env.VITE_EEN_CLIENT_ID
const CLIENT_SECRET = import.meta.env.VITE_EEN_CLIENT_SECRET
const REDIRECT_URI = import.meta.env.VITE_EEN_REDIRECT_URI

const AUTHORIZE_URL = 'https://auth.eagleeyenetworks.com/oauth2/authorize'
// Relative path -> routed through the Vite dev proxy (see vite.config.ts) to
// avoid CORS on the token endpoint.
const TOKEN_URL = '/oauth2/token'

const KEY_ACCESS = 'access_token'
const KEY_REFRESH = 'refresh_token'
const KEY_BASE = 'base_url'

interface TokenResponse {
  access_token: string
  refresh_token?: string
  expires_in: number
  httpsBaseUrl?: { hostname: string; port: number }
}

/**
 * Build the authorization URL. The redirect_uri must NOT be percent-encoded —
 * EEN matches it byte-for-byte against the whitelisted value (concept.md §3.2).
 */
export function getAuthUrl(): string {
  return (
    `${AUTHORIZE_URL}` +
    `?response_type=code` +
    `&scope=vms.all` +
    `&client_id=${CLIENT_ID}` +
    `&redirect_uri=${REDIRECT_URI}`
  )
}

async function postToken(body: Record<string, string>): Promise<TokenResponse> {
  const credentials = btoa(`${CLIENT_ID}:${CLIENT_SECRET}`)
  const res = await fetch(TOKEN_URL, {
    method: 'POST',
    headers: {
      Authorization: `Basic ${credentials}`,
      'Content-Type': 'application/x-www-form-urlencoded',
      Accept: 'application/json',
    },
    body: new URLSearchParams(body),
  })
  if (!res.ok) {
    throw new Error(`Token request failed: ${res.status} ${await res.text()}`)
  }
  return res.json()
}

function storeSession(token: TokenResponse): void {
  localStorage.setItem(KEY_ACCESS, token.access_token)
  if (token.refresh_token) localStorage.setItem(KEY_REFRESH, token.refresh_token)
  if (token.httpsBaseUrl?.hostname) {
    localStorage.setItem(KEY_BASE, token.httpsBaseUrl.hostname)
  }
}

export async function exchangeCode(code: string): Promise<void> {
  const token = await postToken({
    grant_type: 'authorization_code',
    scope: 'vms.all',
    code,
    redirect_uri: REDIRECT_URI,
  })
  storeSession(token)
}

/** Refresh the access token. Returns false if no refresh token or it failed. */
export async function refresh(): Promise<boolean> {
  const refreshToken = localStorage.getItem(KEY_REFRESH)
  if (!refreshToken) return false
  try {
    const token = await postToken({
      grant_type: 'refresh_token',
      scope: 'vms.all',
      refresh_token: refreshToken,
    })
    storeSession(token)
    return true
  } catch {
    return false
  }
}

export function getAccessToken(): string {
  return localStorage.getItem(KEY_ACCESS) ?? ''
}

export function getBaseUrl(): string {
  return localStorage.getItem(KEY_BASE) ?? ''
}

export function isAuthenticated(): boolean {
  return !!localStorage.getItem(KEY_ACCESS)
}

export function logout(): void {
  localStorage.removeItem(KEY_ACCESS)
  localStorage.removeItem(KEY_REFRESH)
  localStorage.removeItem(KEY_BASE)
}
