<script setup>
import { ref, onMounted, watch } from 'vue'
import api from '../services/api'
import UiButton from './ui/UiButton.vue'

const props = defineProps({
  article: { type: Object, required: true },
})
const emit = defineEmits(['changed'])

const issues = ref([])
const selected = ref(props.article.issue ?? '')
const premium = ref(props.article.is_premium)
const busy = ref(false)
const saved = ref('')
const error = ref('')

onMounted(async () => {
  const { data } = await api.get('/publication/issues/')
  issues.value = (data.results ?? data)
    .filter(i => !['PUBLISHED', 'ARCHIVED'].includes(i.status))
})

watch(() => props.article, (a) => {
  selected.value = a.issue ?? ''
  premium.value = a.is_premium
})

async function saveIssue() {
  error.value = ''; saved.value = ''
  busy.value = true
  try {
    const { data } = await api.post(
      `/editorial/articles/${props.article.id}/assign-issue/`,
      { issue: selected.value || null })
    // Assignment sets premium server-side; reflect that rather than
    // leaving the toggle showing a stale value.
    premium.value = data.is_premium
    saved.value = selected.value ? 'Assigned to the issue.' : 'Now a standalone article.'
    emit('changed')
  } catch (e) {
    error.value = e.response?.data?.detail || 'Could not assign.'
  } finally { busy.value = false }
}

async function saveAccess(value) {
  error.value = ''; saved.value = ''
  premium.value = value
  busy.value = true
  try {
    await api.post(`/editorial/articles/${props.article.id}/set-access/`,
                   { is_premium: value })
    saved.value = value ? 'Subscribers only.' : 'Free to read.'
    emit('changed')
  } catch (e) {
    error.value = 'Could not change access.'
    premium.value = !value
  } finally { busy.value = false }
}
</script>

<template>
  <section class="pub">
    <h5>Publishing</h5>

    <!-- issue -->
    <div class="field">
      <label for="issue-select">ISSUE</label>
      <div class="row">
        <select id="issue-select" v-model="selected" :disabled="busy">
          <option value="">Not in an issue — publishes on its own</option>
          <option v-for="i in issues" :key="i.id" :value="i.id">
            Issue {{ i.number }} — {{ i.title }}
          </option>
        </select>
        <UiButton size="sm" :loading="busy" @click="saveIssue">Save</UiButton>
      </div>
      <p class="hint">
        An article in an issue publishes with that issue. Left unassigned, the
        publisher can release it on its own.
      </p>
    </div>

    <!-- access -->
    <div class="field">
      <label id="access-label">READER ACCESS</label>
      <div class="choices" role="radiogroup" aria-labelledby="access-label">
        <button role="radio" :aria-checked="!premium" :class="{ on: !premium }"
                :disabled="busy" @click="saveAccess(false)">
          <b>Free</b>
          <span>Anyone can read it. Draws readers to the magazine.</span>
        </button>
        <button role="radio" :aria-checked="premium" :class="{ on: premium }"
                :disabled="busy" @click="saveAccess(true)">
          <b>Subscribers</b>
          <span>An extract shows, then the paywall.</span>
        </button>
      </div>
      <p class="hint">
        Assigning an article to an issue makes it subscriber-only by default,
        since the issue is the paid product. Override it here.
      </p>
    </div>

    <p v-if="error" class="err" role="alert">{{ error }}</p>
    <p v-if="saved" class="ok" role="status">{{ saved }}</p>
  </section>
</template>

<style scoped>
.pub { border: 1px solid var(--nv-line); border-radius: var(--r-md);
       padding: var(--s-5); margin-top: var(--s-5);
       background: var(--nv-surface); }
h5 { margin: 0 0 var(--s-4); font-size: 13px; letter-spacing: .05em;
     text-transform: uppercase; color: var(--nv-text-muted); font-weight: 600; }

.field { margin-bottom: var(--s-5); }
.field:last-of-type { margin-bottom: 0; }
label { display: block; font-size: 12px; letter-spacing: .04em;
        color: var(--nv-text-muted); margin-bottom: 6px; }
.row { display: flex; gap: 8px; }
select { flex: 1; padding: 10px 12px; font-size: 14px; font-family: inherit;
         border: 1px solid var(--nv-line-strong); border-radius: var(--r-sm);
         background: var(--nv-surface); color: var(--nv-text); }

.choices { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
.choices button { text-align: left; padding: 12px 14px; cursor: pointer;
                  background: var(--nv-surface); color: var(--nv-text);
                  border: 1px solid var(--nv-line-strong);
                  border-radius: var(--r-sm); font-family: inherit;
                  transition: border-color var(--dur-fast) var(--ease-out),
                              background var(--dur-fast) var(--ease-out); }
.choices button:hover:not(:disabled) { border-color: var(--nv-accent); }
.choices button.on { border-color: var(--nv-navy-2); background: var(--nv-accent-soft); }
.choices b { display: block; font-size: 14px; margin-bottom: 3px; }
.choices span { font-size: 12px; color: var(--nv-text-muted); line-height: 1.45; }
.choices button:disabled { opacity: .6; cursor: not-allowed; }

.hint { margin: 8px 0 0; font-size: 12.5px; line-height: 1.55;
        color: var(--nv-text-faint); }
.err { color: var(--bad); font-size: 13px; margin: var(--s-3) 0 0; }
.ok { color: var(--ok); font-size: 13px; margin: var(--s-3) 0 0; }
</style>
