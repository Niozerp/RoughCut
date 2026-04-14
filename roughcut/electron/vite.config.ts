import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'
import fs from 'fs'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [
    react(),
    {
      name: 'copy-version-md',
      writeBundle() {
        // Copy version.md to dist folder after build
        const srcPath = path.resolve(__dirname, 'version.md')
        const destPath = path.resolve(__dirname, 'dist', 'version.md')
        if (fs.existsSync(srcPath)) {
          fs.copyFileSync(srcPath, destPath)
          console.log('[Vite] Copied version.md to dist')
        }
      }
    }
  ],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  base: './',
  build: {
    outDir: 'dist',
    emptyOutDir: false,
  },
})
