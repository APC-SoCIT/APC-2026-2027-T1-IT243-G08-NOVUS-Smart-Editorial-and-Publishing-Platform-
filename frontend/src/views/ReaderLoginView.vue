<script setup>
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const email = ref('')
const password = ref('')
const showPassword = ref(false)
const error = ref('')
const loading = ref(false)

const auth = useAuthStore()
const router = useRouter()

const emailValid = computed(() =>
  !email.value || /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.value))

async function submit() {
  if (loading.value) return
  error.value = ''
  if (!email.value || !password.value) {
    error.value = 'Enter your email address and password.'
    return
  }
  loading.value = true
  try {
    await auth.login(email.value, password.value)
    if (auth.role !== 'READER') {
      auth.logout()
      error.value = 'Editorial accounts sign in at the staff portal.'
      return
    }
    router.push('/read')
  } catch {
    error.value = 'Those credentials were not recognised.'
  } finally { loading.value = false }
}
</script>

<template>
  <div class="boss page">
    <router-link to="/read" class="back">← Back to BOSS</router-link>

    <main class="card">
      <img src="/boss-logo.png" alt="BOSS Magazine PH" class="mark" />
      <p class="tag">Sign in to read premium stories and digital issues.</p>

      <label :class="{ bad: !emailValid }">
        EMAIL
        <input v-model.trim="email" type="email" autocomplete="username"
               required :aria-invalid="!emailValid" @keyup.enter="submit" />
      </label>

      <label>
        PASSWORD
        <div class="pw">
          <input v-model="password" :type="showPassword ? 'text' : 'password'"
                 autocomplete="current-password" required @keyup.enter="submit" />
          <button type="button" class="peek" :aria-pressed="showPassword"
                  :aria-label="showPassword ? 'Hide password' : 'Show password'"
                  @click="showPassword = !showPassword">
            <span aria-hidden="true">{{ showPassword ? 'Hide' : 'Show' }}</span>
          </button>
        </div>
      </label>

      <p v-if="error" class="error" role="alert">{{ error }}</p>

      <button class="go" :disabled="loading" @click="submit">
        {{ loading ? 'Signing in…' : 'Sign in' }}
      </button>

      <p class="note">Free articles need no account.</p>

      <div class="alt">
        <p>New here? <router-link to="/register">Create an account</router-link></p>
      </div>
    </main>
  </div>
</template>

<style scoped>
.page { min-height: 100vh; background: var(--boss-bg); color: var(--boss-text);
        display: flex; align-items: center; justify-content: center;
        padding: var(--s-6); position: relative; font-family: var(--font-ui); }
.back { position: absolute; top: var(--s-6); left: var(--s-7);
        font-size: var(--t-xs); letter-spacing: var(--track-caps);
        text-transform: uppercase; color: var(--boss-text-faint);
        transition: color var(--dur-fast) var(--ease-out); }
.back:hover { color: var(--boss-gold); }

.card { width: 100%; max-width: 400px; background: var(--boss-surface);
        border: 1px solid var(--boss-line); border-radius: var(--r-lg);
        padding: var(--s-8) var(--s-7); text-align: center; }
.mark { height: 52px; width: auto; margin: 0 auto var(--s-4); }
.tag { color: var(--boss-text-muted); font-size: var(--t-sm);
       line-height: var(--lh-body); margin: 0 0 var(--s-7); }

label { display: block; text-align: left; font-size: var(--t-xs);
        letter-spacing: var(--track-caps); color: var(--boss-text-muted);
        margin-bottom: var(--s-4); }
label.bad { color: #d98080; }
input { width: 100%; margin-top: var(--s-2); padding: 13px 15px;
        font-size: var(--t-base); font-family: inherit;
        background: var(--boss-surface-2); color: var(--boss-text);
        border: 1px solid var(--boss-line); border-radius: var(--r-sm);
        transition: border-color var(--dur-fast) var(--ease-out); }
input:focus { outline: none; border-color: var(--boss-gold); }
.pw { position: relative; }
.peek { position: absolute; right: 6px; top: 50%; transform: translateY(-25%);
        background: none; border: 0; color: var(--boss-gold);
        font-size: var(--t-xs); cursor: pointer; padding: 7px 10px;
        font-family: inherit; }

.error { background: rgba(158,47,47,.14); border: 1px solid rgba(158,47,47,.4);
         color: #e09a9a; padding: 11px 14px; border-radius: var(--r-sm);
         font-size: var(--t-sm); margin: 0 0 var(--s-4); text-align: left; }

.go { width: 100%; padding: 14px; border: 0; background: var(--boss-gold);
      color: var(--boss-bg); border-radius: var(--r-sm); font-weight: 700;
      font-size: var(--t-sm); letter-spacing: var(--track-caps);
      text-transform: uppercase; cursor: pointer; font-family: inherit;
      transition: background var(--dur-base) var(--ease-out); }
.go:hover:not(:disabled) { background: var(--boss-gold-bright); }
.go:disabled { opacity: .5; cursor: not-allowed; }

.note { font-size: var(--t-xs); color: var(--boss-text-faint);
        margin: var(--s-4) 0 0; }
.alt { margin-top: var(--s-6); padding-top: var(--s-5);
       border-top: 1px solid var(--boss-line); }
.alt p { font-size: var(--t-sm); color: var(--boss-text-muted); margin: 0 0 var(--s-2); }
.alt a { color: var(--boss-gold); }
.alt a:hover { color: var(--boss-gold-bright); }
</style>
