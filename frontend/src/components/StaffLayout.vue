<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import NotificationBell from './NotificationBell.vue'

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
    { to: '/writer/compose', label: 'New submission' },
  ],
  EDITOR: [
    { to: '/editor', label: 'Dashboard' },
  ],
  PUBLISHER: [
    { to: '/publisher', label: 'Pipeline' },
  ],
  GRAPHIC_DESIGNER: [
    { to: '/designer', label: 'Workspace' },
  ],
  ADMIN: [
    { to: '/editor', label: 'Dashboard' },
  ],
}

const nav = computed(() => NAV[auth.role] || [])

const roleLabel = computed(() =>
  (auth.role || '').replace('_', ' ').toLowerCase())

const initials = computed(() => {
  const u = auth.user
  if (!u) return '?'
  return ((u.first_name?.[0] || '') + (u.last_name?.[0] || '')).toUpperCase() || '?'
})

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
      <router-link to="/read" class="brand">
        <span class="mark">N</span>
        <span class="word">NOVUS</span>
      </router-link>

      <nav>
        <router-link v-for="n in nav" :key="n.to" :to="n.to"
                     :class="{ on: isActive(n.to) }">
          {{ n.label }}
        </router-link>
      </nav>

      <div class="who">
        <div class="avatar">{{ initials }}</div>
        <div class="idblock">
          <b>{{ auth.user?.first_name }} {{ auth.user?.last_name }}</b>
          <span>{{ roleLabel }}</span>
        </div>
      </div>
    </aside>

    <div class="main">
      <header>
        <div>
          <h1>{{ title }}</h1>
          <p v-if="subtitle">{{ subtitle }}</p>
        </div>
        <div class="hactions">
          <NotificationBell />
          <button class="out" @click="signOut">Sign out</button>
        </div>
      </header>

      <div class="content">
        <slot />
      </div>
    </div>
  </div>
</template>

<style scoped>
.shell { display: flex; min-height: 100vh; font-family: system-ui;
         background: #f7f8fa; }

aside { width: 216px; background: #0d1526; color: #fff; padding: 24px 0;
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
nav a.on { background: rgba(255,255,255,.11); color: #fff; font-weight: 600; }

.who { display: flex; align-items: center; gap: 11px; padding: 18px 22px 0;
       margin: 0 12px; border-top: 1px solid rgba(255,255,255,.09); }
.avatar { width: 34px; height: 34px; border-radius: 50%; background: #2c3e63;
          display: flex; align-items: center; justify-content: center;
          font-size: 12px; font-weight: 600; flex-shrink: 0; }
.idblock { display: flex; flex-direction: column; min-width: 0; }
.idblock b { font-size: 13px; white-space: nowrap; overflow: hidden;
             text-overflow: ellipsis; }
.idblock span { font-size: 11px; color: #6f82a3; text-transform: capitalize; }

.main { flex: 1; min-width: 0; }
header { display: flex; justify-content: space-between; align-items: flex-start;
         padding: 26px 34px; background: #fff; border-bottom: 1px solid #eaecef; }
header h1 { margin: 0; font-size: 21px; letter-spacing: .3px; }
header p { margin: 4px 0 0; font-size: 13px; color: #8a97a8; }
.hactions { display: flex; gap: 10px; align-items: center; }
.out { border: 1px solid #d5dae0; background: #fff; border-radius: 7px;
       padding: 7px 14px; font-size: 13px; cursor: pointer; }
.out:hover { background: #f4f5f7; }

.content { padding: 28px 34px 70px; max-width: 940px; }

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
