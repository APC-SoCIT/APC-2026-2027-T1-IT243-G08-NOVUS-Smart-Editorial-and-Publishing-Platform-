<script setup>
import { ref, watch, computed, nextTick, onUnmounted } from 'vue'

const props = defineProps({
  open: { type: Boolean, default: false },
  title: { type: String, default: 'Are you sure?' },
  message: { type: String, default: '' },
  confirmLabel: { type: String, default: 'Confirm' },
  tone: { type: String, default: 'primary' },   // primary | warn | danger
  busy: { type: Boolean, default: false },
  // Consequences the user should read before agreeing.
  points: { type: Array, default: () => [] },
  // When set, the user must type this exact word to proceed. Reserved for
  // irreversible actions such as publishing an issue.
  requireText: { type: String, default: '' },
})
const emit = defineEmits(['confirm', 'cancel'])

const typed = ref('')
const box = ref(null)
let lastFocused = null

/* A modal must contain keyboard focus. Without this, Tab walks into the page
   behind the dialog, which is invisible to a sighted user and confusing to
   everyone else. Escape closes, and focus returns where it came from. */
function onKeydown(e) {
  if (!props.open) return

  if (e.key === 'Escape') {
    e.preventDefault()
    emit('cancel')
    return
  }
  if (e.key !== 'Tab' || !box.value) return

  const focusable = box.value.querySelectorAll(
    'button:not([disabled]), input:not([disabled]), a[href], [tabindex]:not([tabindex="-1"])')
  if (!focusable.length) return

  const first = focusable[0]
  const last = focusable[focusable.length - 1]

  if (e.shiftKey && document.activeElement === first) {
    e.preventDefault(); last.focus()
  } else if (!e.shiftKey && document.activeElement === last) {
    e.preventDefault(); first.focus()
  }
}

watch(() => props.open, async (o) => {
  if (o) {
    typed.value = ''
    lastFocused = document.activeElement
    document.addEventListener('keydown', onKeydown)
    document.body.style.overflow = 'hidden'
    await nextTick()
    const target = box.value?.querySelector('input, button')
    target?.focus()
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

const canConfirm = computed(() =>
  !props.busy && (!props.requireText || typed.value.trim() === props.requireText))
</script>

<template>
  <transition name="fade">
    <div v-if="open" class="scrim" @click.self="emit('cancel')">
      <div ref="box" class="box focus-trap" :class="tone"
           role="alertdialog" aria-modal="true"
           :aria-labelledby="`dlg-title`" :aria-describedby="`dlg-msg`">
        <h3 id="dlg-title">{{ title }}</h3>
        <p v-if="message" id="dlg-msg" class="msg">{{ message }}</p>

        <ul v-if="points.length" class="points">
          <li v-for="(p, i) in points" :key="i">{{ p }}</li>
        </ul>

        <div v-if="requireText" class="typed">
          <label for="dlg-confirm-text">
            Type <b>{{ requireText }}</b> to confirm
          </label>
          <input id="dlg-confirm-text" v-model="typed" :placeholder="requireText"
                 autocomplete="off"
                 @keyup.enter="canConfirm && emit('confirm')" />
        </div>

        <div class="actions">
          <button class="cancel" :disabled="busy" @click="emit('cancel')">Cancel</button>
          <button class="go" :disabled="!canConfirm" @click="emit('confirm')">
            {{ busy ? 'Working…' : confirmLabel }}
          </button>
        </div>
      </div>
    </div>
  </transition>
</template>

<style scoped>
.scrim { position: fixed; inset: 0; background: rgba(13,21,38,.6);
         backdrop-filter: blur(2px); display: flex; align-items: center;
         justify-content: center; z-index: 90; font-family: system-ui; }
.box { background: #fff; border-radius: 12px; padding: 26px 28px; width: 420px;
       max-width: calc(100vw - 40px); box-shadow: 0 18px 50px rgba(0,0,0,.26);
       border-top: 4px solid #1a2744; }
.box.warn { border-top-color: #b5651d; }
.box.danger { border-top-color: #b53b3b; }
h3 { margin: 0 0 9px; font-size: 17px; }
.msg { margin: 0; font-size: 14px; line-height: 1.6; color: #556; }
.points { margin: 14px 0 0; padding-left: 20px; }
.points li { font-size: 13px; line-height: 1.65; color: #667; }
.typed { margin-top: 18px; }
.typed label { display: block; font-size: 12px; color: #778; margin-bottom: 6px; }
.typed input { width: 100%; padding: 10px; border: 1px solid #ccd; border-radius: 6px;
               font-size: 14px; font-family: inherit; }
.actions { display: flex; gap: 10px; margin-top: 24px; }
.actions button { flex: 1; padding: 11px; border-radius: 7px; font-size: 14px;
                  cursor: pointer; font-weight: 600; }
.cancel { border: 1px solid #ccd; background: #fff; color: #445; }
.go { border: 0; background: #1a2744; color: #fff; }
.box.warn .go { background: #b5651d; }
.box.danger .go { background: #b53b3b; }
.actions button:disabled { opacity: .45; cursor: not-allowed; }
.fade-enter-active, .fade-leave-active { transition: opacity .2s; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
</style>
