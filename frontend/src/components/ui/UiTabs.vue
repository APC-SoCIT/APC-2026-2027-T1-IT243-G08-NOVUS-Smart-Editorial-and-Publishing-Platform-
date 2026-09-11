<script setup>
/* Tabs with counts. The count is the point — it tells you where the work is
   before you click, which a plain label cannot. Arrow keys move between tabs,
   as the WAI-ARIA tabs pattern expects. */
const props = defineProps({
  tabs: { type: Array, required: true },   // [{ key, label, count }]
  modelValue: { type: String, required: true },
})
const emit = defineEmits(['update:modelValue'])

function onKey(e, i) {
  const n = props.tabs.length
  let next = null
  if (e.key === 'ArrowRight') next = (i + 1) % n
  if (e.key === 'ArrowLeft') next = (i - 1 + n) % n
  if (e.key === 'Home') next = 0
  if (e.key === 'End') next = n - 1
  if (next === null) return
  e.preventDefault()
  emit('update:modelValue', props.tabs[next].key)
  document.getElementById(`tab-${props.tabs[next].key}`)?.focus()
}
</script>

<template>
  <div class="tabs" role="tablist">
    <button v-for="(t, i) in tabs" :key="t.key" :id="`tab-${t.key}`"
            role="tab" :aria-selected="modelValue === t.key"
            :tabindex="modelValue === t.key ? 0 : -1"
            :class="{ on: modelValue === t.key }"
            @click="emit('update:modelValue', t.key)"
            @keydown="onKey($event, i)">
      {{ t.label }}
      <span v-if="t.count !== undefined" class="count"
            :class="{ alert: t.alert && t.count }">{{ t.count }}</span>
    </button>
  </div>
</template>

<style scoped>
.tabs { display: flex; gap: var(--s-1); border-bottom: 1px solid var(--nv-line);
        margin-bottom: var(--s-5); overflow-x: auto; }
button { display: inline-flex; align-items: center; gap: var(--s-2);
         background: none; border: 0; border-bottom: 2px solid transparent;
         padding: var(--s-3) var(--s-4); font-size: var(--t-sm);
         color: var(--nv-text-muted); cursor: pointer; white-space: nowrap;
         transition: color var(--dur-fast) var(--ease-out),
                     border-color var(--dur-fast) var(--ease-out); }
button:hover { color: var(--nv-text); }
button.on { color: var(--nv-navy-2); border-bottom-color: var(--nv-navy-2);
            font-weight: 600; }
.count { font-size: var(--t-xs); font-weight: 600; min-width: 20px;
         padding: 1px var(--s-2); border-radius: var(--r-full);
         background: #eef0f3; color: var(--nv-text-muted); }
button.on .count { background: var(--nv-navy-2); color: #fff; }
.count.alert { background: var(--bad-bg); color: var(--bad); }
button.on .count.alert { background: var(--bad); color: #fff; }
</style>
