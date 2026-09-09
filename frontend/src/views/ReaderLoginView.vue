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

async function submit() {
  error.value = ''
  loading.value = true
  try {
    await auth.login(email.value, password.value)
    if (auth.role !== 'READER') {
      auth.logout()
      error.value = 'Editorial accounts sign in at /staff/login.'
      return
    }
    router.push('/read')
  } catch (e) {
    error.value = 'Invalid email or password.'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="wrap">
    <h1>BOSS</h1>
    <p class="tag">Sign in to read premium stories.</p>
    <input v-model="email" type="email" placeholder="Email" @keyup.enter="submit" />
    <input v-model="password" type="password" placeholder="Password" @keyup.enter="submit" />
    <p v-if="error" class="err">{{ error }}</p>
    <button :disabled="loading" @click="submit">
      {{ loading ? 'Signing in…' : 'Sign In' }}
    </button>
    <p class="alt"><router-link to="/staff/login">Editorial team login</router-link></p>
  </div>
</template>

<style scoped>
.wrap { max-width: 380px; margin: 90px auto; font-family: Georgia, serif; text-align: center; }
h1 { font-size: 46px; margin: 0; letter-spacing: 6px; }
.tag { color: #777; margin-bottom: 28px; }
input { width: 100%; padding: 12px; margin-top: 10px; border: 1px solid #ddd; border-radius: 4px;
        font-family: system-ui; }
button { width: 100%; margin-top: 18px; padding: 12px; border: 0; background: #111; color: #fff;
         font-family: system-ui; font-weight: 600; cursor: pointer; }
button:disabled { opacity: .55; }
.err { color: #c00; font-size: 13px; font-family: system-ui; }
.alt { margin-top: 24px; font-size: 13px; font-family: system-ui; }
</style>
