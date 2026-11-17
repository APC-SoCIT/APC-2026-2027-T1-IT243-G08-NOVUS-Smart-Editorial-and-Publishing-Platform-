<script setup>
/* UC-4.4 Manage a Subscription: see the plan, the date access lasts to and
   how it was paid; renew; or cancel at the end of the paid period. */
import { ref, computed, onMounted } from 'vue'
import api from '../services/api'
import BossShell from '../components/BossShell.vue'
import { useAuthStore } from '../stores/auth'

const auth = useAuthStore()
const info = ref(null)
const confirming = ref(false)
const busy = ref(false)
const message = ref('')
const error = ref('')

const sub = computed(() => info.value?.subscription)
const fmt = (d) => d ? new Date(d).toLocaleDateString('en-PH',
  { year: 'numeric', month: 'long', day: 'numeric' }) : ''

async function load() {
  const { data } = await api.get('/payments/subscription/')
  info.value = data
}
onMounted(() => { document.title = 'Subscription — BOSS Magazine PH'; load() })

async function cancel() {
  busy.value = true
  error.value = ''
  try {
    const { data } = await api.post('/payments/subscription/cancel/')
    info.value = data
    confirming.value = false
    message.value = `Cancelled. You can still read everything until ${fmt(data.subscription.access_until)}.`
    auth.fetchUser()
  } catch (e) {
    error.value = e.response?.data?.detail || 'Could not cancel just now. Try again.'
  } finally { busy.value = false }
}
</script>

<template>
  <BossShell>
    <section class="wrap">
      <router-link to="/account" class="back">← Your account</router-link>
      <h1>Subscription</h1>

      <p v-if="!info" class="muted" role="status">Loading…</p>

      <template v-else>
        <p v-if="message" class="notice" role="status">{{ message }}</p>
        <p v-if="error" class="notice bad" role="alert">{{ error }}</p>

        <div v-if="sub" class="card">
          <dl>
            <div><dt>Plan</dt><dd>{{ sub.plan_name }}</dd></div>
            <div>
              <dt>{{ sub.status === 'CANCELLED' ? 'Access ends' : 'Paid up to' }}</dt>
              <dd>{{ fmt(sub.access_until) }}</dd>
            </div>
            <div><dt>Status</dt>
              <dd>{{ sub.status === 'CANCELLED' ? 'Cancelled: not renewing' : 'Active' }}</dd></div>
            <div v-if="info.payment_method"><dt>Last paid with</dt><dd>{{ info.payment_method }}</dd></div>
          </dl>

          <p class="hint">
            Subscriptions are prepaid, so nothing is charged automatically. You choose how
            to pay (GCash, Maya, a card or QR Ph) each time you renew, and renewing adds
            the new period to the end of this one.
          </p>

          <div v-if="!confirming" class="actions">
            <router-link to="/subscribe" class="cta">Renew or change how you pay</router-link>
            <button v-if="sub.status === 'ACTIVE'" class="ghost" @click="confirming = true">
              Cancel subscription
            </button>
          </div>

          <div v-else class="confirm" role="alertdialog" aria-labelledby="cq">
            <p id="cq">
              Your access continues until <b>{{ fmt(sub.access_until) }}</b>, then your account
              returns to a free account. Nothing more will be charged. Cancel?
            </p>
            <div class="actions">
              <button class="danger" :disabled="busy" @click="cancel">
                {{ busy ? 'Cancelling…' : 'Confirm cancellation' }}
              </button>
              <button class="ghost" :disabled="busy" @click="confirming = false">Keep subscription</button>
            </div>
          </div>
        </div>

        <div v-else-if="info.granted_by_staff" class="card">
          <p>Your subscription was set up by BOSS Magazine and has no end date. To change it,
            contact the editorial team.</p>
        </div>

        <div v-else class="card">
          <p>You have a free account. Subscribe to read every story and every digital issue.</p>
          <div class="actions"><router-link to="/subscribe" class="cta">See plans</router-link></div>
        </div>

        <template v-if="info.history.length">
          <h2>Payments</h2>
          <table>
            <thead><tr><th>Date</th><th>Plan</th><th>Amount</th><th>Method</th><th>Result</th></tr></thead>
            <tbody>
              <tr v-for="(h, i) in info.history" :key="i">
                <td>{{ fmt(h.date) }}</td><td>{{ h.plan }}</td><td>{{ h.amount }}</td>
                <td>{{ h.method }}</td><td>{{ h.status }}</td>
              </tr>
            </tbody>
          </table>
        </template>
      </template>
    </section>
  </BossShell>
</template>

<style scoped>
.wrap { max-width: 760px; margin: 0 auto; padding: var(--s-8) var(--s-7) var(--s-9);
        font-family: var(--font-ui); color: var(--boss-text); }
.back { color: var(--boss-text-muted); font-size: var(--t-sm); text-decoration: none; }
.back:hover { color: var(--boss-gold); }
h1 { font-family: var(--font-serif); font-size: var(--t-3xl); font-weight: 400;
     margin: var(--s-4) 0 var(--s-6); }
h2 { font-family: var(--font-serif); font-size: var(--t-xl); font-weight: 400;
     margin: var(--s-7) 0 var(--s-4); }
.muted { color: var(--boss-text-muted); }
.notice { border: 1px solid var(--boss-gold-deep); padding: var(--s-3) var(--s-4);
          font-size: var(--t-sm); margin: 0 0 var(--s-5); }
.notice.bad { border-color: #8a3b32; background: rgba(138, 59, 50, .15); }
.card { background: var(--boss-surface); border: 1px solid var(--boss-line); padding: var(--s-6); }
.card > p { color: var(--boss-text-muted); font-size: var(--t-sm); line-height: var(--lh-body); margin: 0; }
dl { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
     gap: var(--s-5); margin: 0 0 var(--s-5); }
dt { font-size: var(--t-xs); letter-spacing: var(--track-caps); text-transform: uppercase;
     color: var(--boss-gold); margin-bottom: var(--s-1); }
dd { margin: 0; font-size: var(--t-md); }
.hint { font-size: var(--t-sm); color: var(--boss-text-muted); line-height: var(--lh-snug);
        margin: 0 0 var(--s-5) !important; }
.actions { display: flex; flex-wrap: wrap; gap: var(--s-3); margin-top: var(--s-4); }
.cta, .ghost, .danger { display: inline-block; padding: var(--s-3) var(--s-5); font-size: var(--t-xs);
        font-weight: 700; letter-spacing: var(--track-caps); text-transform: uppercase;
        cursor: pointer; font-family: inherit; text-decoration: none; border: 1px solid transparent; }
.cta { background: var(--boss-gold); color: var(--boss-bg); }
.cta:hover { background: var(--boss-gold-bright); }
.ghost { background: transparent; color: var(--boss-text); border-color: var(--boss-line); }
.ghost:hover { border-color: var(--boss-gold-deep); }
.danger { background: #8a3b32; color: #fff; }
.danger:disabled, .ghost:disabled { opacity: .6; cursor: not-allowed; }
.confirm { border-top: 1px solid var(--boss-line); padding-top: var(--s-4); }
.confirm p { margin: 0; font-size: var(--t-sm); line-height: var(--lh-body); }
table { width: 100%; border-collapse: collapse; font-size: var(--t-sm); }
th { text-align: left; font-weight: 400; font-size: var(--t-xs); letter-spacing: var(--track-caps);
     text-transform: uppercase; color: var(--boss-text-faint); padding: var(--s-2) var(--s-2) var(--s-2) 0;
     border-bottom: 1px solid var(--boss-line); }
td { padding: var(--s-3) var(--s-2) var(--s-3) 0; border-bottom: 1px solid var(--boss-line); }
@media (max-width: 600px) {
  .wrap { padding-left: var(--s-5); padding-right: var(--s-5); }
  table { font-size: var(--t-xs); }
}
</style>
