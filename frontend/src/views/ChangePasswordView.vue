<script setup>
/*
 * Change password. Reached two ways: by choice from the account page, or
 * by force when a password has expired (90 days) or an administrator has
 * required a change. In the forced case the router sends the user here
 * from every page, and the API refuses everything else, until it is done.
 */
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import api from '../services/api'
import { useAuthStore } from '../stores/auth'

const HOME = { WRITER: '/writer', EDITOR: '/editor', PUBLISHER: '/publisher',
               GRAPHIC_DESIGNER: '/designer', ADMIN: '/editor', READER: '/read' }

const auth = useAuthStore()
const router = useRouter()

const current = ref('')
const next = ref('')
const confirm = ref('')
const show = ref(false)
const saving = ref(false)
const done = ref(false)
const errors = ref({})

const forced = computed(() => !!auth.user?.must_change_password)
const mismatch = computed(() => !!confirm.value && next.value !== confirm.value)

onMounted(async () => {
  document.title = 'Change your password'
  if (!auth.user) { try { await auth.fetchUser() } catch { /* the guard handles it */ } }
})

const list = (v) => (Array.isArray(v) ? v : v ? [v] : [])

async function submit() {
  errors.value = {}
  if (!current.value || !next.value || !confirm.value) {
    errors.value.form = 'Fill in all three fields.'
    return
  }
  if (next.value !== confirm.value) return

  const wasForced = forced.value
  saving.value = true
  try {
    const { data } = await api.post('/auth/password/', {
      current_password: current.value, new_password: next.value })
    auth.user = data
    done.value = true
    current.value = next.value = confirm.value = ''
    setTimeout(() => router.push(wasForced ? (HOME[data.role] || '/read') : '/account'), 1200)
  } catch (e) {
    const d = e.response?.data || {}
    errors.value = {
      current_password: list(d.current_password)[0],
      new_password: list(d.new_password),
      form: e.response?.status === 429
        ? 'Too many attempts. Wait a while before trying again.'
        : (!d.current_password && !d.new_password ? (d.detail || 'Could not change your password.') : ''),
    }
  } finally { saving.value = false }
}

function signOut() {
  const staff = auth.role && auth.role !== 'READER'
  auth.logout()
  router.push(staff ? '/staff/login' : '/login')
}
</script>

<template>
  <main class="cp">
    <form class="card" novalidate @submit.prevent="submit">
      <p class="eyebrow">Account security</p>
      <h1>Change your password</h1>

      <p v-if="forced" class="notice" role="status">
        Your password has expired, or an administrator has asked you to change it.
        Choose a new one to continue.
      </p>
      <p v-else class="sub">Choose a new password for your account.</p>

      <p v-if="done" class="ok" role="status">Password changed. Taking you back…</p>
      <p v-if="errors.form" class="alert" role="alert">{{ errors.form }}</p>

      <label for="cp-current">Current password</label>
      <input id="cp-current" v-model="current" :type="show ? 'text' : 'password'"
             autocomplete="current-password" :aria-invalid="!!errors.current_password" />
      <p v-if="errors.current_password" class="err">{{ errors.current_password }}</p>

      <label for="cp-new">New password</label>
      <input id="cp-new" v-model="next" :type="show ? 'text' : 'password'"
             autocomplete="new-password" :aria-invalid="!!(errors.new_password && errors.new_password.length)" />
      <ul v-if="errors.new_password && errors.new_password.length" class="err">
        <li v-for="m in errors.new_password" :key="m">{{ m }}</li>
      </ul>

      <label for="cp-confirm">Confirm new password</label>
      <input id="cp-confirm" v-model="confirm" :type="show ? 'text' : 'password'"
             autocomplete="new-password" :aria-invalid="mismatch" />
      <p v-if="mismatch" class="err">The new passwords do not match.</p>

      <label class="check"><input v-model="show" type="checkbox" /> Show passwords</label>

      <ul class="rules" aria-label="Password rules">
        <li>At least 8 characters</li>
        <li>Not a common password, and not all numbers</li>
        <li>Not too similar to your name or email</li>
        <li>Not one of your last 4 passwords</li>
      </ul>

      <button class="primary" type="submit" :disabled="saving || done">
        {{ saving ? 'Changing…' : 'Change password' }}
      </button>
      <button v-if="forced" type="button" class="link" @click="signOut">Sign out instead</button>
      <router-link v-else to="/account" class="link">Back to your account</router-link>
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
.sub { margin: 0 0 20px; font-size: 14px; color: var(--nv-text-muted, #56627a); }
.notice { margin: 0 0 20px; padding: 10px 12px; border-radius: 8px; font-size: 13.5px;
          background: rgba(178, 106, 0, .1); color: var(--warn, #8a5300); }
.ok { margin: 0 0 16px; padding: 10px 12px; border-radius: 8px; font-size: 13.5px;
      background: var(--ok-bg, #e8f6ee); color: var(--ok, #1c6b45); }
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
.primary { box-sizing: border-box; width: 100%; height: 46px; border: 0; border-radius: 10px;
           background: #0f1a33; color: #fff; font: inherit; font-size: 15px; font-weight: 600; cursor: pointer; }
.primary:disabled { opacity: .6; cursor: not-allowed; }
.link { display: block; width: 100%; margin-top: 14px; border: 0; background: none; cursor: pointer;
        text-align: center; font: inherit; font-size: 13.5px; color: #3d5ba9; text-decoration: none; }
</style>
