<script setup>
/* UC-4.3 Subscribe to BOSS Magazine, steps 1 and 2: pick a plan, then pay on
   PayRex's own checkout page. Nothing is granted here; access comes from
   PayRex's signed confirmation to the server. */
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import api from '../services/api'
import BossShell from '../components/BossShell.vue'
import { useAuthStore } from '../stores/auth'

const route = useRoute()
const auth = useAuthStore()

const plans = ref([])
const available = ref(true)
const chosen = ref('ANNUAL')
const busy = ref(false)
const error = ref('')
const cancelled = route.query.cancelled === '1'

const plan = computed(() => plans.value.find((p) => p.code === chosen.value))
const isStaff = computed(() => auth.role && auth.role !== 'READER')
const until = computed(() => {
  const p = auth.user?.reader_profile
  if (p?.tier !== 'SUBSCRIBER' || !p.subscription_renews_at) return null
  const d = new Date(p.subscription_renews_at)
  return d > new Date() ? d.toLocaleDateString('en-PH', { year: 'numeric', month: 'long', day: 'numeric' }) : null
})

onMounted(async () => {
  document.title = 'Subscribe — BOSS Magazine PH'
  if (auth.isAuthenticated && !auth.user) auth.fetchUser()
  const { data } = await api.get('/payments/plans/')
  plans.value = data.plans
  available.value = data.available
})

async function pay() {
  error.value = ''
  busy.value = true
  try {
    const { data } = await api.post('/payments/checkout/', { plan: chosen.value })
    window.location.assign(data.checkout_url)
  } catch (e) {
    error.value = e.response?.data?.detail || 'Payment could not be started. Try again in a moment.'
    busy.value = false
  }
}
</script>

<template>
  <BossShell>
    <header class="intro">
      <p class="eyebrow"><span>Subscribe</span><span class="rule" aria-hidden="true"></span></p>
      <h1>Read every story and every issue</h1>
      <p class="sub">Premium articles, every digital edition to read or download, and the full archive.</p>
    </header>

    <section class="wrap">
      <p v-if="cancelled" class="notice bad" role="alert">
        The payment was not completed, and you were not charged. You can try again,
        with the same or another payment method.
      </p>
      <p v-if="until" class="notice" role="status">
        You are subscribed until {{ until }}. Paying again adds the new period to the end.
      </p>

      <div class="plans" role="radiogroup" aria-label="Plans">
        <button v-for="p in plans" :key="p.code" type="button" class="plan"
                role="radio" :aria-checked="chosen === p.code"
                :class="{ on: chosen === p.code }" @click="chosen = p.code">
          <span v-if="p.note" class="best">Best value</span>
          <span class="name">{{ p.name }}</span>
          <span class="price">{{ p.price }}</span>
          <span class="per">{{ p.days }} days of access</span>
          <span v-if="p.note" class="note">{{ p.note }}</span>
        </button>
      </div>

      <div class="act">
        <p v-if="isStaff" class="hint">Staff accounts already have full access.</p>
        <router-link v-else-if="!auth.isAuthenticated" class="cta"
                     :to="{ path: '/login', query: { next: '/subscribe' } }">
          Sign in to subscribe
        </router-link>
        <button v-else class="cta" :disabled="busy || !plan || !available" @click="pay">
          {{ busy ? 'Opening checkout…' : `Continue to payment${plan ? ' · ' + plan.price : ''}` }}
        </button>
        <p v-if="!available" class="hint">Online payment is not set up yet.</p>
        <p v-if="error" class="notice bad" role="alert">{{ error }}</p>
      </div>

      <ul class="terms">
        <li>Pay with GCash, Maya, a card or QR Ph on PayRex's secure page. Your payment details never reach BOSS Magazine.</li>
        <li>Prepaid: nothing is charged automatically. We remind you before your access ends.</li>
        <li>Cancel any time; you keep access to the end of the period you paid for.
          See the <router-link to="/legal/refunds">Refund Policy</router-link>.</li>
      </ul>
    </section>
  </BossShell>
</template>

<style scoped>
.intro { max-width: 900px; margin: 0 auto; padding: var(--s-9) var(--s-7) var(--s-6);
         border-bottom: 1px solid var(--boss-line); }
.eyebrow { display: flex; align-items: center; gap: var(--s-4); font-family: var(--font-ui);
           font-size: var(--t-xs); letter-spacing: var(--track-caps); text-transform: uppercase;
           color: var(--boss-gold); margin: 0 0 var(--s-4); }
.rule { width: 50px; height: 1px; background: var(--boss-gold-deep); }
h1 { font-family: var(--font-serif); font-size: var(--t-3xl); font-weight: 400;
     margin: 0 0 var(--s-3); color: var(--boss-text); line-height: var(--lh-tight); }
.sub { color: var(--boss-text-muted); font-size: var(--t-md); margin: 0; font-family: var(--font-ui); }

.wrap { max-width: 900px; margin: 0 auto; padding: var(--s-7) var(--s-7) var(--s-9);
        font-family: var(--font-ui); }
.notice { border: 1px solid var(--boss-gold-deep); color: var(--boss-text);
          padding: var(--s-3) var(--s-4); font-size: var(--t-sm); margin: 0 0 var(--s-5);
          line-height: var(--lh-snug); }
.notice.bad { border-color: #8a3b32; background: rgba(138, 59, 50, .15); }

.plans { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
         gap: var(--s-5); margin-bottom: var(--s-6); }
.plan { position: relative; display: flex; flex-direction: column; align-items: flex-start;
        gap: var(--s-2); text-align: left; padding: var(--s-6); cursor: pointer;
        background: var(--boss-surface); border: 1px solid var(--boss-line);
        color: var(--boss-text); font-family: inherit;
        transition: border-color var(--dur-base) var(--ease-out); }
.plan:hover { border-color: var(--boss-gold-deep); }
.plan.on { border-color: var(--boss-gold); box-shadow: inset 0 0 0 1px var(--boss-gold); }
.best { position: absolute; top: var(--s-4); right: var(--s-4); font-size: var(--t-xs);
        letter-spacing: var(--track-caps); text-transform: uppercase; color: var(--boss-bg);
        background: var(--boss-gold); padding: 2px var(--s-2); }
.name { font-size: var(--t-xs); letter-spacing: var(--track-caps); text-transform: uppercase;
        color: var(--boss-gold); }
.price { font-family: var(--font-serif); font-size: var(--t-3xl); line-height: 1; }
.per { color: var(--boss-text-muted); font-size: var(--t-sm); }
.note { color: var(--boss-text-faint); font-size: var(--t-xs); }

.act { margin-bottom: var(--s-7); }
.cta { display: inline-block; border: 0; background: var(--boss-gold); color: var(--boss-bg);
       padding: var(--s-4) var(--s-7); font-size: var(--t-sm); font-weight: 700;
       letter-spacing: var(--track-caps); text-transform: uppercase; cursor: pointer;
       font-family: inherit; text-decoration: none; }
.cta:hover:not(:disabled) { background: var(--boss-gold-bright); }
.cta:disabled { opacity: .5; cursor: not-allowed; }
.hint { color: var(--boss-text-muted); font-size: var(--t-sm); margin: var(--s-3) 0 0; }

.terms { list-style: none; padding: var(--s-5) 0 0; margin: 0; border-top: 1px solid var(--boss-line); }
.terms li { position: relative; padding: var(--s-2) 0 var(--s-2) var(--s-5); color: var(--boss-text-muted);
            font-size: var(--t-sm); line-height: var(--lh-snug); }
.terms li::before { content: '\2713'; position: absolute; left: 0; color: var(--boss-gold); }
.terms a { color: var(--boss-gold); }
@media (max-width: 600px) {
  .intro, .wrap { padding-left: var(--s-5); padding-right: var(--s-5); }
}
</style>
