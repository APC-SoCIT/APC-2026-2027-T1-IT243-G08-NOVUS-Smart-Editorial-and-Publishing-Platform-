<script setup>
/*
 * UC-5.2.2 Recover a Forgotten Password, steps 1-2. The reply is the same
 * for every address, so this page never reveals who has an account.
 * ?staff=1 means the user came from the staff sign-in page, which decides
 * where "Back to sign in" goes.
 */
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import api from '../services/api'

const route = useRoute()
const staff = computed(() => route.query.staff === '1')
const signInPath = computed(() => (staff.value ? '/staff/login' : '/login'))

const email = ref('')
const sending = ref(false)
const sent = ref('')
const error = ref('')

const emailValid = computed(() => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.value))

onMounted(() => { document.title = 'Reset your password' })

async function submit() {
  error.value = ''
  if (!emailValid.value) {
    error.value = 'Enter the email address you sign in with.'
    return
  }
  sending.value = true
  try {
    const { data } = await api.post('/auth/password/forgot/', { email: email.value })
    sent.value = data.detail
  } catch (e) {
    error.value = e.response?.status === 429
      ? 'Too many requests for this address. Wait an hour before asking again.'
      : 'Could not send the link. Check your connection and try again.'
  } finally { sending.value = false }
}
</script>

<template>
  <main class="cp">
    <form class="card" novalidate @submit.prevent="submit">
      <p class="eyebrow">Account security</p>
      <h1>Reset your password</h1>

      <template v-if="!sent">
        <p class="sub">Enter the email address you sign in with. We'll send you a link to choose a new password.</p>
        <p v-if="error" class="alert" role="alert">{{ error }}</p>

        <label for="fp-email">Email address</label>
        <input id="fp-email" v-model.trim="email" type="email" inputmode="email"
               autocomplete="username" autofocus :aria-invalid="!!error" />

        <button class="primary" type="submit" :disabled="sending">
          {{ sending ? 'Sending…' : 'Send reset link' }}
        </button>
      </template>

      <template v-else>
        <p class="ok" role="status">{{ sent }}</p>
        <p class="sub">Check your inbox, and your spam folder. The link works once and expires in 1 hour.</p>
        <button type="button" class="link" @click="sent = ''">Use a different address</button>
      </template>

      <router-link :to="signInPath" class="link">Back to sign in</router-link>
    </form>
  </main>
</template>

<style scoped>
.cp { min-height: 100vh; display: grid; place-items: center; padding: 32px 16px;
      background: var(--nv-bg, #f5f7fb); }
.card { box-sizing: border-box; width: 100%; max-width: 420px; padding: 32px;
        border-radius: 14px; background: var(--nv-surface, #fff);
        border: 1px solid var(--nv-line, #e2e7f0); }
.eyebrow { margin: 0; font-size: 11.5px; font-weight: 700; letter-spacing: .14em;
           text-transform: uppercase; color: var(--nv-text-muted, #5b6b8c); }
h1 { margin: 6px 0 8px; font-size: 26px; color: var(--nv-text, #0f1a33); }
.sub { margin: 0 0 20px; font-size: 14px; line-height: 1.5; color: var(--nv-text-muted, #56627a); }
.ok { margin: 0 0 16px; padding: 10px 12px; border-radius: 8px; font-size: 13.5px;
      background: var(--ok-bg, #e8f6ee); color: var(--ok, #1c6b45); }
.alert { margin: 0 0 16px; padding: 10px 12px; border-radius: 8px; font-size: 13.5px;
         background: var(--bad-bg, #fdecec); color: var(--bad, #b42318); }
label { display: block; margin: 14px 0 6px; font-size: 12px; font-weight: 700;
        letter-spacing: .06em; text-transform: uppercase; color: var(--nv-text, #3c4a66); }
input { box-sizing: border-box; width: 100%; height: 44px; padding: 0 12px; border-radius: 9px;
        border: 1px solid var(--nv-line, #d5dbe7); background: var(--nv-bg, #f8fafd);
        font: inherit; font-size: 14.5px; color: var(--nv-text, #0f1a33); }
input:focus { outline: none; border-color: #3d5ba9; box-shadow: 0 0 0 4px rgba(61, 91, 169, .16); }
input[aria-invalid="true"] { border-color: var(--bad, #b42318); }
.primary { box-sizing: border-box; width: 100%; height: 46px; margin-top: 20px; border: 0; border-radius: 10px;
           background: #0f1a33; color: #fff; font: inherit; font-size: 15px; font-weight: 600; cursor: pointer; }
.primary:disabled { opacity: .6; cursor: not-allowed; }
.link { display: block; width: 100%; margin-top: 14px; border: 0; background: none; cursor: pointer;
        text-align: center; font: inherit; font-size: 13.5px; color: #3d5ba9; text-decoration: none; }
</style>
