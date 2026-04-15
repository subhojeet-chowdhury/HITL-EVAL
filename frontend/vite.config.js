import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// LESSON — Vite proxy:
// In dev, the React app runs on port 5173 and the FastAPI backend on 8000.
// The proxy tells Vite: "any request starting with /api should be forwarded
// to the backend on port 8000 — don't handle it yourself."
// This avoids CORS issues in development.
// In production, both are served from the same FastAPI server.

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      }
    }
  }
})
