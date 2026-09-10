<script setup>
import { computed } from 'vue'

const props = defineProps({
  /* Workflow status, or a plain tone. Status wins if given, so callers pass
     the raw value and get the right colour without a lookup table each time. */
  status: { type: String, default: '' },
  tone: { type: String, default: 'neutral' },   // neutral | ok | warn | bad | info
  dot: { type: Boolean, default: false },
})

const STATUS_TONE = {
  ASSIGNED: 'info', DRAFTING: 'neutral', AWAITING_EVALUATION: 'info',
  UNDER_REVIEW: 'info', REVISION_REQUESTED: 'warn', APPROVED: 'ok',
  PUBLISHED: 'ok', WITHDRAWN: 'bad',
  PENDING_REVIEW: 'info', REVISION: 'warn', SUPERSEDED: 'neutral',
  PLANNING: 'neutral', COMPILED: 'info', READY: 'ok',
  SCHEDULED: 'info', ARCHIVED: 'neutral',
  FREE: 'neutral', SUBSCRIBER: 'ok',
}

const resolved = computed(() =>
  props.status ? (STATUS_TONE[props.status] || 'neutral') : props.tone)

const text = computed(() =>
  props.status ? props.status.replace(/_/g, ' ').toLowerCase() : '')
</script>

<template>
  <span :class="['badge', resolved]">
    <span v-if="dot" class="dot" aria-hidden="true"></span>
    <slot>{{ text }}</slot>
  </span>
</template>

<style scoped>
.badge { display: inline-flex; align-items: center; gap: var(--s-2);
         font-size: var(--t-xs); font-weight: 600; letter-spacing: .02em;
         padding: var(--s-1) var(--s-3); border-radius: var(--r-full);
         text-transform: capitalize; white-space: nowrap;
         border: 1px solid transparent; }
.dot { width: 6px; height: 6px; border-radius: 50%; background: currentColor; }

.neutral { background: #f0f2f5; color: var(--nv-text-muted); border-color: #e4e7ec; }
.ok   { background: var(--ok-bg);   color: var(--ok);   border-color: var(--ok-line); }
.warn { background: var(--warn-bg); color: var(--warn); border-color: var(--warn-line); }
.bad  { background: var(--bad-bg);  color: var(--bad);  border-color: var(--bad-line); }
.info { background: var(--info-bg); color: var(--info); border-color: #cfe0f5; }
</style>
