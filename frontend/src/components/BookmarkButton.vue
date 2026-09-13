<script setup>
import { ref, watch } from 'vue'
import api from '../services/api'
import { useAuthStore } from '../stores/auth'

const props = defineProps({
  articleId: { type: [Number, String], required: true },
  saved: { type: Boolean, default: false },
  /* 'icon' for cards, 'full' for the article page where there is room
     for a label and the action is less obvious from context. */
  variant: { type: String, default: 'icon' },
})
const emit = defineEmits(['changed'])

const auth = useAuthStore()
const on = ref(props.saved)
const busy = ref(false)
const prompt = ref(false)

watch(() => props.saved, (v) => { on.value = v })

async function toggle() {
  if (!auth.isAuthenticated) {
    // Prompting is kinder than redirecting: a reader halfway through an
    // article should not lose their place to find out they need an account.
    prompt.value = true
    setTimeout(() => (prompt.value = false), 4000)
    return
  }
  if (busy.value) return

  // Optimistic: the round trip is short and the action is trivially
  // reversible, so waiting to redraw makes it feel slower than it is.
  const previous = on.value
  on.value = !previous
  busy.value = true
  try {
    const { data } = await api.post(`/content/bookmarks/${props.articleId}/toggle/`)
    on.value = data.saved
    emit('changed', data.saved)
  } catch {
    on.value = previous
  } finally { busy.value = false }
}
</script>

<template>
  <div class="wrap">
    <button :class="['bm', variant, { on }]"
            :aria-pressed="on"
            :aria-label="on ? 'Remove from saved articles' : 'Save this article'"
            :disabled="busy"
            @click.stop.prevent="toggle">
      <svg width="17" height="17" viewBox="0 0 24 24" aria-hidden="true"
           :fill="on ? 'currentColor' : 'none'" stroke="currentColor"
           stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
        <path d="M19 21l-7-5-7 5V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z" />
      </svg>
      <span v-if="variant === 'full'">{{ on ? 'Saved' : 'Save' }}</span>
    </button>

    <transition name="fade">
      <span v-if="prompt" class="hint" role="status">
        <router-link to="/login">Sign in</router-link> to save articles
      </span>
    </transition>
  </div>
</template>

<style scoped>
.wrap { position: relative; display: inline-flex; align-items: center; }

.bm { display: inline-flex; align-items: center; gap: 7px;
      background: transparent; border: 1px solid var(--boss-line);
      color: var(--boss-text-muted); cursor: pointer;
      border-radius: var(--r-sm); font-family: inherit;
      transition: color var(--dur-fast) var(--ease-out),
                  border-color var(--dur-fast) var(--ease-out); }
.bm:hover { color: var(--boss-gold); border-color: var(--boss-gold-deep); }
.bm.on { color: var(--boss-gold); border-color: var(--boss-gold-deep); }
.bm:disabled { opacity: .6; cursor: wait; }

.bm.icon { padding: 7px; }
.bm.full { padding: var(--s-2) var(--s-4); font-size: var(--t-xs);
           letter-spacing: var(--track-caps); text-transform: uppercase; }

.hint { position: absolute; left: calc(100% + 10px); white-space: nowrap;
        font-size: var(--t-xs); color: var(--boss-text-muted);
        background: var(--boss-surface); border: 1px solid var(--boss-line);
        padding: 6px 11px; border-radius: var(--r-sm); }
.hint a { color: var(--boss-gold); border-bottom: 1px solid var(--boss-gold-deep); }

.fade-enter-active, .fade-leave-active { transition: opacity var(--dur-base); }
.fade-enter-from, .fade-leave-to { opacity: 0; }
</style>
