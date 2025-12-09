import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  server: {
    proxy: {
      // Proxy API requests to FastAPI backend
      '/agencies': {
        target: 'http://localhost:8001',
        changeOrigin: true,
      },
      '/lists': {
        target: 'http://localhost:8001',
        changeOrigin: true,
      },
      '/scrape': {
        target: 'http://localhost:8001',
        changeOrigin: true,
      },
      '/health': {
        target: 'http://localhost:8001',
        changeOrigin: true,
      },
      '/counties': {
        target: 'http://localhost:8001',
        changeOrigin: true,
      },
    },
  },
})
