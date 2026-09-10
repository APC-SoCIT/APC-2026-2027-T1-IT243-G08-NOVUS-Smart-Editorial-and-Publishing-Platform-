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
  <div class="page">
    <router-link to="/read" class="back">← Back to BOSS</router-link>

    <div class="card">
      <h1>BOSS</h1>
      <p class="tag">Sign in to read premium stories and save articles.</p>

      <label :class="{ bad: !emailValid }">
        EMAIL
        <input v-model.trim="email" type="email" autocomplete="username"
               @keyup.enter="submit" />
      </label>

      <label>
        PASSWORD
        <div class="pw">
          <input v-model="password" :type="showPassword ? 'text' : 'password'"
                 autocomplete="current-password" @keyup.enter="submit" />
          <button type="button" class="peek" @click="showPassword = !showPassword">
            {{ showPassword ? 'Hide' : 'Show' }}
          </button>
        </div>
      </label>

      <p v-if="error" class="error">{{ error }}</p>

      <button class="go" :disabled="loading" @click="submit">
        {{ loading ? 'Signing in…' : 'Sign in' }}
      </button>

      <p class="note">Free articles need no account.</p>
      <p class="alt">New here? <router-link to="/register">Create an account</router-link></p>
      <p class="alt"><router-link to="/staff/login">Editorial team login</router-link></p>
    </div>
  </div>
</template>

<style scoped>
.page { min-height: 100vh; display: flex; flex-direction: column;
        align-items: center; justify-content: center; font-family: Georgia, serif;
        background: #fbfbfa; padding: 24px; position: relative; }
.back { position: absolute; top: 26px; left: 30px; font-family: system-ui;
        font-size: 13px; color: #888; }
.card { width: 100%; max-width: 380px; background: #fff; border: 1px solid #ececec;
        border-radius: 14px; padding: 42px 38px; text-align: center; }
h1 { font-size: 42px; letter-spacing: 7px; margin: 0 0 8px; font-weight: 700; }
.tag { color: #888; font-size: 14px; margin: 0 0 30px; line-height: 1.55; }
label { display: block; font-family: system-ui; font-size: 11px; letter-spacing: .6px;
        color: #667; text-align: left; margin-bottom: 16px; }
label.bad { color: #b53b3b; }
input { width: 100%; margin-top: 7px; padding: 12px 14px; border: 1px solid #ddd;
        border-radius: 8px; font-size: 15px; font-family: system-ui; }
input:focus { outline: none; border-color: #111; }
.pw { position: relative; }
.peek { position: absolute; right: 6px; top: 50%; transform: translateY(-25%);
        border: 0; background: none; color: #4a7fb5; font-size: 12px;
        font-family: system-ui; cursor: pointer; padding: 6px 9px; }
.error { background: #fdeeee; border: 1px solid #f0cfcf; color: #a33;
         padding: 10px 12px; border-radius: 8px; font-size: 13px;
         font-family: system-ui; margin: 0 0 14px; text-align: left; }
.go { width: 100%; padding: 13px; border: 0; background: #111; color: #fff;
      border-radius: 8px; font-family: system-ui; font-weight: 600;
      font-size: 15px; cursor: pointer; }
.go:disabled { opacity: .5; }
.note { font-family: system-ui; font-size: 12px; color: #aaa; margin: 16px 0 0; }
.alt { font-family: system-ui; font-size: 13px; margin: 20px 0 0; }
.alt a { color: #4a7fb5; }
</style>
