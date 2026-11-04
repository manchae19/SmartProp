import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'
import tailwindcss from '@tailwindcss/vite'
import {approvedPublicAssets} from './build/publicAssets.mjs'

export default defineConfig(({mode}) => {
  const env=loadEnv(mode,process.cwd(),'')
  const apiTarget=process.env.SMARTPROP_DEV_API_TARGET||env.BE_API_TARGET||'http://127.0.0.1:8080'
  const aiTarget=env.AI_API_TARGET||'http://127.0.0.1:8000'
  for(const target of [apiTarget,aiTarget])if(!new RegExp('^http://127[.]0[.]0[.]1:[0-9]{4,5}$').test(target))throw Error('Dev API proxy must target a loopback HTTP port')
  const proxy={
    '/api/ai':{target:aiTarget,changeOrigin:true,rewrite:value=>value.replace(/^\/api\/ai(?=\/|$)/,''),proxyTimeout:15000},
    '/api':{target:apiTarget,changeOrigin:false,proxyTimeout:15000},
  }
  return {
    plugins:[approvedPublicAssets(),vue({template:{transformAssetUrls:{includeAbsolute:false}}}),tailwindcss()],
    server:{host:'127.0.0.1',port:5173,strictPort:true,proxy},
    preview:{host:'127.0.0.1',port:4173,strictPort:true,proxy},
  }
})
