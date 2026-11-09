<script setup>
/*
 * UC-5.2.2 steps 4-5: open the emailed link and choose a new password.
 * The link is checked before the form is shown (step 4.1), and the token is
 * then removed from the address bar so it does not stay in browser history.
 */
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import api from '../services/api'

const route = useRoute()
const router = useRouter()

const token = ref('')
const state = ref('checking')   // checking | form | invalid
const next = ref('')
const confirm = ref('')
const show = ref(false)
const saving = ref(false)
const errors = ref({})

const mismatch = computed(() => !!confirm.value && next.value !== confirm.value)
const list = (v) => (Array.isArray(v) ? v : v ? [v] : [])

onMounted(async () => {
  document.title = 'Choose a new password'
  token.value = String(route.query.token || '')
  if (token.value) window.history.replaceState(null, '', '/reset-password')
  if (!token.value) { state.value = 'invalid'; return }
  try {
    await api.post('/auth/password/reset/verify/', { token: token.value })
    state.value = 'form'
  } catch { state.value = 'invalid' }
})

async function submit() {
  errors.value = {}
  if (!next.value || !confirm.value) {
    errors.value.form = 'Type your new password twice.'
    return
  }
  if (mismatch.value) return
  saving.value = true
  try {
    const { data } = await api.post('/auth/password/reset/', {
      token: token.value, new_password: next.value })
    router.push({ path: data.staff ? '/staff/login' : '/login', query: { reset: '1' } })
  } catch (e) {
    const d = e.response?.data || {}
    if (d.code === 'invalid_link') { state.value = 'invalid'; return }
    errors.value = {
      new_password: list(d.new_password),
      form: e.response?.status === 429
        ? 'Too many attempts. Wait a while before trying again.'
        : (!d.new_password ? 'Could not save your password. Try again.' : ''),
    }
  } finally { saving.value = false }
}
</script>

<template>
  <main class="cp">
    <div class="card">
      <p class="eyebrow">Account security</p>

      <template v-if="state === 'checking'">
        <h1>Checking your link…</h1>
      </template>

      <template v-else-if="state === 'invalid'">
        <h1>This link has expired</h1>
        <p class="sub">Reset links work once and expire after 1 hour. Ask for a new one and use the latest email.</p>
        <router-link to="/forgot-password" class="primary as-link">Send a new link</router-link>
        <router-link to="/login" class="link">Back to sign in</router-link>
      </template>

      <form v-else novalidate @submit.prevent="submit">
        <h1>Choose a new password</h1>
        <p class="sub">You'll use it to sign in from now on.</p>
        <p v-if="errors.form" class="alert" role="alert">{{ errors.form }}</p>

        <label for="rp-new">New password</label>
        <input id="rp-new" v-model="next" :type="show ? 'text' : 'password'" autocomplete="new-password"
               autofocus :aria-invalid="!!(errors.new_password && errors.new_password.length)" />
        <ul v-if="errors.new_password && errors.new_password.length" class="err">
          <li v-for="m in errors.new_password" :key="m">{{ m }}</li>
        </ul>

        <label for="rp-confirm">Confirm new password</label>
        <input id="rp-confirm" v-model="confirm" :type="show ? 'text' : 'password'"
               autocomplete="new-password" :aria-invalid="mismatch" />
        <p v-if="mismatch" class="err">The new passwords do not match.</p>

        <label class="check"><input v-model="show" type="checkbox" /> Show passwords</label>

        <ul class="rules" aria-label="Password rules">
          <li>At least 8 characters</li>
          <li>Not a common password, and not all numbers</li>
          <li>Not too similar to your name or email</li>
          <li>Not one of your last 4 passwords</li>
        </ul>

        <button class="primary" type="submit" :disabled="saving">
          {{ saving ? 'Saving…' : 'Save new password' }}
        </button>
      </form>
    </div>
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
.alert { margin: 0 0 16px; padding: 10px 12px; border-radius: 8px; font-size: 13.5px;
         background: var(--bad-bg, #fdecec); color: var(--bad, #b42318); }
label { display: block; margin: 14px 0 6px; font-size: 12px; font-weight: 700;
        letter-spacing: .06em; text-transform: uppercase; color: var(--nv-text, #3c4a66); }
input[type="password"], input[type="text"] {
  box-sizing: border-box; width: 100%; height: 44px; padding: 0 12px; border-radius: 9px;
  border: 1px solid var(--nv-line, #d5dbe7); background: var(--nv-bg, #f8fafd);
  font: inherit; font-size: 14.5px; color: var(--nv-text, #0f1a33); }
input:focus { outline: none; border-color: #3d5ba9; box-shadow: 0 0 0 4px rgba(61, 91, 169, .16); }
input[aria-invalid="true"] { border-color: var(--bad, #b42318); }
.check { display: flex; align-items: center; gap: 8px; margin-top: 14px; font-size: 13px;
         font-weight: 500; letter-spacing: 0; text-transform: none; color: var(--nv-text-muted, #56627a); }
.err { margin: 6px 0 0; padding-left: 0; list-style: none; font-size: 12.5px; color: var(--bad, #b42318); }
.rules { margin: 18px 0; padding: 12px 14px 12px 30px; border-radius: 9px; font-size: 12.5px;
         line-height: 1.7; background: var(--nv-bg, #f5f7fb); color: var(--nv-text-muted, #56627a); }
.primary { box-sizing: border-box; display: flex; align-items: center; justify-content: center; width: 100%;
           height: 46px; border: 0; border-radius: 10px; background: #0f1a33; color: #fff; font: inherit;
           font-size: 15px; font-weight: 600; cursor: pointer; text-decoration: none; }
.primary:disabled { opacity: .6; cursor: not-allowed; }
.link { display: block; width: 100%; margin-top: 14px; border: 0; background: none; cursor: pointer;
        text-align: center; font: inherit; font-size: 13.5px; color: #3d5ba9; text-decoration: none; }
</style>
