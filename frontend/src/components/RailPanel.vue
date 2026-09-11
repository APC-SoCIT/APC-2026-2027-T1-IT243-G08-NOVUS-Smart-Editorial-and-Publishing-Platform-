<script setup>
defineProps({
  title: { type: String, required: true },
})
</script>

<template>
  <section class="panel">
    <h3>{{ title }}</h3>
    <slot />
  </section>
</template>

<style scoped>
.panel { background: var(--nv-surface); border: 1px solid var(--nv-line);
         border-radius: var(--r-md); padding: var(--s-4); }
h3 { font-size: var(--t-xs); letter-spacing: var(--track-caps);
     text-transform: uppercase; color: var(--nv-text-faint);
     margin: 0 0 var(--s-3); font-weight: 600; }
</style>
