import { fileURLToPath, URL } from 'node:url'

import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import vueDevTools from 'vite-plugin-vue-devtools'
import { VitePWA } from 'vite-plugin-pwa'
import { minimal2023Preset as preset } from '@vite-pwa/assets-generator/config'

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    vue(),
    vueDevTools(),
    VitePWA({
      devOptions: {
        enabled: true,
      },
      pwaAssets: {
        config: true,
      },
      workbox: {
        navigateFallbackDenylist: [/^\/api/]
      }
    }),
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
        strictExecutionOrder: true,
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
