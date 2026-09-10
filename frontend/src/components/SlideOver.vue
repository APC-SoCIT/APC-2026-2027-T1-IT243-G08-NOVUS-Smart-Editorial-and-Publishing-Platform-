<script setup>
import { watch, ref, nextTick, onUnmounted } from 'vue'

const props = defineProps({
  open: { type: Boolean, default: false },
  title: { type: String, required: true },
  subtitle: { type: String, default: '' },
})
const emit = defineEmits(['close'])

const panel = ref(null)
let lastFocused = null

/* Same focus discipline as the dialog: contain Tab, close on Escape, and
   return focus to whatever opened it. A panel that leaks focus to the page
   behind is unusable without a mouse. */
function onKeydown(e) {
  if (!props.open) return
  if (e.key === 'Escape') { emit('close'); return }
  if (e.key !== 'Tab' || !panel.value) return

  const f = panel.value.querySelectorAll(
    'button:not([disabled]), input:not([disabled]), select, textarea, a[href]')
  if (!f.length) return
  const first = f[0], last = f[f.length - 1]

  if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus() }
  else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus() }
}

watch(() => props.open, async (o) => {
  if (o) {
    lastFocused = document.activeElement
    document.addEventListener('keydown', onKeydown)
    document.body.style.overflow = 'hidden'
    await nextTick()
    panel.value?.querySelector('input, select, textarea, button')?.focus()
  } else {
    document.removeEventListener('keydown', onKeydown)
    document.body.style.overflow = ''
    lastFocused?.focus?.()
  }
})

onUnmounted(() => {
  document.removeEventListener('keydown', onKeydown)
  document.body.style.overflow = ''
})
</script>

<template>
  <teleport to="body">
    <transition name="fade">
      <div v-if="open" class="scrim" @click.self="emit('close')"></div>
    </transition>

    <transition name="slide">
      <aside v-if="open" ref="panel" class="panel" role="dialog"
             aria-modal="true" aria-labelledby="so-title">
        <header>
          <div>
            <h2 id="so-title">{{ title }}</h2>
            <p v-if="subtitle">{{ subtitle }}</p>
          </div>
          <button class="x" aria-label="Close panel" @click="emit('close')">
            <span aria-hidden="true">×</span>
          </button>
        </header>
        <div class="body"><slot /></div>
      </aside>
    </transition>
  </teleport>
</template>

<style scoped>
.scrim { position: fixed; inset: 0; background: rgba(13,21,38,.45);
         backdrop-filter: blur(2px); z-index: 70; }
.panel { position: fixed; top: 0; right: 0; bottom: 0; width: 480px;
         max-width: 92vw; background: var(--nv-surface); z-index: 71;
         display: flex; flex-direction: column;
         box-shadow: -8px 0 40px rgba(13,21,38,.18); }

header { display: flex; justify-content: space-between; align-items: flex-start;
         gap: var(--s-4); padding: var(--s-5); border-bottom: 1px solid var(--nv-line); }
h2 { font-size: 18px; margin: 0; color: var(--nv-text); }
header p { font-size: 14px; color: var(--nv-text-muted); margin: 4px 0 0;
           line-height: 1.5; }
.x { background: none; border: 0; font-size: 26px; line-height: 1;
     color: var(--nv-text-muted); cursor: pointer; padding: 0 6px;
     border-radius: var(--r-sm); }
.x:hover { color: var(--nv-text); background: var(--nv-bg); }

.body { flex: 1; overflow-y: auto; padding: var(--s-5); }

.fade-enter-active, .fade-leave-active { transition: opacity var(--dur-base); }
.fade-enter-from, .fade-leave-to { opacity: 0; }
.slide-enter-active, .slide-leave-active {
  transition: transform var(--dur-base) var(--ease-out); }
.slide-enter-from, .slide-leave-to { transform: translateX(100%); }
</style>
