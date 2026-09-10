<script setup>
defineProps({
  title: { type: String, default: '' },
  caption: { type: String, default: '' },
  padded: { type: Boolean, default: true },
  interactive: { type: Boolean, default: false },
})
</script>

<template>
  <section :class="['card', { padded, interactive }]">
    <header v-if="title || $slots.action" class="head">
      <div>
        <h3 v-if="title">{{ title }}</h3>
        <p v-if="caption">{{ caption }}</p>
      </div>
      <slot name="action" />
    </header>
    <slot />
  </section>
</template>

<style scoped>
.card { background: var(--nv-surface); border: 1px solid var(--nv-line);
        border-radius: var(--r-md); margin-bottom: var(--s-4); }
.padded { padding: var(--s-5); }
.interactive { cursor: pointer;
               transition: border-color var(--dur-fast) var(--ease-out),
                           box-shadow var(--dur-fast) var(--ease-out); }
.interactive:hover { border-color: var(--nv-line-strong); box-shadow: var(--shadow-sm); }

.head { display: flex; justify-content: space-between; align-items: flex-start;
        gap: var(--s-4); margin-bottom: var(--s-4); }
h3 { font-size: var(--t-base); font-weight: 600; margin: 0; color: var(--nv-text); }
.head p { font-size: var(--t-xs); color: var(--nv-text-faint); margin: var(--s-1) 0 0;
          line-height: var(--lh-snug); }
</style>
