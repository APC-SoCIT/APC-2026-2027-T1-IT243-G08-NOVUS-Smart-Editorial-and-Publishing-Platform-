<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import CookieNotice from './components/CookieNotice.vue'
import ConfirmHost from './components/ConfirmHost.vue'
import { useAuthStore } from './stores/auth'
 
const route = useRoute()
const auth = useAuthStore()
 
/* The storage notice is for the public magazine. Staff work in the
   workspace under the platform's staff terms, so it never shows there:
   not on workspace pages, the staff sign-in, or a staff member's own
   account pages. */
const showCookieNotice = computed(() => {
  if (route.meta.roles || route.meta.staff || route.path.startsWith('/staff')) return false
  const isStaff = !!auth.role && auth.role !== 'READER'
  return !(isStaff && ['/account', '/change-password'].includes(route.path))
})
</script>
 
<template>
<router-view />
<CookieNotice v-if="showCookieNotice" />
<ConfirmHost />
</template>
