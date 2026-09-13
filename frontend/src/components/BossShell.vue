<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { useRoute } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const route = useRoute()
const auth = useAuthStore()
const scrolled = ref(false)
const menuOpen = ref(false)

const onScroll = () => { scrolled.value = window.scrollY > 20 }
onMounted(() => window.addEventListener('scroll', onScroll, { passive: true }))
onUnmounted(() => window.removeEventListener('scroll', onScroll))

const NAV = [
  { to: '/read', label: 'Home' },
  { to: '/issues', label: 'Magazines' },
  { to: '/read?view=all', label: 'Articles' },
  { to: '/about', label: 'About' },
]

const isOn = (to) => route.path === to.split('?')[0]
</script>

<template>
  <div class="boss">
    <a href="#main" class="skip-link">Skip to main content</a>

    <header :class="{ solid: scrolled }">
      <router-link to="/read" class="logo" aria-label="BOSS Magazine PH — home">
        <img src="/boss-logo.png" alt="BOSS Magazine PH" />
      </router-link>

      <nav aria-label="Primary">
        <router-link v-if="auth.isAuthenticated" to="/saved"
                     :class="{ on: route.path === '/saved' }">Saved</router-link>
        <router-link v-for="n in NAV" :key="n.label" :to="n.to"
                     :class="{ on: isOn(n.to) }"
                     :aria-current="isOn(n.to) ? 'page' : undefined">
          {{ n.label }}
        </router-link>
      </nav>

      <router-link to="/issues" class="cta">View Issues</router-link>

      <button class="burger" :aria-expanded="menuOpen"
              aria-controls="mobile-nav" @click="menuOpen = !menuOpen">
        <span class="sr-only">{{ menuOpen ? 'Close menu' : 'Open menu' }}</span>
        <span class="bars" aria-hidden="true"></span>
      </button>
    </header>

    <nav v-show="menuOpen" id="mobile-nav" class="mobile" aria-label="Primary">
      <router-link v-for="n in NAV" :key="n.label" :to="n.to"
                   @click="menuOpen = false">{{ n.label }}</router-link>
    </nav>

    <main id="main" tabindex="-1">
      <slot />
    </main>

    <footer>
      <div class="fmain">
        <div class="fbrand">
          <img src="/boss-logo.png" alt="" aria-hidden="true" />
          <p>
            The Philippines' premier lifestyle and business publication,
            celebrating Filipino excellence.
          </p>
        </div>

        <nav aria-label="Footer">
          <h3>Read</h3>
          <router-link to="/read">Articles</router-link>
          <router-link to="/issues">Issues</router-link>
          <router-link to="/about">About</router-link>
        </nav>

        <nav aria-label="Account">
          <h3>Account</h3>
          <router-link to="/login">Sign in</router-link>
          <router-link to="/register">Create account</router-link>
        </nav>

        <nav aria-label="Legal">
          <h3>Legal</h3>
          <router-link to="/legal/privacy">Privacy Policy</router-link>
          <router-link to="/legal/terms">Terms of Service</router-link>
          <router-link to="/legal/cookies">Cookie Policy</router-link>
          <router-link to="/legal/refunds">Refund Policy</router-link>
        </nav>
      </div>

      <div class="fbase">
        <p>© {{ new Date().getFullYear() }} BOSS Media Philippines Inc. All rights reserved.</p>
        <p class="built">Powered by NOVUS</p>
      </div>
    </footer>
  </div>
</template>

<style scoped>
.boss { background: var(--boss-bg); color: var(--boss-text); min-height: 100vh;
        display: flex; flex-direction: column; }

header { position: sticky; top: 0; z-index: 40; display: flex; align-items: center;
         gap: var(--s-6); padding: var(--s-4) var(--s-7);
         border-bottom: 1px solid transparent;
         transition: background var(--dur-base) var(--ease-out),
                     border-color var(--dur-base) var(--ease-out); }
header.solid { background: rgba(10,10,10,.92); backdrop-filter: blur(10px);
               border-bottom-color: var(--boss-line); }

.logo img { height: 46px; width: auto; }

header nav { display: flex; gap: var(--s-6); flex: 1; justify-content: center; }
header nav a { font-size: var(--t-xs); letter-spacing: var(--track-caps);
               text-transform: uppercase; color: var(--boss-text-muted);
               padding: var(--s-2) 0; position: relative;
               transition: color var(--dur-fast) var(--ease-out); }
header nav a:hover { color: var(--boss-text); }
header nav a.on { color: var(--boss-gold); }
header nav a.on::after { content: ''; position: absolute; left: 0; right: 0;
                         bottom: 0; height: 1px; background: var(--boss-gold); }

.cta { border: 1px solid var(--boss-gold); color: var(--boss-gold);
       padding: var(--s-3) var(--s-5); font-size: var(--t-xs);
       letter-spacing: var(--track-caps); text-transform: uppercase;
       transition: background var(--dur-base) var(--ease-out),
                   color var(--dur-base) var(--ease-out); }
.cta:hover { background: var(--boss-gold); color: var(--boss-bg); }

.burger { display: none; background: none; border: 0; cursor: pointer;
          padding: var(--s-2); }
.bars, .bars::before, .bars::after { display: block; width: 22px; height: 1.5px;
                                     background: var(--boss-text); }
.bars::before, .bars::after { content: ''; position: relative; }
.bars::before { top: -6px; } .bars::after { top: 4.5px; }

.mobile { display: none; flex-direction: column; padding: var(--s-4) var(--s-7);
          border-bottom: 1px solid var(--boss-line); background: var(--boss-surface); }
.mobile a { padding: var(--s-3) 0; font-size: var(--t-sm);
            letter-spacing: var(--track-caps); text-transform: uppercase;
            color: var(--boss-text-muted); }

main { flex: 1; }
main:focus { outline: none; }

footer { border-top: 1px solid var(--boss-line); margin-top: var(--s-9);
         padding: var(--s-8) var(--s-7) var(--s-6); background: var(--boss-surface); }
.fmain { max-width: 1100px; margin: 0 auto; display: grid;
         grid-template-columns: 2fr 1fr 1fr 1fr; gap: var(--s-7); }
.fbrand img { height: 40px; margin-bottom: var(--s-4); }
.fbrand p { color: var(--boss-text-muted); font-size: var(--t-sm);
            line-height: var(--lh-body); max-width: 300px; margin: 0; }
footer nav { display: flex; flex-direction: column; gap: var(--s-3); }
footer h3 { font-size: var(--t-xs); letter-spacing: var(--track-caps);
            text-transform: uppercase; color: var(--boss-gold); margin: 0 0 var(--s-1); }
footer nav a { font-size: var(--t-sm); color: var(--boss-text-muted);
               transition: color var(--dur-fast) var(--ease-out); }
footer nav a:hover { color: var(--boss-text); }

.fbase { max-width: 1100px; margin: var(--s-7) auto 0; padding-top: var(--s-5);
         border-top: 1px solid var(--boss-line); display: flex;
         justify-content: space-between; }
.fbase p { margin: 0; font-size: var(--t-xs); color: var(--boss-text-faint); }
.built { letter-spacing: var(--track-caps); text-transform: uppercase; }

@media (max-width: 900px) {
  header { padding: var(--s-3) var(--s-4); gap: var(--s-4); }
  header nav, .cta { display: none; }
  .burger { display: block; margin-left: auto; }
  .mobile { display: flex; }
  .fmain { grid-template-columns: 1fr 1fr; gap: var(--s-6); }
  .fbase { flex-direction: column; gap: var(--s-2); }
}
</style>
