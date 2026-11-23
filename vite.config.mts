import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import tailwindcss from '@tailwindcss/vite'
import path from 'node:path'

export default defineConfig({
  // Keep the existing GitHub Pages deployment path.
  base: '/GeoAI/',
  resolve: {
    alias: {
      '@': path.resolve(process.cwd(), 'docs/src'),
    },
  },
  worker: {
    format: 'es',
  },
  plugins: [
    vue(),
    tailwindcss(),
  ],
})
