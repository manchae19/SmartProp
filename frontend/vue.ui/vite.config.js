import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import tailwindcss from '@tailwindcss/vite'
import {approvedPublicAssets} from './build/publicAssets.mjs'

export default defineConfig({
  plugins: [
    approvedPublicAssets(),
    // Root URLs reference runtime public assets; absent optional background video
    // must not become unresolved JavaScript imports during the production build.
    vue({ template: { transformAssetUrls: { includeAbsolute: false } } }),
    tailwindcss(),
  ],
})
