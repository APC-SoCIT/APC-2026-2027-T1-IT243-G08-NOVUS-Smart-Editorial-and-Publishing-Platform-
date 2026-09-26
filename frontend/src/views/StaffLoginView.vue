<script setup>
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { ArrowRight, Clock, Eye, EyeOff, KeyRound, Lock, Mail, ShieldCheck } from 'lucide-vue-next'
import ConstellationBackground from '../components/ConstellationBackground.vue'
import NovusLogo from '../components/NovusLogo.vue'

const email = ref('')
const password = ref('')
const showPassword = ref(false)
const capsOn = ref(false)
const error = ref('')
const loading = ref(false)
const attempts = ref(0)
const year = new Date().getFullYear()

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
  <div class="login">
    <!-- Brand panel. The constellation is decoration; the logo carries the name. -->
    <section class="hero">
      <ConstellationBackground />
      <div class="brand">
        <NovusLogo class="hero-logo" />
        <p class="tagline">Smart Editorial &amp; Publishing Platform</p>
      </div>
      <p class="legal">BOSS Media Philippines Inc.<br>&copy; NOVUS {{ year }} &middot; All rights reserved</p>
    </section>

    <main class="panel">
      <form class="card" novalidate @submit.prevent="submit">
        <p class="eyebrow">Editorial workspace</p>
        <h1>Sign in</h1>
        <p class="sub">Use the account issued to you by your editor.</p>

        <p v-if="error" id="login-error" class="alert" role="alert">{{ error }}</p>

        <label for="email">Email address</label>
        <div class="field" :class="{ bad: !emailValid }">
          <Mail class="i" aria-hidden="true" />
          <input id="email" v-model.trim="email" type="email" inputmode="email"
                 autocomplete="username" placeholder="you@bossmedia.ph" autofocus
                 :aria-invalid="!emailValid"
                 :aria-describedby="error ? 'login-error' : undefined" />
        </div>

        <label for="password">Password</label>
        <div class="field">
          <Lock class="i" aria-hidden="true" />
          <input id="password" v-model="password" :type="showPassword ? 'text' : 'password'"
                 autocomplete="current-password"
                 :aria-describedby="capsOn ? 'caps' : undefined"
                 @keydown="checkCaps" @keyup="checkCaps" />
          <button type="button" class="show" :aria-pressed="showPassword"
                  @click="showPassword = !showPassword">
            <EyeOff v-if="showPassword" aria-hidden="true" />
            <Eye v-else aria-hidden="true" />
            {{ showPassword ? 'Hide' : 'Show' }}
          </button>
        </div>
        <p v-if="capsOn" id="caps" class="hint">Caps Lock is on.</p>

        <button class="submit" type="submit" :disabled="loading || throttled">
          <template v-if="loading">Signing in&hellip;</template>
          <template v-else>Sign in <ArrowRight aria-hidden="true" /></template>
        </button>
        <p v-if="throttled" class="hint">
          Sign-in is paused after several failed attempts. Refresh the page to try again later.
        </p>

        <ul class="notes">
          <li><span class="tile"><ShieldCheck aria-hidden="true" /></span>Sessions are secured with signed tokens.</li>
          <li><span class="tile"><Clock aria-hidden="true" /></span>Sessions expire automatically.</li>
          <li class="warn"><span class="tile"><KeyRound aria-hidden="true" /></span>Never share your credentials with anyone.</li>
        </ul>

        <p class="alt"><router-link to="/read">Visit BOSS Magazine &rarr;</router-link></p>
      </form>
    </main>
  </div>
</template>

<style scoped>
.login { display: grid; grid-template-columns: 1fr 1fr; min-height: 100vh; }
/* Sized from the border inward regardless of the page's global reset. */
.card, .field input, .submit, .alert { box-sizing: border-box; }

/* ---- brand panel -------------------------------------------------------- */
.hero { position: relative; overflow: hidden; color: #fff; isolation: isolate;
        background:
          radial-gradient(1100px 620px at 18% 8%, #1B2B55 0%, transparent 60%),
          radial-gradient(900px 520px at 92% 92%, #152245 0%, transparent 55%),
          #0B1430; }
.brand { position: absolute; inset: 0; display: flex; flex-direction: column;
         align-items: center; justify-content: center; gap: 22px; padding: 40px;
         pointer-events: none; }
/* A soft pool of dark behind the wordmark keeps it legible over the lines. */
.brand::before { content: ""; position: absolute; width: 520px; height: 300px;
                 background: radial-gradient(closest-side, rgba(11,20,48,.75), transparent);
                 z-index: -1; }
.hero-logo { width: min(310px, 68%);
             filter: drop-shadow(0 6px 24px rgba(120, 160, 255, .25)); }
.tagline { margin: 0; font-size: 19px; letter-spacing: .01em; color: rgba(255,255,255,.88); }
.legal { position: absolute; left: 28px; bottom: 22px; margin: 0; font-size: 12px;
         line-height: 1.6; color: rgba(255,255,255,.6); }

/* ---- form panel --------------------------------------------------------- */
.panel { display: flex; align-items: center; justify-content: center; padding: 48px 32px;
         background: var(--nv-surface, #fff); }
.card { width: 100%; max-width: 380px; }
.eyebrow { margin: 0; font-size: 11.5px; font-weight: 700; letter-spacing: .14em;
           text-transform: uppercase; color: var(--nv-text-muted, #5B6B8C); }
h1 { margin: 8px 0 6px; font-size: 30px; color: var(--nv-text, #0F1A33); }
.sub { margin: 0 0 24px; font-size: 14.5px; color: var(--nv-text-muted, #56627A); }

.alert { margin: 0 0 18px; padding: 10px 12px; border-radius: 8px; font-size: 13.5px;
         background: var(--bad-bg, #FDECEC); color: var(--bad, #B42318); }

label { display: block; margin: 0 0 7px; font-size: 11.5px; font-weight: 700;
        letter-spacing: .08em; text-transform: uppercase; color: var(--nv-text, #3C4A66); }
.field { position: relative; margin-bottom: 18px; }
.field .i { position: absolute; left: 13px; top: 50%; width: 18px; height: 18px;
            transform: translateY(-50%); color: var(--nv-text-faint, #8A96AE); pointer-events: none; }
.field input { width: 100%; height: 46px; padding: 0 76px 0 42px; border-radius: 10px;
               border: 1px solid var(--nv-line, #D5DBE7); background: var(--nv-bg, #F8FAFD);
               font: inherit; font-size: 14.5px; color: var(--nv-text, #0F1A33);
               transition: border-color .15s, box-shadow .15s, background .15s; }
.field input::placeholder { color: var(--nv-text-faint, #8A96AE); }
.field input:focus { outline: none; border-color: #3D5BA9; background: var(--nv-surface, #fff);
                     box-shadow: 0 0 0 4px rgba(61, 91, 169, .16); }
.field.bad input { border-color: var(--bad, #B42318); }
.show { position: absolute; right: 8px; top: 50%; transform: translateY(-50%);
        display: flex; align-items: center; gap: 6px; padding: 6px 8px; border: 0;
        border-radius: 6px; background: none; cursor: pointer;
        font: inherit; font-size: 13px; color: var(--nv-text-muted, #56627A); }
.show:hover { background: var(--nv-line, #EEF1F6); }
.show:focus-visible { outline: 2px solid #3D5BA9; outline-offset: 1px; }
.show svg { width: 17px; height: 17px; }
.hint { margin: -10px 0 16px; font-size: 12.5px; color: var(--warn, #B26A00); }

.submit { width: 100%; height: 48px; margin-top: 4px; border: 0; border-radius: 10px;
          display: flex; align-items: center; justify-content: center; gap: 10px;
          background: #0F1A33; color: #fff; cursor: pointer;
          font: inherit; font-size: 15px; font-weight: 600;
          box-shadow: 0 8px 20px rgba(15, 26, 51, .18);
          transition: transform .12s, box-shadow .12s, background .12s; }
.submit:hover:not(:disabled) { background: #16244A; box-shadow: 0 10px 24px rgba(15,26,51,.24); }
.submit:active:not(:disabled) { transform: translateY(1px); }
.submit:focus-visible { outline: 3px solid rgba(61, 91, 169, .45); outline-offset: 2px; }
.submit:disabled { opacity: .6; cursor: not-allowed; }
.submit svg { width: 18px; height: 18px; transition: transform .15s; }
.submit:hover:not(:disabled) svg { transform: translateX(3px); }
.submit + .hint { margin: 10px 0 0; }

.notes { list-style: none; margin: 28px 0 0; padding: 20px 0 0; display: grid; gap: 12px;
         border-top: 1px solid var(--nv-line, #E6EAF2); }
.notes li { display: flex; align-items: center; gap: 12px; font-size: 13.5px;
            color: var(--nv-text-muted, #3C4A66); }
.tile { flex: 0 0 32px; height: 32px; border-radius: 9px; display: grid; place-items: center;
        background: rgba(61, 91, 169, .1); color: #3D5BA9; }
.tile svg { width: 17px; height: 17px; }
.notes li.warn .tile { background: rgba(178, 106, 0, .12); color: #B26A00; }

.alt { margin: 26px 0 0; text-align: center; font-size: 13.5px; color: var(--nv-text-muted, #56627A); }
.alt a { color: #3D5BA9; font-weight: 600; text-decoration: none; }
.alt a:hover { text-decoration: underline; }

/* ---- small screens: the brand panel becomes a band above the form ------- */
@media (max-width: 900px) {
  .login { grid-template-columns: 1fr; }
  .hero { min-height: 220px; }
  .hero-logo { width: min(220px, 60%); }
  .tagline { font-size: 15px; }
  .legal { display: none; }
  .panel { padding: 32px 20px 40px; }
}
</style>
