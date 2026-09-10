<script setup>
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const email = ref('')
const password = ref('')
const showPassword = ref(false)
const capsOn = ref(false)
const error = ref('')
const loading = ref(false)
const attempts = ref(0)

const auth = useAuthStore()
const router = useRouter()

const DEST = {
  WRITER: '/writer',
  EDITOR: '/editor',
  PUBLISHER: '/publisher',
  GRAPHIC_DESIGNER: '/designer',
  ADMIN: '/editor',
}

const emailValid = computed(() =>
  !email.value || /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.value))

// After repeated failures the server rate-limits. Saying so is more useful
// than letting the user keep guessing into a wall.
const throttled = computed(() => attempts.value >= 5)

function checkCaps(e) {
  capsOn.value = e.getModifierState && e.getModifierState('CapsLock')
}

async function submit() {
  if (loading.value || throttled.value) return
  error.value = ''

  if (!email.value || !password.value) {
    error.value = 'Enter your email address and password.'
    return
  }
  if (!emailValid.value) {
    error.value = 'That email address does not look right.'
    return
  }

  loading.value = true
  try {
    await auth.login(email.value, password.value)

    if (auth.role === 'READER') {
      auth.logout()
      error.value = 'This is the editorial login. Readers sign in on the public site.'
      return
    }
    router.push(DEST[auth.role] || '/writer')
  } catch (e) {
    attempts.value++
    const status = e.response?.status
    if (status === 429) {
      error.value = 'Too many attempts. Wait a moment before trying again.'
    } else {
      // Deliberately does not say which field was wrong.
      error.value = 'Those credentials were not recognised.'
    }
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="shell">
    <aside>
      <div class="brandblock">
        <div class="mark">N</div>
        <h1>NOVUS</h1>
        <p class="tag">Smart Editorial &amp; Publishing Platform</p>
      </div>
      <div class="foot">
        <p class="client">BOSS Media Philippines Inc.</p>
        <p class="copy">© NOVUS 2026 · All rights reserved</p>
      </div>
    </aside>

    <main>
      <div class="form">
        <span class="eyebrow">Editorial workspace</span>
        <h2>Sign in</h2>
        <p class="sub">Use the account issued to you by your editor.</p>

        <label :class="{ bad: !emailValid }">
          EMAIL ADDRESS
          <input id="staff-email" v-model.trim="email" type="email"
                 autocomplete="username" required
                 :disabled="throttled" placeholder="you@bossmedia.ph"
                 :aria-invalid="!emailValid"
                 aria-describedby="email-note"
                 @keyup.enter="submit" />
        </label>
        <p v-if="!emailValid" id="email-note" class="fieldnote">
          Check the format of your email address.
        </p>

        <label>
          PASSWORD
          <div class="pw">
            <input id="staff-password" v-model="password"
                   :type="showPassword ? 'text' : 'password'"
                   autocomplete="current-password" required :disabled="throttled"
                   aria-describedby="caps-note"
                   @keyup="checkCaps" @keydown="checkCaps" @keyup.enter="submit" />
            <button type="button" class="peek" :disabled="throttled"
                    :aria-pressed="showPassword"
                    :aria-label="showPassword ? 'Hide password' : 'Show password'"
                    @click="showPassword = !showPassword">
              <span aria-hidden="true">{{ showPassword ? 'Hide' : 'Show' }}</span>
            </button>
          </div>
        </label>
        <p v-if="capsOn" id="caps-note" class="fieldnote warn" role="status">
          Caps Lock is on.
        </p>

        <p v-if="error" class="error" role="alert">{{ error }}</p>

        <button class="signin" :disabled="loading || throttled" @click="submit">
          {{ loading ? 'Verifying…' : 'Sign in' }}
        </button>

        <p v-if="attempts >= 3 && !throttled" class="attempts" role="status">
          {{ 5 - attempts }} attempts remaining before this account is locked.
        </p>

        <div class="security">
          <span class="lock">🔒</span>
          <p>
            Sessions are secured with signed tokens and expire automatically.
            Never share your credentials — NOVUS staff will never ask for them.
          </p>
        </div>

        <p class="alt">
          Reader?
          <router-link to="/login">Sign in to the public site</router-link>
        </p>
      </div>
    </main>
  </div>
</template>

<style scoped>
.shell { display: flex; min-height: 100vh; font-family: system-ui; }

aside { width: 42%; background: linear-gradient(160deg, #0d1526 0%, #1a2744 100%);
        color: #fff; padding: 54px 48px; display: flex; flex-direction: column;
        justify-content: space-between; }
.mark { width: 52px; height: 52px; border: 2px solid rgba(255,255,255,.85);
        border-radius: 12px; display: flex; align-items: center;
        justify-content: center; font-size: 26px; font-weight: 700;
        letter-spacing: 1px; margin-bottom: 26px; }
aside h1 { font-size: 46px; letter-spacing: 7px; margin: 0 0 10px; font-weight: 700; }
.tag { color: #9fb0cc; font-size: 15px; margin: 0; letter-spacing: .3px; }
.client { color: #cdd8e8; font-size: 13px; margin: 0 0 5px; }
.copy { color: #5e6f8c; font-size: 12px; margin: 0; }

main { flex: 1; display: flex; align-items: center; justify-content: center; padding: 40px; }
.form { width: 100%; max-width: 380px; }
.eyebrow { font-size: 11px; letter-spacing: 1.6px; text-transform: uppercase;
           color: #8a97a8; }
h2 { font-size: 30px; margin: 10px 0 6px; }
.sub { color: #778; font-size: 14px; margin: 0 0 28px; }

label { display: block; font-size: 11px; letter-spacing: .6px; color: #667;
        margin-bottom: 16px; }
label.bad { color: #b53b3b; }
input { width: 100%; margin-top: 7px; padding: 12px 14px; border: 1px solid #d3d9e0;
        border-radius: 8px; font-size: 15px; font-family: inherit;
        transition: border-color .15s, box-shadow .15s; }
input:focus { outline: none; border-color: #4a7fb5;
              box-shadow: 0 0 0 3px rgba(74,127,181,.14); }
input:disabled { background: #f4f5f7; }
.pw { position: relative; }
.peek { position: absolute; right: 6px; top: 50%; transform: translateY(-25%);
        border: 0; background: none; color: #4a7fb5; font-size: 12px;
        cursor: pointer; padding: 6px 9px; }

.fieldnote { margin: -10px 0 14px; font-size: 12px; color: #b53b3b; }
.fieldnote.warn { color: #96631a; }

.error { background: #fdeeee; border: 1px solid #f0cfcf; color: #a33;
         padding: 11px 13px; border-radius: 8px; font-size: 13px; margin: 0 0 16px; }

.signin { width: 100%; padding: 13px; border: 0; border-radius: 8px;
          background: #1a2744; color: #fff; font-size: 15px; font-weight: 600;
          cursor: pointer; transition: background .15s; }
.signin:hover:not(:disabled) { background: #24365e; }
.signin:disabled { opacity: .5; cursor: not-allowed; }

.attempts { margin: 12px 0 0; font-size: 12px; color: #96631a; text-align: center; }

.security { display: flex; gap: 11px; margin-top: 30px; padding-top: 22px;
            border-top: 1px solid #eef0f3; }
.lock { font-size: 14px; }
.security p { margin: 0; font-size: 12px; line-height: 1.6; color: #8a97a8; }

.alt { margin-top: 22px; font-size: 13px; color: #778; text-align: center; }
.alt a { color: #4a7fb5; }

@media (max-width: 820px) {
  .shell { flex-direction: column; }
  aside { width: auto; padding: 34px 28px; }
  aside h1 { font-size: 34px; }
  .foot { display: none; }
}
</style>
