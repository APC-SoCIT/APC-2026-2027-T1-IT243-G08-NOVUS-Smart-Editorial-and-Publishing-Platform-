<script setup>
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import api from '../services/api'
import { useAuthStore } from '../stores/auth'

const first = ref('')
const last = ref('')
const email = ref('')
const password = ref('')
const showPassword = ref(false)
const error = ref('')
const loading = ref(false)
const acceptTerms = ref(false)
const acceptMarketing = ref(false)

const auth = useAuthStore()
const router = useRouter()

const emailValid = computed(() =>
  !email.value || /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.value))

const strength = computed(() => {
  const p = password.value
  if (!p) return { score: 0, label: '' }
  let score = 0
  if (p.length >= 8) score++
  if (p.length >= 12) score++
  if (/[A-Z]/.test(p) && /[a-z]/.test(p)) score++
  if (/\d/.test(p)) score++
  if (/[^A-Za-z0-9]/.test(p)) score++
  return { score, label: ['Very weak', 'Weak', 'Fair', 'Good', 'Strong'][Math.min(score, 4)] }
})

async function submit() {
  if (loading.value) return
  error.value = ''

  if (!first.value || !last.value || !email.value || !password.value) {
    error.value = 'Fill in every field.'
    return
  }
  if (!emailValid.value) { error.value = 'Check your email address.'; return }
  if (password.value.length < 8) {
    error.value = 'Your password must be at least 8 characters.'
    return
  }
  if (!acceptTerms.value) {
    error.value = 'Please accept the Terms of Service and Privacy Policy to continue.'
    return
  }

  loading.value = true
  try {
    await api.post('/auth/register/', {
      first_name: first.value,
      last_name: last.value,
      email: email.value,
      password: password.value,
    })
    // Sign them straight in — asking someone to log in immediately after
    // registering is friction with no purpose.
    await auth.login(email.value, password.value)
    router.push('/read')
  } catch (e) {
    const d = e.response?.data
    error.value = d?.email?.[0] || d?.password?.[0] || 'Could not create your account.'
  } finally { loading.value = false }
}
</script>

<template>
  <div class="boss page">
    <router-link to="/read" class="back">← Back to BOSS</router-link>

    <div class="card">
      <h1>BOSS</h1>
      <p class="tag">Create a free account to save articles and follow the magazine.</p>

      <div class="row">
        <label>FIRST NAME<input v-model.trim="first" @keyup.enter="submit" /></label>
        <label>LAST NAME<input v-model.trim="last" @keyup.enter="submit" /></label>
      </div>

      <label :class="{ bad: !emailValid }">
        EMAIL
        <input v-model.trim="email" type="email" autocomplete="username"
               @keyup.enter="submit" />
      </label>

      <label>
        PASSWORD
        <div class="pw">
          <input v-model="password" :type="showPassword ? 'text' : 'password'"
                 autocomplete="new-password" @keyup.enter="submit" />
          <button type="button" class="peek" @click="showPassword = !showPassword">
            {{ showPassword ? 'Hide' : 'Show' }}
          </button>
        </div>
      </label>

      <div v-if="password" class="meter">
        <div class="bars">
          <i v-for="n in 5" :key="n" :class="{ on: n <= strength.score }"
             :data-lvl="strength.score"></i>
        </div>
        <span>{{ strength.label }}</span>
      </div>

      <fieldset class="consent">
        <legend class="sr-only">Consent</legend>

        <label class="check">
          <input type="checkbox" v-model="acceptTerms" required />
          <span>
            I have read and accept the
            <router-link to="/legal/terms" target="_blank">Terms of Service</router-link>
            and
            <router-link to="/legal/privacy" target="_blank">Privacy Policy</router-link>.
          </span>
        </label>

        <label class="check">
          <input type="checkbox" v-model="acceptMarketing" />
          <span>
            Email me when a new issue is published.
            <em>Optional — you can change this at any time.</em>
          </span>
        </label>
      </fieldset>

      <p v-if="error" class="error" role="alert">{{ error }}</p>

      <button class="go" :disabled="loading" @click="submit">
        {{ loading ? 'Creating account…' : 'Create account' }}
      </button>

      <p class="note">
        Free articles need no account. A subscription unlocks premium stories
        and digital issues.
      </p>
      <p class="alt">
        Already registered? <router-link to="/login">Sign in</router-link>
      </p>
    </div>
  </div>
</template>

<style scoped>
.page { min-height: 100vh; background: var(--boss-bg); color: var(--boss-text);
        display: flex; align-items: center; justify-content: center;
        padding: var(--s-6); position: relative; font-family: var(--font-ui); }
.back { position: absolute; top: var(--s-6); left: var(--s-7);
        font-size: var(--t-xs); letter-spacing: var(--track-caps);
        text-transform: uppercase; color: var(--boss-text-faint); }
.back:hover { color: var(--boss-gold); }

.card { width: 100%; max-width: 440px; background: var(--boss-surface);
        border: 1px solid var(--boss-line); border-radius: var(--r-lg);
        padding: var(--s-7); text-align: center; }
h1 { font-family: var(--font-serif); font-size: var(--t-2xl);
     letter-spacing: .18em; margin: 0 0 var(--s-2); color: var(--boss-gold); }
.tag { color: var(--boss-text-muted); font-size: var(--t-sm);
       line-height: var(--lh-body); margin: 0 0 var(--s-6); }

.row { display: flex; gap: var(--s-3); }
.row label { flex: 1; }
label { display: block; text-align: left; font-size: var(--t-xs);
        letter-spacing: var(--track-caps); color: var(--boss-text-muted);
        margin-bottom: var(--s-4); }
label.bad { color: #d98080; }
input { width: 100%; margin-top: var(--s-2); padding: 12px 14px;
        font-size: var(--t-base); font-family: inherit;
        background: var(--boss-surface-2); color: var(--boss-text);
        border: 1px solid var(--boss-line); border-radius: var(--r-sm); }
input:focus { outline: none; border-color: var(--boss-gold); }
.pw { position: relative; }
.peek { position: absolute; right: 6px; top: 50%; transform: translateY(-25%);
        background: none; border: 0; color: var(--boss-gold);
        font-size: var(--t-xs); cursor: pointer; padding: 7px 10px;
        font-family: inherit; }

.meter { display: flex; align-items: center; gap: var(--s-3);
         margin: -6px 0 var(--s-4); }
.bars { display: flex; gap: 3px; flex: 1; }
.bars i { height: 4px; flex: 1; background: var(--boss-line); border-radius: 2px; }
.bars i.on[data-lvl="0"], .bars i.on[data-lvl="1"] { background: #a84a4a; }
.bars i.on[data-lvl="2"] { background: #a87a2a; }
.bars i.on[data-lvl="3"] { background: #7a9a5a; }
.bars i.on[data-lvl="4"], .bars i.on[data-lvl="5"] { background: #4a9a6a; }
.meter span { font-size: var(--t-xs); color: var(--boss-text-faint);
              width: 66px; text-align: right; }

.consent { border: 0; padding: 0; margin: 0 0 var(--s-4); text-align: left; }
.check { display: flex; gap: 10px; align-items: flex-start;
         font-size: var(--t-sm); line-height: var(--lh-body);
         color: var(--boss-text-muted); margin-bottom: var(--s-3);
         cursor: pointer; letter-spacing: normal; text-transform: none; }
.check input { width: 16px; height: 16px; margin: 3px 0 0; flex-shrink: 0;
               accent-color: var(--boss-gold); }
.check a { color: var(--boss-gold); border-bottom: 1px solid var(--boss-gold-deep); }
.check em { display: block; color: var(--boss-text-faint); font-style: normal;
            font-size: var(--t-xs); margin-top: 2px; }

.error { background: rgba(158,47,47,.14); border: 1px solid rgba(158,47,47,.4);
         color: #e09a9a; padding: 11px 14px; border-radius: var(--r-sm);
         font-size: var(--t-sm); margin: 0 0 var(--s-4); text-align: left; }

.go { width: 100%; padding: 14px; border: 0; background: var(--boss-gold);
      color: var(--boss-bg); border-radius: var(--r-sm); font-weight: 700;
      font-size: var(--t-sm); letter-spacing: var(--track-caps);
      text-transform: uppercase; cursor: pointer; font-family: inherit; }
.go:hover:not(:disabled) { background: var(--boss-gold-bright); }
.go:disabled { opacity: .5; }

.note { font-size: var(--t-xs); color: var(--boss-text-faint);
        margin: var(--s-4) 0 0; line-height: var(--lh-body); }
.alt { font-size: var(--t-sm); color: var(--boss-text-muted);
       margin: var(--s-5) 0 0; }
.alt a { color: var(--boss-gold); }
</style>
