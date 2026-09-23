<script setup>
import { computed } from 'vue'

const props = defineProps({
  evaluation: { type: Object, default: null },
  busy: { type: String, default: null },
  canEdit: { type: Boolean, default: false },
  error: { type: String, default: '' },
})
const emit = defineEmits(['decide'])

const fixes = computed(() => props.evaluation?.fixes || [])
const show = computed(() => props.evaluation?.verdict === 'REVISE' && fixes.value.length)
const resolved = computed(() => fixes.value.filter(f => f.state !== 'pending').length)
const LABEL = { accepted: 'Applied', dismissed: 'Dismissed', stale: 'No longer applies' }
</script>

<template>
  <section v-if="show" class="qf" aria-labelledby="qf-h">
    <header>
      <h2 id="qf-h">Quick fixes</h2>
      <span class="count">{{ resolved }} of {{ fixes.length }} resolved</span>
    </header>
    <p class="note">
      Line edits for mechanical problems. They don't change your score —
      it's measured again when you resubmit.
    </p>
    <p v-if="error" class="err" role="alert">{{ error }}</p>

    <ul>
      <li v-for="f in fixes" :key="f.id" :class="'s-' + f.state">
        <p class="diff">
          <del>{{ f.original }}</del>
          <span aria-hidden="true">→</span>
          <ins>{{ f.replacement }}</ins>
        </p>
        <p v-if="f.reason" class="why">{{ f.reason }}</p>

        <div v-if="f.state === 'pending'" class="acts">
          <button class="apply" :disabled="!canEdit || !!busy"
                  @click="emit('decide', f, 'apply')">
            {{ busy === f.id ? 'Applying…' : 'Apply' }}
          </button>
          <button class="dismiss" :disabled="!canEdit || !!busy"
                  @click="emit('decide', f, 'dismiss')">Dismiss</button>
        </div>
        <span v-else class="state">{{ LABEL[f.state] }}</span>
      </li>
    </ul>
  </section>
</template>

<style scoped>
.qf { background: var(--nv-surface); border: 1px solid var(--nv-line);
      border-radius: var(--r-md); padding: var(--s-4); }
header { display: flex; align-items: baseline; justify-content: space-between; gap: 8px; }
h2 { margin: 0; font-size: 14px; color: var(--nv-text); }
.count { font-size: 12px; color: var(--nv-text-muted); font-variant-numeric: tabular-nums; }
.note { margin: 6px 0 var(--s-3); font-size: 12.5px; line-height: 1.5;
        color: var(--nv-text-faint); }
.err { margin: 0 0 var(--s-3); font-size: 13px; color: var(--bad); }
ul { list-style: none; margin: 0; padding: 0; display: grid; gap: var(--s-2); }
li { border: 1px solid var(--nv-line); border-radius: var(--r-sm); padding: 10px 12px;
     background: var(--nv-bg); }
li.s-accepted, li.s-dismissed, li.s-stale { opacity: .7; }
.diff { margin: 0; font-size: 13.5px; line-height: 1.55; color: var(--nv-text); }
del { color: var(--bad); background: var(--bad-bg); text-decoration: line-through;
      padding: 0 2px; border-radius: 3px; }
ins { color: var(--ok); background: var(--ok-bg); text-decoration: none;
      padding: 0 2px; border-radius: 3px; }
.diff span { margin: 0 6px; color: var(--nv-text-faint); }
.why { margin: 4px 0 0; font-size: 12.5px; color: var(--nv-text-muted); }
.acts { display: flex; gap: 8px; margin-top: 8px; }
.acts button { font: inherit; font-size: 12.5px; padding: 5px 12px; cursor: pointer;
               border-radius: var(--r-sm); }
.apply { border: 0; background: var(--nv-navy-2); color: #fff; font-weight: 600; }
.dismiss { border: 1px solid var(--nv-line-strong); background: var(--nv-surface);
           color: var(--nv-text); }
.acts button:disabled { opacity: .5; cursor: not-allowed; }
.state { display: inline-block; margin-top: 8px; font-size: 12px;
         color: var(--nv-text-muted); }
.s-accepted .state { color: var(--ok); }
</style>
