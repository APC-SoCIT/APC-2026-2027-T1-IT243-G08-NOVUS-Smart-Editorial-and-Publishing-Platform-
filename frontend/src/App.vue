<script setup>
import CookieNotice from './components/CookieNotice.vue'
import ConfirmHost from './components/ConfirmHost.vue'
</script>

<template>
  <router-view />
  <CookieNotice />
  <ConfirmHost />
</template>
