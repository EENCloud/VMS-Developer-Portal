/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_EEN_CLIENT_ID: string
  readonly VITE_EEN_CLIENT_SECRET: string
  readonly VITE_EEN_REDIRECT_URI: string
  readonly VITE_USE_FIXTURES?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
