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

/* Page-turn animation is a preference, not a default anyone should be stuck
   with. A page curl is pleasant the first few times and tiresome by the
   twentieth, so the choice persists and the reader keeps it.

   'off' also serves anyone who has asked their system to reduce motion —
   checked below so the preference is honoured without them setting it. */
const FLIP_KEY = 'boss.flip-style'
const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches
const flipStyle = ref(
  reduced ? 'off' : (localStorage.getItem(FLIP_KEY) || 'subtle'))
const settingsOpen = ref(false)

const FLIP_OPTIONS = [
  { key: 'off', label: 'None', hint: 'Pages change instantly' },
  { key: 'subtle', label: 'Subtle', hint: 'A slight lift as the page turns' },
  { key: 'page', label: 'Page turn', hint: 'The page swings across like paper' },
]

function setFlip(v) {
  flipStyle.value = v
  localStorage.setItem(FLIP_KEY, v)
  settingsOpen.value = false
}

let renderTask = null

async function render() {
  if (!doc || !canvas.value) return
  renderTask?.cancel?.()

  const p = await doc.getPage(page.value)
  const el = canvas.value
  const ctx = el.getContext('2d')

  // Fit the page to the viewport, then apply the reader's zoom on top.
  const base = p.getViewport({ scale: 1 })
  const stage = el.closest('.stage')
  const availH = (stage?.clientHeight || window.innerHeight) - 48
  const availW = (stage?.clientWidth || window.innerWidth) - 140
  // Fit to whichever dimension binds first, so a portrait page fills the
  // height and a landscape spread fills the width.
  const fit = Math.min(availH / base.height, availW / base.width)
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
  const ms = flipStyle.value === 'page' ? 520
           : flipStyle.value === 'subtle' ? 280 : 0
  setTimeout(() => (turning.value = null), ms)
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
        <div class="setwrap">
          <button class="cog" :aria-expanded="settingsOpen"
                  aria-label="Reading settings"
                  @click="settingsOpen = !settingsOpen">Aa</button>
          <div v-if="settingsOpen" class="setmenu" role="menu">
            <p class="sethead">Page turn</p>
            <button v-for="o in FLIP_OPTIONS" :key="o.key" role="menuitemradio"
                    :aria-checked="flipStyle === o.key"
                    :class="{ on: flipStyle === o.key }"
                    @click="setFlip(o.key)">
              <b>{{ o.label }}</b>
              <span>{{ o.hint }}</span>
            </button>
          </div>
        </div>

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

        <div class="sheet" :class="[turning, `flip-${flipStyle}`]">
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
.sheet { box-shadow: 0 24px 70px rgba(0,0,0,.75); background: #fff;
         border-radius: 2px;
         transform-origin: center left;
         transition: transform var(--dur-base) var(--ease-out),
                     opacity var(--dur-base) var(--ease-out); }
/* Three intensities. The transform origin sits on the spine so the page
   pivots where a real one would, rather than rotating about its centre. */
.sheet.flip-off.next, .sheet.flip-off.prev { animation: none; }

.sheet.flip-subtle.next { animation: liftNext 280ms var(--ease-out); }
.sheet.flip-subtle.prev { animation: liftPrev 280ms var(--ease-out); }
@keyframes liftNext {
  0%   { transform: perspective(1600px) rotateY(0); opacity: 1; }
  45%  { transform: perspective(1600px) rotateY(-9deg); opacity: .85; }
  100% { transform: perspective(1600px) rotateY(0); opacity: 1; }
}
@keyframes liftPrev {
  0%   { transform: perspective(1600px) rotateY(0); opacity: 1; }
  45%  { transform: perspective(1600px) rotateY(9deg); opacity: .85; }
  100% { transform: perspective(1600px) rotateY(0); opacity: 1; }
}

.sheet.flip-page { transform-origin: left center; }
.sheet.flip-page.next { animation: turnNext 520ms cubic-bezier(.36,.1,.3,1); }
.sheet.flip-page.prev { animation: turnPrev 520ms cubic-bezier(.36,.1,.3,1); }
@keyframes turnNext {
  0%   { transform: perspective(1800px) rotateY(0); filter: brightness(1); }
  50%  { transform: perspective(1800px) rotateY(-72deg); filter: brightness(.72); }
  51%  { transform: perspective(1800px) rotateY(72deg); filter: brightness(.72); }
  100% { transform: perspective(1800px) rotateY(0); filter: brightness(1); }
}
@keyframes turnPrev {
  0%   { transform: perspective(1800px) rotateY(0); filter: brightness(1); }
  50%  { transform: perspective(1800px) rotateY(72deg); filter: brightness(.72); }
  51%  { transform: perspective(1800px) rotateY(-72deg); filter: brightness(.72); }
  100% { transform: perspective(1800px) rotateY(0); filter: brightness(1); }
}

.setwrap { position: relative; }
.cog { background: transparent; border: 1px solid var(--boss-line);
       color: var(--boss-text-muted); width: 32px; height: 32px;
       border-radius: var(--r-sm); font-size: 13px; font-weight: 600;
       cursor: pointer; font-family: var(--font-serif); }
.cog:hover { border-color: var(--boss-gold); color: var(--boss-gold); }
.setmenu { position: absolute; right: 0; top: 40px; z-index: 10;
           background: var(--boss-surface); border: 1px solid var(--boss-line);
           border-radius: var(--r-md); padding: 6px; min-width: 210px;
           box-shadow: 0 12px 40px rgba(0,0,0,.6); }
.sethead { margin: 6px 10px 8px; font-size: 10px;
           letter-spacing: var(--track-caps); text-transform: uppercase;
           color: var(--boss-text-faint); }
.setmenu button { display: block; width: 100%; text-align: left;
                  background: none; border: 0; padding: 8px 10px;
                  border-radius: var(--r-sm); cursor: pointer;
                  font-family: var(--font-ui); }
.setmenu button:hover { background: var(--boss-surface-2); }
.setmenu button.on b { color: var(--boss-gold); }
.setmenu b { display: block; font-size: 13px; color: var(--boss-text);
             font-weight: 500; }
.setmenu span { font-size: 11px; color: var(--boss-text-faint); }

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
