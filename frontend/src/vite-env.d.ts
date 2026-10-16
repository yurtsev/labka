/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_MODE?: 'mock' | 'real'
  readonly VITE_MAX_FILE_SIZE_BYTES: string
  readonly VITE_PASSWORD_MIN_LENGTH: string
  readonly VITE_PASSWORD_MAX_LENGTH: string
}
