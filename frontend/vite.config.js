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
  // YOLOv8 object detection runs as its own service so it can be restarted
  // without touching duplicate scanning (18001) or RAG chat (8001).
  const visionTarget=process.env.SMARTPROP_DEV_VISION_TARGET||env.VISION_API_TARGET||'http://127.0.0.1:18002'
  // Internal loopback mentor demo key (never VITE_*, never exposed to browser bundle).
  const internalDemoKey=(process.env.SMARTPROP_INTERNAL_DEMO_KEY||process.env.RAG_DEMO_KEY||env.SMARTPROP_INTERNAL_DEMO_KEY||env.RAG_DEMO_KEY||'').trim()
  const validDemoKey=internalDemoKey.length>=16?internalDemoKey:''
  for(const target of [apiTarget,aiTarget,visionTarget])if(!new RegExp('^http://127[.]0[.]0[.]1:[0-9]{4,5}$').test(target))throw Error('Dev API proxy must target a loopback HTTP port')
  const proxy={
    '^/api/chat(?:/health)?(?:\\?|$)':publicChatProxy(chatTarget,{demoKey:validDemoKey}),
    '/api/image-duplicates':{target:chatTarget,changeOrigin:false,proxyTimeout:60000,
      rewrite:value=>value.replace(/^\/api\/image-duplicates(?=\/|$)/,'/image-duplicates')},
    '/api/image-analysis':{target:visionTarget,changeOrigin:false,proxyTimeout:60000,
      rewrite:value=>value.replace(/^\/api\/image-analysis(?=\/|$)/,'/image-analysis')},
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
    // Hòa Xuân land demo map/detail routes live on the chat service (loopback mentor demo only).
    '/api/land':{target:chatTarget,changeOrigin:false,proxyTimeout:30000,
      rewrite:value=>value.replace(/^\/api\/land(?=\/|$)/,'/land'),
      configure:proxy=>{
        proxy.on('proxyReq',request=>{
          for(const name of ['Cookie','X-SmartProp-Demo-Key','Forwarded','X-Forwarded-For'])request.removeHeader(name)
          if(validDemoKey)request.setHeader('X-SmartProp-Demo-Key',validDemoKey)
        })
      }},
    '/api/ai':{target:aiTarget,changeOrigin:true,rewrite:value=>value.replace(/^\/api\/ai(?=\/|$)/,''),proxyTimeout:15000},
    '/api':{target:apiTarget,changeOrigin:false,proxyTimeout:15000},
  }
  return {
    optimizeDeps:{include:['leaflet']},
    plugins:[publicChatBoundary({demoKey:validDemoKey}),approvedPublicAssets(),react(),tailwindcss()],
    server:{host:'127.0.0.1',port:Number(process.env.SMARTPROP_DEV_PORT||5173),strictPort:true,proxy},
    preview:{host:'127.0.0.1',port:4173,strictPort:true,proxy},
  }
})
