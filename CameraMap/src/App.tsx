import { useEffect, useState } from 'react'
import { exchangeCode, getAuthUrl, isAuthenticated, logout } from './auth/oauth'
import { MapView } from './MapView'

type View =
  | { kind: 'login' }
  | { kind: 'callback' }
  | { kind: 'map'; demo: boolean }

const FIXTURES_ENV = import.meta.env.VITE_USE_FIXTURES === 'true'

function initialView(): View {
  const { pathname, search } = window.location
  const params = new URLSearchParams(search)
  if (pathname === '/callback' && params.get('code')) return { kind: 'callback' }
  if (FIXTURES_ENV || params.get('demo') === '1') return { kind: 'map', demo: true }
  if (isAuthenticated()) return { kind: 'map', demo: false }
  return { kind: 'login' }
}

export default function App() {
  const [view, setView] = useState<View>(initialView)
  const [authError, setAuthError] = useState<string | null>(null)

  // Handle the OAuth redirect: exchange ?code= for tokens, then land on the map.
  useEffect(() => {
    if (view.kind !== 'callback') return
    const code = new URLSearchParams(window.location.search).get('code')!
    let cancelled = false
    exchangeCode(code)
      .then(() => {
        if (cancelled) return
        window.history.replaceState({}, '', '/')
        setView({ kind: 'map', demo: false })
      })
      .catch((e) => {
        if (cancelled) return
        setAuthError(e instanceof Error ? e.message : String(e))
        window.history.replaceState({}, '', '/')
        setView({ kind: 'login' })
      })
    return () => {
      cancelled = true
    }
  }, [view.kind])

  if (view.kind === 'callback') {
    return <div className="centered">Signing you in…</div>
  }

  if (view.kind === 'map') {
    return (
      <MapView
        demo={view.demo}
        onLogout={() => {
          if (!view.demo) logout()
          window.history.replaceState({}, '', '/')
          setView({ kind: 'login' })
        }}
        onAuthExpired={() => {
          logout()
          setAuthError('Your session expired. Please log in again.')
          setView({ kind: 'login' })
        }}
      />
    )
  }

  return (
    <div className="centered login">
      <h1>Camera Map</h1>
      <p>View your Eagle Eye Networks cameras on a floor plan.</p>
      {authError && <div className="banner error">{authError}</div>}
      <div className="login-actions">
        <a className="btn primary" href={getAuthUrl()}>
          Log in with Eagle Eye Networks
        </a>
        <button
          className="btn"
          onClick={() => {
            window.history.replaceState({}, '', '/?demo=1')
            setView({ kind: 'map', demo: true })
          }}
        >
          Explore demo data
        </button>
      </div>
    </div>
  )
}
