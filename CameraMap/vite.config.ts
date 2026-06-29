import { defineConfig, type Plugin } from 'vite'
import react from '@vitejs/plugin-react'
import https from 'node:https'

// Neither the EEN auth server nor the per-account API host send permissive CORS
// headers for browser apps, so both are routed server-side so the browser only
// makes same-origin requests.
//
// The API host is account-specific (api.cXXX.eagleeyenetworks.com) and only
// known after login. Vite's built-in `server.proxy` uses `http-proxy`, which
// has NO per-request `router` option, so it cannot target a dynamic host. This
// plugin proxies `/api/*` manually, choosing the upstream host from the
// `x-een-host` request header the client sends.
//
// For production, replace this with an equivalent server-side proxy/backend.
function eenApiProxy(): Plugin {
  return {
    name: 'een-api-proxy',
    configureServer(server) {
      server.middlewares.use('/api', (req, res) => {
        const raw = req.headers['x-een-host']
        const host = (Array.isArray(raw) ? raw[0] : raw) || 'api.eagleeyenetworks.com'
        const path = req.originalUrl ?? req.url ?? ''

        const headers = { ...req.headers }
        // Talk to the upstream as itself, and drop hop-specific headers.
        headers.host = host
        delete headers['x-een-host']

        console.log(`[api-proxy] ${req.method} -> https://${host}${path}`)

        const upstream = https.request(
          { hostname: host, port: 443, path, method: req.method, headers },
          (upRes) => {
            res.statusCode = upRes.statusCode ?? 502
            for (const [k, v] of Object.entries(upRes.headers)) {
              if (v !== undefined) res.setHeader(k, v as string | string[])
            }
            upRes.pipe(res)
          },
        )
        upstream.on('error', (err) => {
          console.error(`[api-proxy] error: ${err.message}`)
          res.statusCode = 502
          res.end(JSON.stringify({ error: 'proxy_error', message: err.message }))
        })
        req.pipe(upstream)
      })
    },
  }
}

export default defineConfig({
  plugins: [react(), eenApiProxy()],
  server: {
    host: '127.0.0.1',
    port: 3333,
    proxy: {
      '/oauth2': {
        target: 'https://auth.eagleeyenetworks.com',
        changeOrigin: true,
        secure: true,
      },
    },
  },
})
