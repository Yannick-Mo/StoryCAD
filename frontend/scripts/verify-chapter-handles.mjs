import { readFileSync } from 'node:fs'
import assert from 'node:assert/strict'

const chapterNodeSource = readFileSync(new URL('../src/pages/editor/views/plot/ChapterNode.tsx', import.meta.url), 'utf8')

const declaredHandles = new Set(
  Array.from(chapterNodeSource.matchAll(/id="([^"]+)"/g), match => match[1])
)

// These are the handle ids that getBestHandle can return for chapter-to-chapter edges.
const handlesUsedByAutoRouting = ['s-r', 't-l', 's-l', 't-r', 's-b', 't-t', 's-t', 't-b']

const missing = handlesUsedByAutoRouting.filter(handleId => !declaredHandles.has(handleId))

assert.deepEqual(
  missing,
  [],
  `ChapterNode is missing handles used by automatic edge routing: ${missing.join(', ')}`
)
