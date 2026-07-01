import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'

// Alvo da API no dev. Configurável por VITE_API_TARGET (ex.: se a 8000 já estiver
// ocupada por outro serviço, use http://127.0.0.1:8010). Default: 8000.
declare const process: { env: Record<string, string | undefined> }
const API_TARGET = process.env.VITE_API_TARGET || 'http://127.0.0.1:8000'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./src/test/setup.ts'],
    css: false,
  },
  server: {
    proxy: {
      // Encaminha chamadas do frontend para a API FastAPI (Ollama local).
      // Evita CORS em dev e mantém o app local-first.
      '/api': {
        target: API_TARGET,
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ''),
      },
    },
  },
})
