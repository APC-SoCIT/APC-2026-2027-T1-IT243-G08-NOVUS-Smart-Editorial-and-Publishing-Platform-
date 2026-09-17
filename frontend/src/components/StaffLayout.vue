<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import NotificationBell from './NotificationBell.vue'
import ThemeToggle from './ThemeToggle.vue'

const props = defineProps({
  title: { type: String, default: '' },
  subtitle: { type: String, default: '' },
})

const auth = useAuthStore()
const route = useRoute()
const router = useRouter()

// Nav is role-scoped: each role sees only what it can act on.
const NAV = {
  WRITER: [
    { to: '/writer', label: 'Dashboard' },
    { to: '/calendar', label: 'Calendar' },
    { to: '/archive', label: 'Archive' },
  ],
  EDITOR: [
    { to: '/editor', label: 'Dashboard' },
    { to: '/calendar', label: 'Calendar' },
    { to: '/issues-overview', label: 'Issues' },
    { to: '/archive', label: 'Archive' },
    { to: '/reports', label: 'Reports' },
  ],
  PUBLISHER: [
    { to: '/publisher', label: 'Pipeline' },
    { to: '/calendar', label: 'Calendar' },
    { to: '/archive', label: 'Archive' },
    { to: '/reports', label: 'Reports' },
  ],
  GRAPHIC_DESIGNER: [
    { to: '/designer', label: 'Workspace' },
    { to: '/issues-overview', label: 'Issues' },
    { to: '/archive', label: 'Archive' },
  ],
  // An administrator holds every role's authority, so their navigation
  // carries every destination rather than a subset.
  ADMIN: [
    { to: '/editor', label: 'Editorial' },
    { to: '/publisher', label: 'Publishing' },
    { to: '/calendar', label: 'Calendar' },
    { to: '/issues-overview', label: 'Issues' },
    { to: '/archive', label: 'Archive' },
    { to: '/reports', label: 'Reports' },
    { to: '/settings', label: 'Settings' },
  ],
}

const nav = computed(() => NAV[auth.role] || [])

/* The brand mark returns to the workspace, not to the public site. A logo
   that navigates out of the product someone is working in is disorienting —
   the reader portal is a different application wearing a different name. */
const home = computed(() => nav.value[0]?.to || '/writer')

const roleLabel = computed(() =>
  (auth.role || '').replace('_', ' ').toLowerCase())

const initials = computed(() => {
  const u = auth.user
  if (!u) return '?'
  return ((u.first_name?.[0] || '') + (u.last_name?.[0] || '')).toUpperCase() || '?'
})

/* Vue Router applies active-class itself and keeps it in sync through
   navigation; this is only used for aria-current, where a stale value is
   harmless but a missing one is not. */
const isActive = (to) =>
  to === route.path || (to !== '/' && route.path.startsWith(to + '/'))

function signOut() {
  auth.logout()
  router.push('/staff/login')
}
</script>

<template>
  <div class="shell">
    <aside>
      <router-link :to="home" class="brand" aria-label="NOVUS workspace home">
        <span class="mark">N</span>
        <span class="word">NOVUS</span>
      </router-link>

      <nav>
        <router-link v-for="n in nav" :key="n.to" :to="n.to"
                     active-class="on" exact-active-class="on"
                     :aria-current="isActive(n.to) ? 'page' : undefined">
          {{ n.label }}
        </router-link>
      </nav>

      <a href="/read" target="_blank" rel="noopener" class="viewsite">
        View public site
        <span aria-hidden="true">↗</span>
        <span class="sr-only">(opens in a new tab)</span>
      </a>

      <router-link to="/account" class="who">
        <div class="avatar">{{ initials }}</div>
        <div class="idblock">
          <b>{{ auth.user?.first_name }} {{ auth.user?.last_name }}</b>
          <span>{{ roleLabel }}</span>
        </div>
      </router-link>
    </aside>

    <div class="main">
      <header>
        <div>
          <h1>{{ title }}</h1>
          <p v-if="subtitle">{{ subtitle }}</p>
        </div>
        <div class="hactions">
          <slot name="action" />
          <NotificationBell />
          <ThemeToggle />
          <button class="out" @click="signOut">Sign out</button>
        </div>
      </header>

      <div class="content" :class="{ railed: $slots.rail }">
        <div class="main-col">
          <slot />
        </div>
        <aside v-if="$slots.rail" class="rail" aria-label="At a glance">
          <slot name="rail" />
        </aside>
      </div>
    </div>
  </div>
</template>

<style scoped>
.shell { display: flex; min-height: 100vh; font-family: var(--font-ui);
         background: var(--nv-bg); }

aside { width: 216px; background: var(--nv-navy); color: #fff; padding: 24px 0;
        display: flex; flex-direction: column; flex-shrink: 0; position: sticky;
        top: 0; height: 100vh; }
.brand { display: flex; align-items: center; gap: 10px; padding: 0 22px 26px;
         color: #fff; }
.mark { width: 32px; height: 32px; border: 1.5px solid rgba(255,255,255,.8);
        border-radius: 8px; display: flex; align-items: center;
        justify-content: center; font-weight: 700; font-size: 16px; }
.word { font-size: 18px; letter-spacing: 3px; font-weight: 700; }

nav { display: flex; flex-direction: column; gap: 2px; padding: 0 12px; flex: 1; }
nav a { display: block; padding: 10px 14px; border-radius: 7px; font-size: 14px;
        color: #9fb0cc; transition: background .15s, color .15s; }
nav a:hover { background: rgba(255,255,255,.06); color: #fff; }
nav a.on { background: rgba(255,255,255,.14); color: #fff; font-weight: 600;
           position: relative; }
/* A left marker reads faster than a background tint alone, especially
   against a dark sidebar where the tint is necessarily subtle. */
nav a.on::before { content: ''; position: absolute; left: 0; top: 8px;
                   bottom: 8px; width: 3px; border-radius: 0 2px 2px 0;
                   background: var(--nv-accent); }

.viewsite { display: flex; align-items: center; gap: 7px;
            margin: 0 12px var(--s-3); padding: 9px 14px;
            border-radius: var(--r-sm); font-size: 13px;
            color: #7f8fab; border: 1px solid rgba(255,255,255,.08);
            transition: color var(--dur-fast) var(--ease-out),
                        border-color var(--dur-fast) var(--ease-out); }
.viewsite:hover { color: #fff; border-color: rgba(255,255,255,.2); }
.who { display: flex; align-items: center; gap: 11px; cursor: pointer;
       border-radius: var(--r-sm);
       transition: background var(--dur-fast) var(--ease-out); padding: 18px 22px 0;
       margin: 0 12px; border-top: 1px solid rgba(255,255,255,.09); }
.who:hover { background: rgba(255,255,255,.06); }
.avatar { width: 34px; height: 34px; border-radius: 50%; background: #2c3e63;
          display: flex; align-items: center; justify-content: center;
          font-size: 12px; font-weight: 600; flex-shrink: 0; }
.idblock { display: flex; flex-direction: column; min-width: 0; }
.idblock b { font-size: 13px; white-space: nowrap; overflow: hidden;
             text-overflow: ellipsis; }
.idblock span { font-size: 11px; color: #6f82a3; text-transform: capitalize; }

.main { flex: 1; min-width: 0; background: var(--nv-bg); }
header { display: flex; justify-content: space-between; align-items: flex-start;
         padding: var(--s-5) var(--s-7); background: var(--nv-surface);
         border-bottom: 1px solid var(--nv-line); }
header h1 { margin: 0; font-size: 21px; letter-spacing: .3px; }
header p { margin: 4px 0 0; font-size: 13px; color: #8a97a8; }
.hactions { display: flex; gap: var(--s-3); align-items: center; }
.out { border: 1px solid var(--nv-line-strong); background: var(--nv-surface);
       color: var(--nv-text); border-radius: var(--r-sm);
       padding: 7px 14px; font-size: 13px; cursor: pointer;
       transition: border-color var(--dur-fast) var(--ease-out); }
.out:hover { background: var(--nv-bg); border-color: var(--nv-text-faint); }

.content { padding: var(--s-6) var(--s-7) var(--s-9); max-width: 1240px; }
.content.railed { display: grid; grid-template-columns: minmax(0, 1fr) 300px;
                  gap: var(--s-6); align-items: start; }
.main-col { min-width: 0; }
/* The rail scrolls with the page until it reaches the top, then holds.
   Its own background stops the shell showing through the gaps between
   panels, which read as a rendering fault rather than a design. */
.rail { position: sticky; top: var(--s-6); align-self: start;
        display: flex; flex-direction: column; gap: var(--s-3);
        background: var(--nv-bg); }

@media (max-width: 1100px) {
  .content.railed { grid-template-columns: 1fr; }
  .rail { position: static; }
}

@media (max-width: 780px) {
  .shell { flex-direction: column; }
  aside { width: auto; height: auto; position: static; flex-direction: row;
          align-items: center; padding: 14px 18px; }
  .brand { padding: 0 18px 0 0; }
  nav { flex-direction: row; padding: 0; }
  .who { border-top: 0; border-left: 1px solid rgba(255,255,255,.09);
         padding: 0 0 0 16px; margin-left: auto; }
  .idblock { display: none; }
  .content { padding: 20px; }
}
</style>
