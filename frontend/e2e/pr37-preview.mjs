// Builds the fixture-only entry with the real Vite config, then serves it
// without the development API proxies. Normal production dist is separate.
import { mkdirSync, mkdtempSync, writeFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { build, preview } from 'vite'

const evidence = resolve('../.smartprop')
mkdirSync(evidence, { recursive: true })
const outDir = mkdtempSync(resolve(evidence, 'pr37-fixture-dist-'))
await build({
  plugins: [{
    name: 'pr37-synthetic-session-entry',
    transformIndexHtml: {
      order: 'pre',
      handler: html => html.replace('/src/app/main.jsx', '/e2e/pr37-session-entry.js'),
    },
  }],
  build: { outDir },
})
const server = await preview({
  configFile: false,
  build: { outDir },
  preview: { host: '127.0.0.1', port: 0 },
})
const address = server.httpServer.address()
const url = `http://127.0.0.1:${address.port}`
writeFileSync(resolve(evidence, 'pr37-browser-url.txt'), url)
console.log(url)
