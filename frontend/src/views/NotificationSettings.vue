<script setup>
import { ref, onMounted } from 'vue'
import api from '../services/api'
import StaffLayout from '../components/StaffLayout.vue'
import UiButton from '../components/ui/UiButton.vue'

const prefs = ref(null)
const loading = ref(true)
const saving = ref(false)
const saved = ref('')
const error = ref('')

/* Grouped by what a person would actually want to silence. Nobody thinks
   "mute DESIGN_UPLOADED" — they think "stop telling me about layouts". */
const GROUPS = [
  {
    label: 'Your work',
    hint: 'Things happening to articles you wrote or were assigned.',
    kinds: [
      { key: 'ASSIGNED', label: 'An article is assigned to you' },
      { key: 'REVISION', label: 'Revisions are requested on your article' },
      { key: 'RETURNED_BY_AI', label: 'Pre-screening returns your article' },
      { key: 'APPROVED', label: 'Your article is approved' },
      { key: 'PUBLISHED', label: 'Your article is published' },
    ],
  },
  {
    label: 'Deadlines',
    hint: 'Warnings before and after a deadline passes.',
    kinds: [
      { key: 'DEADLINE_NEAR', label: 'A deadline is approaching' },
      { key: 'DEADLINE_PASSED', label: 'A deadline has passed' },
    ],
  },
  {
    label: 'The desk',
    hint: 'Work arriving for you to review or act on.',
    kinds: [
      { key: 'SUBMITTED', label: 'An article is submitted for review' },
      { key: 'DESIGN_UPLOADED', label: 'A layout is submitted' },
      { key: 'DESIGN_APPROVED', label: 'A layout is approved' },
      { key: 'DESIGN_REVISION', label: 'A layout needs revision' },
    ],
  },
  {
    label: 'Conversation',
    hint: 'Messages on articles you are working on.',
    kinds: [{ key: 'MESSAGE', label: 'Someone comments on an article' }],
  },
]

onMounted(async () => {
  const { data } = await api.get('/notifications/preferences/')
  prefs.value = { ...data, muted_kinds: data.muted_kinds || [] }
  loading.value = false
})

const muted = (k) => prefs.value?.muted_kinds.includes(k)

function toggle(k) {
  const list = prefs.value.muted_kinds
  const i = list.indexOf(k)
  if (i === -1) list.push(k)
  else list.splice(i, 1)
}

async function save() {
  error.value = ''; saved.value = ''
  saving.value = true
  try {
    await api.patch('/notifications/preferences/', {
      in_app: prefs.value.in_app,
      muted_kinds: prefs.value.muted_kinds,
    })
    saved.value = 'Preferences saved.'
    setTimeout(() => (saved.value = ''), 2500)
  } catch {
    error.value = 'Could not save your preferences.'
  } finally { saving.value = false }
}
</script>

<template>
  <StaffLayout title="Notifications"
               subtitle="Choose what you are told about">

    <p v-if="loading">Loading…</p>

    <template v-else>
      <p v-if="error" class="err" role="alert">{{ error }}</p>
      <p v-if="saved" class="ok" role="status">{{ saved }}</p>

      <section class="card">
        <label class="master">
          <input type="checkbox" v-model="prefs.in_app" />
          <span>
            <b>Show notifications in the app</b>
            <em>Turning this off silences everything below.</em>
          </span>
        </label>
      </section>

      <section v-for="g in GROUPS" :key="g.label" class="card"
               :class="{ dim: !prefs.in_app }">
        <h2>{{ g.label }}</h2>
        <p class="hint">{{ g.hint }}</p>

        <label v-for="k in g.kinds" :key="k.key" class="row">
          <input type="checkbox" :checked="!muted(k.key)"
                 :disabled="!prefs.in_app" @change="toggle(k.key)" />
          <span>{{ k.label }}</span>
        </label>
      </section>

      <section class="card note">
        <h2>Email</h2>
        <p class="hint">
          Email delivery is planned but not yet available. Notifications appear
          in the app only for now.
        </p>
      </section>

      <UiButton variant="primary" :loading="saving" @click="save">
        Save preferences
      </UiButton>
    </template>
  </StaffLayout>
</template>

<style scoped>
.card { background: var(--nv-surface); border: 1px solid var(--nv-line);
        border-radius: var(--r-md); padding: var(--s-5);
        margin-bottom: var(--s-3); }
.card.dim { opacity: .55; }
.card.note { background: var(--nv-bg); }

h2 { font-size: 15px; margin: 0 0 4px; color: var(--nv-text); }
.hint { font-size: 13px; color: var(--nv-text-faint); margin: 0 0 var(--s-4);
        line-height: 1.55; }
.card.note .hint { margin: 0; }

.master { display: flex; gap: 12px; align-items: flex-start; cursor: pointer; }
.master b { display: block; font-size: 15px; color: var(--nv-text); }
.master em { font-size: 13px; color: var(--nv-text-faint); font-style: normal; }

.row { display: flex; gap: 12px; align-items: center; padding: 9px 0;
       border-top: 1px solid var(--nv-line); cursor: pointer;
       font-size: 14px; color: var(--nv-text); }
.row:first-of-type { border-top: 0; }
input { width: 17px; height: 17px; cursor: pointer; flex-shrink: 0;
        accent-color: var(--nv-navy-2); }
input:disabled { cursor: not-allowed; }

.err { background: var(--bad-bg); border: 1px solid var(--bad-line);
       color: var(--bad); padding: 11px 14px; border-radius: var(--r-sm);
       font-size: 14px; margin: 0 0 var(--s-4); }
.ok { background: var(--ok-bg); border: 1px solid var(--ok-line);
      color: var(--ok); padding: 11px 14px; border-radius: var(--r-sm);
      font-size: 14px; margin: 0 0 var(--s-4); }
</style>
