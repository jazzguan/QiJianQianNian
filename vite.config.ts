import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 5173,
    host: true,
    proxy: {
      '/api/comparison': 'http://127.0.0.1:8001',
      '/api/measure': 'http://127.0.0.1:8001',
      '/api/compare': 'http://127.0.0.1:8001',
    },
  },
})
