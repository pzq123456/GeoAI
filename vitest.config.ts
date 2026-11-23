import { defineConfig } from 'vitest/config'
import path from 'node:path'

export default defineConfig({
  resolve: {
    alias: {
      '@': path.resolve(process.cwd(), 'docs/src'),
    },
  },
  test: {
    environment: 'node',
    include: ['docs/src/core/**/*.test.ts'],
  },
})
