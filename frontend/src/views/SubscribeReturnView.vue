<script setup>
/* UC-4.3 step 4: the reader is back from PayRex. This page only reads what
   PayRex's confirmation recorded; arriving here grants nothing. The
   confirmation usually lands within seconds, so the page waits for it. */
import { ref, onMounted, onUnmounted } from 'vue'
import { useRoute } from 'vue-router'
import api from '../services/api'
import BossShell from '../components/BossShell.vue'
import { useAuthStore } from '../stores/auth'

const route = useRoute()
const auth = useAuthStore()
const state = ref('waiting')   // waiting | paid | failed | slow
const until = ref('')
let timer = null
let tries = 0

async function check() {
  tries += 1
  try {
    const { data } = await api.get(`/payments/checkout/${encodeURIComponent(route.query.ref || '')}/`)
    if (data.status === 'paid') {
      state.value = 'paid'
      until.value = new Date(data.access_until).toLocaleDateString('en-PH',
        { year: 'numeric', month: 'long', day: 'numeric' })
      auth.fetchUser()
      return
    }
    if (data.status === 'failed') { state.value = 'failed'; return }
  } catch { /* keep waiting; a blip should not read as a failure */ }
  if (tries >= 30) { state.value = 'slow'; return }
  timer = setTimeout(check, 2000)
}

onMounted(() => { document.title = 'Subscription — BOSS Magazine PH'; check() })
onUnmounted(() => clearTimeout(timer))
</script>

<template>
  <BossShell>
    <section class="wrap" aria-live="polite">
      <template v-if="state === 'waiting'">
        <p class="eyebrow">One moment</p>
        <h1>Confirming your payment…</h1>
        <p class="sub">PayRex is telling us about your payment. This usually takes a few seconds.</p>
      </template>

      <template v-else-if="state === 'paid'">
        <p class="eyebrow">Welcome</p>
        <h1>You are now a subscriber</h1>
        <p class="sub">Everything is open to you until {{ until }}. A receipt is on its way to your email.</p>
        <router-link to="/issues" class="cta">Read the magazines</router-link>
      </template>

      <template v-else-if="state === 'failed'">
        <p class="eyebrow">Not completed</p>
        <h1>The payment did not go through</h1>
        <p class="sub">Nothing was granted. You can try again with the same or another payment method.</p>
        <router-link to="/subscribe" class="cta">Try again</router-link>
      </template>

      <template v-else>
        <p class="eyebrow">Still confirming</p>
        <h1>This is taking longer than usual</h1>
        <p class="sub">
          If you paid, your subscription starts as soon as PayRex confirms it, and you
          will get a notice. There is no need to pay again.
        </p>
        <router-link to="/read" class="cta">Back to reading</router-link>
      </template>
    </section>
  </BossShell>
</template>

<style scoped>
.wrap { max-width: 640px; margin: 0 auto; padding: var(--s-10, 96px) var(--s-7);
        text-align: center; font-family: var(--font-ui); min-height: 50vh; }
.eyebrow { font-size: var(--t-xs); letter-spacing: var(--track-caps); text-transform: uppercase;
           color: var(--boss-gold); margin: 0 0 var(--s-4); }
h1 { font-family: var(--font-serif); font-size: var(--t-3xl); font-weight: 400;
     margin: 0 0 var(--s-4); color: var(--boss-text); line-height: var(--lh-tight); }
.sub { color: var(--boss-text-muted); font-size: var(--t-md); line-height: var(--lh-body);
       margin: 0 auto var(--s-6); max-width: 46ch; }
.cta { display: inline-block; background: var(--boss-gold); color: var(--boss-bg);
       padding: var(--s-4) var(--s-7); font-size: var(--t-sm); font-weight: 700;
       letter-spacing: var(--track-caps); text-transform: uppercase; text-decoration: none; }
.cta:hover { background: var(--boss-gold-bright); }
</style>
