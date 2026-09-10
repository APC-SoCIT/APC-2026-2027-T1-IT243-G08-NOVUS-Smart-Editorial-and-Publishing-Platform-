<script setup>
/* A shape-matched placeholder reads as "content is coming" far better than the
   word "Loading". Marked aria-hidden with a live status alongside, so screen
   readers hear one clear message instead of a wall of empty boxes. */
defineProps({
  rows: { type: Number, default: 3 },
  variant: { type: String, default: 'list' },   // list | card | stat
  label: { type: String, default: 'Loading' },
})
</script>

<template>
  <div class="wrap">
    <p class="sr-only" role="status">{{ label }}</p>

    <div v-if="variant === 'stat'" class="stats" aria-hidden="true">
      <div v-for="n in rows" :key="n" class="stat sh"></div>
    </div>

    <div v-else-if="variant === 'card'" class="cards" aria-hidden="true">
      <div v-for="n in rows" :key="n" class="card">
        <div class="thumb sh"></div>
        <div class="line sh w60"></div>
        <div class="line sh w90"></div>
      </div>
    </div>

    <div v-else class="rows" aria-hidden="true">
      <div v-for="n in rows" :key="n" class="row">
        <div class="line sh w40"></div>
        <div class="line sh w70 sm"></div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.sh { background: linear-gradient(90deg, #eef0f3 25%, #f6f7f9 50%, #eef0f3 75%);
      background-size: 200% 100%; animation: shimmer 1.4s infinite;
      border-radius: var(--r-sm); }
@keyframes shimmer { to { background-position: -200% 0; } }

.stats { display: flex; gap: var(--s-3); }
.stat { flex: 1; height: 82px; }

.cards { display: grid; grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
         gap: var(--s-5); }
.thumb { height: 120px; margin-bottom: var(--s-3); }

.rows { display: flex; flex-direction: column; gap: var(--s-3); }
.row { border: 1px solid var(--nv-line); border-radius: var(--r-md);
       padding: var(--s-4); }
.line { height: 12px; margin-bottom: var(--s-2); }
.line.sm { height: 9px; }
.w40 { width: 40%; } .w60 { width: 60%; } .w70 { width: 70%; } .w90 { width: 90%; }
</style>
