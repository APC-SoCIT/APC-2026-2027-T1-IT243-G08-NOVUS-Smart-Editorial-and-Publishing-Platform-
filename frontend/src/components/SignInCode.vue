<script setup>
/* Step two of signing in: the 6-digit code emailed after the password.
   Used by both sign-in pages; `theme` matches each page's look. */
import { ref, onMounted, onUnmounted, nextTick } from 'vue'
import { useAuthStore } from '../stores/auth'

const props = defineProps({
  challenge: { type: String, required: true },
  sentTo: { type: String, default: '' },
  theme: { type: String, default: 'staff' },   // staff | reader
})
const emit = defineEmits(['verified', 'restart'])

const auth = useAuthStore()
const code = ref('')
const error = ref('')
const info = ref('')
const busy = ref(false)
const dead = ref(false)          // expired or too many tries: sign in again
const wait = ref(30)             // seconds until another code may be sent
const input = ref(null)
let timer = null

function tick() {
  clearInterval(timer)
  timer = setInterval(() => { if (wait.value > 0) wait.value-- }, 1000)
}
onMounted(() => { tick(); nextTick(() => input.value?.focus()) })
onUnmounted(() => clearInterval(timer))

function onInput(e) {
  code.value = e.target.value.replace(/\D/g, '').slice(0, 6)
  e.target.value = code.value
  if (code.value.length === 6) verify()
}

async function verify() {
  if (busy.value || dead.value) return
  error.value = ''; info.value = ''
  if (code.value.length !== 6) { error.value = 'Enter the 6-digit code from the email.'; return }
  busy.value = true
  try {
    await auth.verifyCode(props.challenge, code.value)
    emit('verified')
  } catch (e) {
    const d = e.response?.data || {}
    if (d.code === 'wrong_code') {
      error.value = `That code is not right. ${d.attempts_left} ${d.attempts_left === 1 ? 'try' : 'tries'} left.`
      code.value = ''
      nextTick(() => input.value?.focus())
    } else if (e.response?.status === 429) {
      error.value = 'Too many attempts. Wait a moment before trying again.'
    } else {
      dead.value = true
      error.value = d.detail || 'This code has expired. Sign in again.'
    }
  } finally { busy.value = false }
}

async function resend() {
  if (wait.value > 0 || busy.value) return
  error.value = ''; info.value = ''
  try {
    const d = await auth.resendCode(props.challenge)
    info.value = `A new code is on its way to ${d.sent_to}.`
    code.value = ''
    wait.value = 30; tick()
  } catch (e) {
    const d = e.response?.data || {}
    if (d.code === 'wait') { wait.value = d.wait; tick(); return }
    if (d.code !== 'wait') dead.value = ['code_expired', 'too_many_sends'].includes(d.code)
    error.value = d.detail || 'Could not send another code.'
  }
}
</script>

<template>
  <div class="code" :class="theme">
    <p class="lead">
      We emailed a 6-digit code to <b>{{ sentTo }}</b>. Enter it to finish signing in.
    </p>

    <p v-if="info" class="info" role="status">{{ info }}</p>
    <p v-if="error" id="code-error" class="error" role="alert">{{ error }}</p>

    <template v-if="!dead">
      <label for="signin-code">Sign-in code</label>
      <input id="signin-code" ref="input" :value="code" type="text" inputmode="numeric"
             autocomplete="one-time-code" maxlength="6" pattern="[0-9]*" placeholder="••••••"
             :aria-describedby="error ? 'code-error' : undefined" :disabled="busy"
             @input="onInput" @keyup.enter="verify" />

      <button class="go" type="button" :disabled="busy || code.length !== 6" @click="verify">
        {{ busy ? 'Checking…' : 'Verify and sign in' }}
      </button>

      <p class="row">
        <button type="button" class="link" :disabled="wait > 0" @click="resend">
          {{ wait > 0 ? `Send a new code in ${wait}s` : 'Send a new code' }}
        </button>
      </p>
    </template>

    <p class="row">
      <button type="button" class="link" @click="emit('restart')">
        {{ dead ? 'Sign in again' : 'Use a different account' }}
      </button>
    </p>
    <p class="fine">The code expires in 10 minutes. Never share it with anyone, including BOSS staff.</p>
  </div>
</template>

<style scoped>
.code { text-align: left; }
.lead { margin: 0 0 18px; font-size: 14.5px; line-height: 1.6; }
label { display: block; margin: 0 0 7px; font-size: 11.5px; font-weight: 700;
        letter-spacing: .08em; text-transform: uppercase; }
input { box-sizing: border-box; width: 100%; height: 56px; margin-bottom: 16px; padding: 0 16px;
        border-radius: 10px; font: inherit; font-size: 26px; font-weight: 700;
        letter-spacing: .5em; text-align: center; font-variant-numeric: tabular-nums; }
input:focus { outline: none; }
.go { box-sizing: border-box; width: 100%; height: 48px; border: 0; border-radius: 10px;
      font: inherit; font-size: 15px; font-weight: 600; cursor: pointer; }
.go:disabled { opacity: .55; cursor: not-allowed; }
.row { margin: 14px 0 0; text-align: center; }
.link { background: none; border: 0; padding: 4px; cursor: pointer; font: inherit;
        font-size: 13.5px; font-weight: 600; text-decoration: underline; }
.link:disabled { cursor: default; text-decoration: none; opacity: .7; }
.fine { margin: 18px 0 0; font-size: 12.5px; line-height: 1.5; text-align: center; }
.error, .info { margin: 0 0 16px; padding: 10px 12px; border-radius: 8px; font-size: 13.5px; }

/* Editorial workspace */
.staff { color: var(--nv-text, #0F1A33); }
.staff .lead, .staff .fine { color: var(--nv-text-muted, #56627A); }
.staff .lead b { color: var(--nv-text, #0F1A33); }
.staff label { color: var(--nv-text, #3C4A66); }
.staff input { border: 1px solid var(--nv-line, #D5DBE7); background: var(--nv-bg, #F8FAFD);
               color: var(--nv-text, #0F1A33); }
.staff input:focus { border-color: #3D5BA9; box-shadow: 0 0 0 4px rgba(61, 91, 169, .16); }
.staff .go { background: #0F1A33; color: #fff; }
.staff .link { color: #3D5BA9; }
.staff .error { background: var(--bad-bg, #FDECEC); color: var(--bad, #B42318); }
.staff .info { background: #e8f6ee; color: #1c6b45; }

/* Reader magazine */
.reader { color: var(--boss-text); }
.reader .lead, .reader .fine { color: var(--boss-text-muted); }
.reader .lead b { color: var(--boss-text); }
.reader label { color: var(--boss-text-muted); font-weight: 400; letter-spacing: var(--track-caps); }
.reader input { border: 1px solid var(--boss-line); background: var(--boss-surface-2);
                color: var(--boss-text); border-radius: var(--r-sm); }
.reader input:focus { border-color: var(--boss-gold); }
.reader .go { background: var(--boss-gold); color: var(--boss-bg); border-radius: var(--r-sm);
              font-weight: 700; text-transform: uppercase; letter-spacing: var(--track-caps);
              font-size: var(--t-sm); }
.reader .link { color: var(--boss-gold); }
.reader .error { background: rgba(158,47,47,.14); border: 1px solid rgba(158,47,47,.4); color: #e09a9a; }
.reader .info { background: rgba(47,158,96,.14); border: 1px solid rgba(47,158,96,.4); color: #8fd4ac; }
</style>
