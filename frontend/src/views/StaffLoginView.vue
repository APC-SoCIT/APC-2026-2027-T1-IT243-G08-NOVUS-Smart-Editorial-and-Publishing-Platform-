<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const email = ref('')
const password = ref('')
const error = ref('')
const loading = ref(false)
const auth = useAuthStore()
const router = useRouter()

const DEST = {
  WRITER: '/writer',
  EDITOR: '/editor',
  PUBLISHER: '/publisher',
  GRAPHIC_DESIGNER: '/designer',
  ADMIN: '/writer',
}

async function submit() {
  error.value = ''
  loading.value = true
  try {
    await auth.login(email.value, password.value)
    if (auth.role === 'READER') {
      auth.logout()
      error.value = 'This is the staff login. Readers should sign in at /login.'
      return
    }
    router.push(DEST[auth.role] || '/writer')
  } catch (e) {
    error.value = 'Invalid email or password.'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="shell">
    <aside>
      <h1>NOVUS</h1>
      <p>Smart Editorial &amp; Publishing Platform</p>
      <small>© NOVUS 2026</small>
    </aside>
    <main>
      <h2>Welcome back!</h2>
      <p class="sub">Log in to continue to your workspace.</p>
      <label>EMAIL</label>
      <input v-model="email" type="email" @keyup.enter="submit" />
      <label>PASSWORD</label>
      <input v-model="password" type="password" @keyup.enter="submit" />
      <p v-if="error" class="err">{{ error }}</p>
      <button :disabled="loading" @click="submit">
        {{ loading ? 'Logging in…' : 'Log In' }}
      </button>
      <p class="alt">Not staff? <router-link to="/login">Reader sign in</router-link></p>
    </main>
  </div>
</template>

<style scoped>
.shell { display: flex; min-height: 100vh; font-family: system-ui; }
aside { width: 40%; background: #0d1526; color: #fff; padding: 48px 40px; display: flex;
        flex-direction: column; justify-content: center; }
aside h1 { font-size: 44px; margin: 0 0 8px; letter-spacing: 2px; }
aside p { color: #9fb0cc; margin: 0; }
aside small { margin-top: auto; color: #5e6f8c; }
main { flex: 1; padding: 80px 56px; max-width: 420px; }
h2 { margin: 0; font-size: 30px; }
.sub { color: #666; margin-top: 4px; }
label { display: block; font-size: 11px; margin-top: 18px; color: #444; letter-spacing: .5px; }
input { width: 100%; padding: 11px; border: 1px solid #ccc; border-radius: 24px; }
button { width: 100%; margin-top: 22px; padding: 12px; border: 0; border-radius: 24px;
         background: #1a2744; color: #fff; font-weight: 600; cursor: pointer; }
button:disabled { opacity: .55; }
.err { color: #c00; font-size: 13px; }
.alt { font-size: 13px; color: #666; margin-top: 20px; }
</style>
