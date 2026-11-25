<script setup>
/* Renders the app-wide confirmation asked for with confirm() from
   composables/useConfirm.js. Mounted once, in App.vue. */
import ConfirmDialog from './ConfirmDialog.vue'
import { confirmState as s, answer } from '../composables/useConfirm'
</script>

<template>
  <ConfirmDialog :open="s.open" :title="s.title" :message="s.message"
                 :points="s.points" :confirm-label="s.confirmLabel" :tone="s.tone"
                 :require-text="s.requireText"
                 @confirm="answer(true)" @cancel="answer(false)" />
</template>
