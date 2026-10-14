import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  build: {
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (id.includes('/node_modules/three/')) return 'three-core'
          if (
            id.includes('/node_modules/@react-three/') ||
            id.includes('/node_modules/three-stdlib/')
          )
            return 'three-tools'
          if (
            id.includes('/node_modules/react') ||
            id.includes('/node_modules/@remix-run/')
          )
            return 'react-vendor'
        },
      },
    },
  },
  server: {
    port: 5173,
    host: true,
    proxy: Object.fromEntries(
      ['/api', '/files', '/media', '/health'].map((path) => [
        path,
        { target: 'http://127.0.0.1:8000', changeOrigin: true },
      ]),
    ),
  },
})
