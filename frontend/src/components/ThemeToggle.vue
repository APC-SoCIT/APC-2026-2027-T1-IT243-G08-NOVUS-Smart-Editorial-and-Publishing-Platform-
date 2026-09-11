<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { useThemeStore } from '../stores/theme'

const theme = useThemeStore()
const open = ref(false)
const root = ref(null)

const OPTIONS = [
  { key: 'light',  label: 'Light',  icon: '☀' },
  { key: 'dark',   label: 'Dark',   icon: '☾' },
  { key: 'system', label: 'System', icon: '⌂' },
]

function pick(k) { theme.set(k); open.value = false }

function onDocClick(e) {
  if (open.value && root.value && !root.value.contains(e.target)) open.value = false
}
function onKey(e) { if (e.key === 'Escape') open.value = false }

onMounted(() => {
  document.addEventListener('click', onDocClick)
  document.addEventListener('keydown', onKey)
})
onUnmounted(() => {
  document.removeEventListener('click', onDocClick)
  document.removeEventListener('keydown', onKey)
})
</script>

<template>
  <div ref="root" class="wrap">
    <button class="btn" :aria-expanded="open" aria-haspopup="true"
            :aria-label="`Appearance: ${theme.preference}. Change it.`"
            @click="open = !open">
      <span aria-hidden="true">{{ theme.resolved === 'dark' ? '☾' : '☀' }}</span>
    </button>

    <div v-if="open" class="menu" role="menu">
      <button v-for="o in OPTIONS" :key="o.key" role="menuitemradio"
              :aria-checked="theme.preference === o.key"
              :class="{ on: theme.preference === o.key }"
              @click="pick(o.key)">
        <span class="ic" aria-hidden="true">{{ o.icon }}</span>
        {{ o.label }}
        <span v-if="theme.preference === o.key" class="tick" aria-hidden="true">✓</span>
      </button>
    </div>
  </div>
</template>

<style scoped>
.wrap { position: relative; }
.btn { width: 36px; height: 36px; border: 1px solid var(--nv-line-strong);
       background: var(--nv-surface); color: var(--nv-text-muted);
       border-radius: var(--r-sm); font-size: 15px; cursor: pointer;
       transition: border-color var(--dur-fast) var(--ease-out),
                   color var(--dur-fast) var(--ease-out); }
.btn:hover { border-color: var(--nv-text-faint); color: var(--nv-text); }

.menu { position: absolute; right: 0; top: calc(100% + 6px); z-index: 40;
        min-width: 160px; background: var(--nv-surface);
        border: 1px solid var(--nv-line); border-radius: var(--r-md);
        box-shadow: var(--shadow-md); padding: 4px; }
.menu button { display: flex; align-items: center; gap: 10px; width: 100%;
               background: none; border: 0; padding: 9px 11px;
               border-radius: var(--r-sm); font-size: 14px; cursor: pointer;
               color: var(--nv-text); font-family: inherit; text-align: left; }
.menu button:hover { background: var(--nv-bg); }
.menu button.on { color: var(--nv-accent); font-weight: 600; }
.ic { width: 16px; text-align: center; color: var(--nv-text-muted); }
.menu button.on .ic { color: var(--nv-accent); }
.tick { margin-left: auto; font-size: 12px; }
</style>
