<script setup>
/* An empty state should teach, not just report absence. It says what belongs
   here, why it is not here yet, and what to do about it. */
defineProps({
  icon: { type: String, default: '○' },
  title: { type: String, required: true },
  body: { type: String, default: '' },
})
</script>

<template>
  <div class="empty">
    <span class="icon" aria-hidden="true">{{ icon }}</span>
    <h4>{{ title }}</h4>
    <p v-if="body">{{ body }}</p>
    <div v-if="$slots.action" class="action"><slot name="action" /></div>
  </div>
</template>

<style scoped>
.empty { text-align: center; padding: var(--s-8) var(--s-5);
         border: 1px dashed var(--nv-line-strong); border-radius: var(--r-md);
         background: var(--nv-surface); }
.icon { display: inline-flex; align-items: center; justify-content: center;
        width: 44px; height: 44px; border-radius: 50%;
        background: var(--nv-bg); color: var(--nv-text-faint);
        font-size: var(--t-lg); margin-bottom: var(--s-4); }
h4 { font-size: var(--t-base); margin: 0 0 var(--s-2); color: var(--nv-text); }
p { font-size: var(--t-sm); color: var(--nv-text-muted); margin: 0 auto;
    max-width: 44ch; line-height: var(--lh-body); }
.action { margin-top: var(--s-5); }
</style>
