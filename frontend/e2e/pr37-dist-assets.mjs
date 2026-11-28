import assert from 'node:assert/strict'
import { createHash } from 'node:crypto'
import { existsSync, readFileSync, readdirSync, statSync } from 'node:fs'
import { basename, join } from 'node:path'
import { publicFiles } from '../build/publicAssets.mjs'

const digest = path => createHash('sha256').update(readFileSync(path)).digest('hex')
const dist = process.argv[2] || 'dist'
const withheld = ['cam-le', 'hai-chau', 'lien-chieu', 'ngu-hanh-son', 'son-tra'].map(name => name + '.webp')
const sizeAndHashes = new Map()
for (const name of withheld) {
  const original = join('public/media/areas', name)
  const size = statSync(original).size
  const hashes = sizeAndHashes.get(size) || []
  hashes.push(digest(original))
  sizeAndHashes.set(size, hashes)
}
assert.ok(existsSync(join(dist, 'index.html')), 'Expected a built production entry')
const files = readdirSync(dist, { recursive: true, withFileTypes: true }).filter(file => file.isFile())
for (const file of files) {
  const path = join(file.parentPath, file.name)
  assert.ok(!withheld.includes(basename(path)), 'Unapproved district image name shipped: ' + file.name)
  const hashes = sizeAndHashes.get(statSync(path).size)
  if (hashes) assert.ok(!hashes.includes(digest(path)), 'Unapproved district image bytes shipped: ' + file.name)
  if (/\.(css|html|js)$/.test(file.name)) {
    const content = readFileSync(path, 'utf8')
    assert.doesNotMatch(content, /\/media\/areas\//)
    assert.doesNotMatch(content, /window\.pr37Fixture|fixture-only-value/)
    for (const match of content.matchAll(/\/(?:images|media)\/[\w/.-]+\.(?:avif|jpe?g|png|svg|webp)/g)) {
      assert.ok(existsSync(join(dist, match[0].slice(1))), 'Bundled asset reference not emitted: ' + match[0])
    }
  }
}
for (const name of publicFiles) {
  assert.equal(digest(join(dist, name)), digest(join('public', name)), 'Approved asset differs: ' + name)
}
for (const metadata of ['credits.json', 'editorial-provenance.json']) {
  const provenance = JSON.parse(readFileSync(join(dist, 'images/news', metadata), 'utf8'))
  assert.ok(Object.keys(provenance).length > 0, 'Missing News provenance: ' + metadata)
}
console.log(`PASS ${withheld.length} withheld district images absent by name and SHA-256, ${publicFiles.length} approved assets byte-identical. Examined ${files.length} dist files, static references and News provenance.`)
