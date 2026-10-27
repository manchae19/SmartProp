import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import tailwindcss from '@tailwindcss/vite'
import {approvedPublicAssets} from './build/publicAssets.mjs'

const apiTarget=process.env.SMARTPROP_DEV_API_TARGET||'http://127.0.0.1:8080'
if(!/^http:\/\/127\.0\.0\.1:[0-9]{4,5}$/.test(apiTarget))throw Error('Dev API proxy must target a loopback HTTP port')
export default defineConfig({
  server:{proxy:{'/api':{target:apiTarget,changeOrigin:false}}},
  plugins: [
    approvedPublicAssets(),
    // Root URLs reference runtime public assets; absent optional background video
    // must not become unresolved JavaScript imports during the production build.
    vue({ template: { transformAssetUrls: { includeAbsolute: false } } }),
    tailwindcss(),
  ],
})
