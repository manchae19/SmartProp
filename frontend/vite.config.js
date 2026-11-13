import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import {approvedPublicAssets} from './build/publicAssets.mjs'
import {publicChatProxy, publicChatBoundary} from './build/chatProxy.mjs'

export default defineConfig(({mode}) => {
  const env=loadEnv(mode,process.cwd(),'')
  const apiTarget=process.env.SMARTPROP_DEV_API_TARGET||env.BE_API_TARGET||'http://127.0.0.1:8080'
  const aiTarget=env.AI_API_TARGET||'http://127.0.0.1:8000'
  const chatTarget=process.env.SMARTPROP_DEV_CHAT_TARGET||env.CHAT_API_TARGET||'http://127.0.0.1:8001'
  for(const target of [apiTarget,aiTarget])if(!new RegExp('^http://127[.]0[.]0[.]1:[0-9]{4,5}$').test(target))throw Error('Dev API proxy must target a loopback HTTP port')
  const proxy={
    '^/api/chat(?:\\?|$)':publicChatProxy(chatTarget),
    '/api/image-duplicates':{target:chatTarget,changeOrigin:false,proxyTimeout:60000,
      rewrite:value=>value.replace(/^\/api\/image-duplicates(?=\/|$)/,'/image-duplicates')},
    // Private local server-to-server header. Never VITE_* or exposed via define.
    '/api/v1/recommendations/research':{target:apiTarget,changeOrigin:false,proxyTimeout:180000,configure:proxy=>{
      proxy.on('proxyReq',request=>{
        request.removeHeader('X-SmartProp-Demo-Key')
        // This research projection never renews sessions or writes auth tables.
        // Existing JWT/session expiry is still enforced by Spring Security.
        request.removeHeader('X-Session-Activity')
        if(process.env.SMARTPROP_INTERNAL_DEMO_KEY)request.setHeader('X-SmartProp-Demo-Key',process.env.SMARTPROP_INTERNAL_DEMO_KEY)
      })
    }},
    '/api/ai':{target:aiTarget,changeOrigin:true,rewrite:value=>value.replace(/^\/api\/ai(?=\/|$)/,''),proxyTimeout:15000},
    '/api':{target:apiTarget,changeOrigin:false,proxyTimeout:15000},
  }
  return {
    optimizeDeps:{include:['leaflet']},
    plugins:[publicChatBoundary(),approvedPublicAssets(),react(),tailwindcss()],
    server:{host:'127.0.0.1',port:5173,strictPort:true,proxy},
    preview:{host:'127.0.0.1',port:4173,strictPort:true,proxy},
  }
})
