<script setup>
import { ref, onMounted, onUnmounted, watch, nextTick } from 'vue'
import * as pdfjsLib from 'pdfjs-dist'
import workerUrl from 'pdfjs-dist/build/pdf.worker.min.mjs?url'

pdfjsLib.GlobalWorkerOptions.workerSrc = workerUrl

const props = defineProps({
  src: { type: String, required: true },
  title: { type: String, default: '' },
})
const emit = defineEmits(['close'])

const canvas = ref(null)
// Not a ref: pdf.js documents use private class fields, and Vue's Proxy
// wrapper is not an instance of the class, so reading them throws. Nothing
// in the template depends on the document itself — only on pages and page,
// which are refs — so it does not need to be reactive.
let doc = null
const page = ref(1)
const pages = ref(0)
const loading = ref(true)
const error = ref('')
const zoom = ref(1)
const turning = ref(null)   // 'next' | 'prev'

let renderTask = null

async function render() {
  if (!doc || !canvas.value) return
  renderTask?.cancel?.()

  const p = await doc.getPage(page.value)
  const el = canvas.value
  const ctx = el.getContext('2d')

  // Fit the page to the viewport, then apply the reader's zoom on top.
  const base = p.getViewport({ scale: 1 })
  const avail = el.parentElement.clientHeight - 32
  const fit = avail / base.height
  const dpr = window.devicePixelRatio || 1
  const viewport = p.getViewport({ scale: fit * zoom.value })

  el.width = viewport.width * dpr
  el.height = viewport.height * dpr
  el.style.width = `${viewport.width}px`
  el.style.height = `${viewport.height}px`
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0)

  renderTask = p.render({ canvasContext: ctx, viewport })
  await renderTask.promise.catch(() => {})
}

async function turn(dir) {
  const next = page.value + dir
  if (next < 1 || next > pages.value) return
  turning.value = dir > 0 ? 'next' : 'prev'
  page.value = next
  await nextTick()
  await render()
  setTimeout(() => (turning.value = null), 260)
}

function onKey(e) {
  if (e.key === 'ArrowRight' || e.key === 'PageDown') { e.preventDefault(); turn(1) }
  if (e.key === 'ArrowLeft'  || e.key === 'PageUp')   { e.preventDefault(); turn(-1) }
  if (e.key === 'Home') { page.value = 1; render() }
  if (e.key === 'End')  { page.value = pages.value; render() }
  if (e.key === 'Escape') emit('close')
  if (e.key === '+' || e.key === '=') { zoom.value = Math.min(2.5, zoom.value + .2); render() }
  if (e.key === '-') { zoom.value = Math.max(.6, zoom.value - .2); render() }
}

onMounted(async () => {
  document.addEventListener('keydown', onKey)
  window.addEventListener('resize', render)
  try {
    // Newer pdf.js builds expect an options object rather than a bare string;
    // passing the URL positionally silently produces 'expected either data,
    // range, or url parameter'.
    doc = await pdfjsLib.getDocument({ url: props.src }).promise
    pages.value = doc.numPages
    loading.value = false
    await nextTick()
    await render()
  } catch (e) {
    // Log the real exception: a URL problem, a parse failure and a worker
    // loading error all reached the same generic message, which made every
    // one of them look identical from the outside.
    console.error('Flipbook failed to open:', e)
    error.value = 'This edition could not be opened in the reader.'
    loading.value = false
  }
})

onUnmounted(() => {
  document.removeEventListener('keydown', onKey)
  window.removeEventListener('resize', render)
  renderTask?.cancel?.()
  doc?.destroy?.()
})

watch(zoom, render)
</script>

<template>
  <div class="reader" role="dialog" aria-modal="true" :aria-label="`Reading ${title}`">
    <header>
      <span class="ttl">{{ title }}</span>

      <div class="tools">
        <button @click="zoom = Math.max(.6, zoom - .2)" aria-label="Zoom out">−</button>
        <span class="zoom">{{ Math.round(zoom * 100) }}%</span>
        <button @click="zoom = Math.min(2.5, zoom + .2)" aria-label="Zoom in">+</button>
        <a :href="src" download class="dl">Download</a>
        <button class="close" @click="emit('close')" aria-label="Close reader">×</button>
      </div>
    </header>

    <div class="stage">
      <p v-if="loading" class="state" role="status">Opening the edition…</p>
      <p v-else-if="error" class="state">{{ error }}</p>

      <template v-else>
        <button class="nav prev" :disabled="page <= 1"
                aria-label="Previous page" @click="turn(-1)">‹</button>

        <div class="sheet" :class="turning">
          <canvas ref="canvas" :aria-label="`Page ${page} of ${pages}`"></canvas>
        </div>

        <button class="nav next" :disabled="page >= pages"
                aria-label="Next page" @click="turn(1)">›</button>
      </template>
    </div>

    <footer v-if="!loading && !error">
      <input type="range" min="1" :max="pages" v-model.number="page"
             aria-label="Jump to page" @input="render" />
      <span class="count" role="status" aria-live="polite">
        Page {{ page }} of {{ pages }}
      </span>
      <span class="hint">Use ← → to turn pages</span>
    </footer>
  </div>
</template>

<style scoped>
.reader { position: fixed; inset: 0; z-index: 100; background: #0a0a0a;
          display: flex; flex-direction: column; font-family: var(--font-ui); }

header { display: flex; align-items: center; gap: var(--s-4);
         padding: var(--s-3) var(--s-5); border-bottom: 1px solid var(--boss-line); }
.ttl { flex: 1; font-family: var(--font-serif); font-size: var(--t-md);
       color: var(--boss-text); }
.tools { display: flex; align-items: center; gap: var(--s-2); }
.tools button { background: transparent; border: 1px solid var(--boss-line);
                color: var(--boss-text-muted); width: 32px; height: 32px;
                border-radius: var(--r-sm); font-size: 17px; cursor: pointer;
                transition: all var(--dur-fast) var(--ease-out); }
.tools button:hover { border-color: var(--boss-gold); color: var(--boss-gold); }
.zoom { font-size: var(--t-xs); color: var(--boss-text-faint); width: 44px;
        text-align: center; font-variant-numeric: tabular-nums; }
.dl { font-size: var(--t-xs); letter-spacing: var(--track-caps);
      text-transform: uppercase; color: var(--boss-gold);
      border: 1px solid var(--boss-gold-deep); padding: 8px var(--s-4);
      border-radius: var(--r-sm); margin-left: var(--s-2); }
.dl:hover { background: var(--boss-gold); color: #0a0a0a; }
.close { margin-left: var(--s-2); font-size: 22px !important; }

.stage { flex: 1; display: flex; align-items: center; justify-content: center;
         gap: var(--s-5); padding: var(--s-4); min-height: 0; }
.state { color: var(--boss-text-muted); }

/* The page lifts and tilts fractionally as it turns — enough to read as a
   page turn without the parody of a full 3D flip. */
.sheet { box-shadow: 0 20px 60px rgba(0,0,0,.7); background: #fff;
         transform-origin: center left;
         transition: transform var(--dur-base) var(--ease-out),
                     opacity var(--dur-base) var(--ease-out); }
.sheet.next { animation: turnNext 280ms var(--ease-out); }
.sheet.prev { animation: turnPrev 280ms var(--ease-out); }
@keyframes turnNext {
  0%   { transform: perspective(1400px) rotateY(0); opacity: 1; }
  45%  { transform: perspective(1400px) rotateY(-11deg); opacity: .82; }
  100% { transform: perspective(1400px) rotateY(0); opacity: 1; }
}
@keyframes turnPrev {
  0%   { transform: perspective(1400px) rotateY(0); opacity: 1; }
  45%  { transform: perspective(1400px) rotateY(11deg); opacity: .82; }
  100% { transform: perspective(1400px) rotateY(0); opacity: 1; }
}
canvas { display: block; }

.nav { background: transparent; border: 1px solid var(--boss-line);
       color: var(--boss-text-muted); width: 46px; height: 76px;
       border-radius: var(--r-sm); font-size: 28px; cursor: pointer;
       flex-shrink: 0; transition: all var(--dur-fast) var(--ease-out); }
.nav:hover:not(:disabled) { border-color: var(--boss-gold); color: var(--boss-gold); }
.nav:disabled { opacity: .25; cursor: not-allowed; }

footer { display: flex; align-items: center; gap: var(--s-5);
         padding: var(--s-4) var(--s-7); border-top: 1px solid var(--boss-line); }
input[type=range] { flex: 1; accent-color: var(--boss-gold); }
.count { font-size: var(--t-sm); color: var(--boss-text); white-space: nowrap;
         font-variant-numeric: tabular-nums; }
.hint { font-size: var(--t-xs); color: var(--boss-text-faint); white-space: nowrap; }

@media (max-width: 700px) {
  .nav { display: none; }
  .hint { display: none; }
  header { padding: var(--s-3); }
  .ttl { font-size: var(--t-sm); }
}
</style>
