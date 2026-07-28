import { fileURLToPath, URL } from 'node:url'

import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import vueDevTools from 'vite-plugin-vue-devtools'

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    vue(),
    vueDevTools(),
  ],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
      'controller': fileURLToPath(new URL('./src/controller_src', import.meta.url)),
    },
  },
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:8001',
        changeOrigin: true,
        secure: false,
        rewrite: (path) => path.replace(/^\/api/, ''),
        ws: true,
      },
    },
    host: true,
    allowedHosts: ["sl-xps15-fedora"],
    port: 5174,
  },
  build: {
    rolldownOptions: {
      output: {
        codeSplitting: {
          maxModuleSize: 30000,
          groups: [
            {
              name: 'large-libs',
              test: /node_modules/,
              minSize: 100000, // 100KB
              maxSize: 250000, // 250KB
              priority: 10,
            }
          ]
        }
      }
    }
  }
})
