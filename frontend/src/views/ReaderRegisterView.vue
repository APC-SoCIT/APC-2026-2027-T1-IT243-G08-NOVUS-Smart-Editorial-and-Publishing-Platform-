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
  <div class="page">
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
.page { min-height: 100vh; display: flex; align-items: center; justify-content: center;
        font-family: Georgia, serif; background: #fbfbfa; padding: 24px; position: relative; }
.back { position: absolute; top: 26px; left: 30px; font-family: system-ui;
        font-size: 13px; color: #888; }
.card { width: 100%; max-width: 420px; background: #fff; border: 1px solid #ececec;
        border-radius: 14px; padding: 40px 38px; text-align: center; }
h1 { font-size: 40px; letter-spacing: 7px; margin: 0 0 8px; font-weight: 700; }
.tag { color: #888; font-size: 14px; margin: 0 0 28px; line-height: 1.55; }
.row { display: flex; gap: 12px; }
.row label { flex: 1; }
label { display: block; font-family: system-ui; font-size: 11px; letter-spacing: .6px;
        color: #667; text-align: left; margin-bottom: 15px; }
label.bad { color: #b53b3b; }
input { width: 100%; margin-top: 7px; padding: 11px 13px; border: 1px solid #ddd;
        border-radius: 8px; font-size: 15px; font-family: system-ui; }
input:focus { outline: none; border-color: #111; }
.pw { position: relative; }
.peek { position: absolute; right: 6px; top: 50%; transform: translateY(-25%);
        border: 0; background: none; color: #4a7fb5; font-size: 12px;
        font-family: system-ui; cursor: pointer; padding: 6px 9px; }
.meter { display: flex; align-items: center; gap: 10px; margin: -6px 0 16px; }
.bars { display: flex; gap: 3px; flex: 1; }
.bars i { height: 4px; flex: 1; background: #e8e8e8; border-radius: 2px; }
.bars i.on[data-lvl="1"], .bars i.on[data-lvl="0"] { background: #c95757; }
.bars i.on[data-lvl="2"] { background: #d9963c; }
.bars i.on[data-lvl="3"] { background: #7ca85c; }
.bars i.on[data-lvl="4"], .bars i.on[data-lvl="5"] { background: #2e9e63; }
.meter span { font-family: system-ui; font-size: 11px; color: #999; width: 62px;
              text-align: right; }
.consent { border: 0; padding: 0; margin: 4px 0 16px; text-align: left; }
.check { display: flex; gap: 10px; align-items: flex-start;
         font-family: system-ui; font-size: 12.5px; line-height: 1.55;
         color: #556; margin-bottom: 12px; cursor: pointer;
         letter-spacing: normal; text-transform: none; }
.check input { width: 16px; height: 16px; margin: 2px 0 0; flex-shrink: 0;
               cursor: pointer; }
.check a { color: #4a7fb5; text-decoration: underline; }
.check em { display: block; color: #99a; font-style: normal; font-size: 11.5px; }
.error { background: #fdeeee; border: 1px solid #f0cfcf; color: #a33;
         padding: 10px 12px; border-radius: 8px; font-size: 13px;
         font-family: system-ui; margin: 0 0 14px; text-align: left; }
.go { width: 100%; padding: 13px; border: 0; background: #111; color: #fff;
      border-radius: 8px; font-family: system-ui; font-weight: 600;
      font-size: 15px; cursor: pointer; }
.go:disabled { opacity: .5; }
.note { font-family: system-ui; font-size: 12px; color: #aaa; margin: 16px 0 0;
        line-height: 1.55; }
.alt { font-family: system-ui; font-size: 13px; margin: 18px 0 0; }
.alt a { color: #4a7fb5; }
</style>
