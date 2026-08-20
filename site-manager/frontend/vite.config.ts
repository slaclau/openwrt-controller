import { fileURLToPath, URL } from 'node:url'

import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import vueDevTools from 'vite-plugin-vue-devtools'
import { VitePWA } from 'vite-plugin-pwa'
import { minimal2023Preset as preset } from '@vite-pwa/assets-generator/config'
import fs from 'fs';
import path from 'path';
import { execSync } from 'child_process';

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
    {
      name: 'generate-version-json',
      // The closeBundle hook runs right after Vite finishes writing files to the dist directory
      closeBundle() {
        const distDir = path.resolve(__dirname, 'dist');
        const filePath = path.join(distDir, 'version.json');
        
        // Customise the object below to include timestamp, git commits, etc.
        const versionData = {
            frontend_version: execSync(`git-semver ${path.resolve(__dirname)}`).toString().trim(),
            controller_frontend_version: execSync(`git-semver ${path.resolve(__dirname, "../../controller/frontend")}`).toString().trim(),
        }
        // Ensure the directory exists and write the file
        if (!fs.existsSync(distDir)){
            fs.mkdirSync(distDir, { recursive: true });
        }
        fs.writeFileSync(filePath, JSON.stringify(versionData, null, 2));
        console.log("versions", versionData)        
      }
    }
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
