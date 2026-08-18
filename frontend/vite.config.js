import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

const BACKEND = 'http://127.0.0.1:8000'

export default defineConfig({
  plugins: [react()],
  build: {
    outDir: 'dist',
    emptyOutDir: true,
  },
  server: {
    port: 5173,
    proxy: {
      '/stats': BACKEND,
      '/jobs': BACKEND,
      '/health': BACKEND,
      '/ingestion': BACKEND,
    },
  },
})
