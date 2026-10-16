import path from 'node:path'
import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig, loadEnv } from 'vite'

// Запросы /api уходят на backend: так cookie сессии остаются на одном адресе с приложением,
// и CORS не нужен.
const backend = process.env.BACKEND_URL ?? 'http://localhost:8000'

// Как backend без config.toml: без обязательных настроек приложение не стартует и называет каждую.
const REQUIRED_ENV = ['VITE_MAX_FILE_SIZE_BYTES', 'VITE_PASSWORD_MIN_LENGTH', 'VITE_PASSWORD_MAX_LENGTH']

export default defineConfig(({ mode }) => {
  const env = { ...loadEnv(mode, import.meta.dirname), ...process.env }
  const missing = REQUIRED_ENV.filter((name) => !/^\d+$/.test(env[name] ?? ''))
  if (missing.length) {
    throw new Error(`Не заданы настройки: ${missing.join(', ')}. Скопируйте frontend/.env.example в frontend/.env.`)
  }
  return {
    plugins: [react(), tailwindcss()],
    resolve: {
      alias: { '@': path.resolve(import.meta.dirname, './src') },
    },
    build: {
      rolldownOptions: {
        output: {
          // Библиотеки — отдельными частями: они меняются реже кода приложения и дольше живут в кэше.
          codeSplitting: {
            groups: [
              { name: 'react', test: /node_modules[\\/](react|react-dom|react-router|scheduler)[\\/]/ },
              { name: 'ui', test: /node_modules[\\/](radix-ui|@radix-ui|lucide-react|sonner|cmdk|react-day-picker|date-fns)[\\/]/ },
              { name: 'motion', test: /node_modules[\\/](motion|motion-dom|motion-utils|framer-motion)[\\/]/ },
              { name: 'data', test: /node_modules[\\/](@tanstack|openapi-fetch|zod|react-hook-form|@hookform)[\\/]/ },
            ],
          },
        },
      },
    },
    server: {
      port: 5173,
      proxy: {
        '/api': { target: backend, changeOrigin: true, ws: true },
      },
    },
  }
})
