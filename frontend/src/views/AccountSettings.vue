<script setup>
import { ref, onMounted, computed } from 'vue'
import api from '../services/api'
import { useAuthStore } from '../stores/auth'
import StaffLayout from '../components/StaffLayout.vue'
import BossShell from '../components/BossShell.vue'
import UiButton from '../components/ui/UiButton.vue'

const auth = useAuthStore()

const form = ref({ first_name: '', last_name: '', email: '' })
const currentPassword = ref('')
const original = ref({})
const saving = ref(false)
const saved = ref('')
const errors = ref({})

/* Readers get the magazine's chrome, staff get the workspace's. The same
   settings serve both — an account is an account — but dropping a reader into
   the editorial shell would be disorienting. */
const isStaff = computed(() => auth.role && auth.role !== 'READER')

const emailChanged = computed(() =>
  form.value.email.trim().toLowerCase() !== (original.value.email || '').toLowerCase())

const dirty = computed(() =>
  form.value.first_name !== original.value.first_name
  || form.value.last_name !== original.value.last_name
  || emailChanged.value)

onMounted(async () => {
  document.title = 'Your account'
  const { data } = await api.get('/auth/me/')
  form.value = {
    first_name: data.first_name,
    last_name: data.last_name,
    email: data.email,
  }
  original.value = { ...form.value }
})

async function save() {
  errors.value = {}
  saved.value = ''

  if (!form.value.first_name.trim() || !form.value.last_name.trim()) {
    errors.value.name = 'Both names are required.'
    return
  }
  if (emailChanged.value && !currentPassword.value) {
    errors.value.current_password =
      'Enter your current password to change your email address.'
    return
  }

  saving.value = true
  try {
    const payload = { ...form.value }
    if (emailChanged.value) payload.current_password = currentPassword.value

    const { data } = await api.patch('/auth/me/', payload)
    auth.user = data
    original.value = {
      first_name: data.first_name,
      last_name: data.last_name,
      email: data.email,
    }
    currentPassword.value = ''
    saved.value = 'Your details have been updated.'
    setTimeout(() => (saved.value = ''), 3000)
  } catch (e) {
    errors.value = e.response?.data || { detail: 'Could not save your changes.' }
  } finally { saving.value = false }
}

function revert() {
  form.value = { ...original.value }
  currentPassword.value = ''
  errors.value = {}
}

const err = (field) => {
  const v = errors.value[field]
  return Array.isArray(v) ? v[0] : v
}
</script>

<template>
  <component :is="isStaff ? StaffLayout : BossShell"
             title="Your account" subtitle="Name and sign-in details">

    <div class="page" :class="{ boss: !isStaff }">
      <h1 v-if="!isStaff">Your account</h1>

      <p v-if="saved" class="ok" role="status">{{ saved }}</p>
      <p v-if="err('detail')" class="bad" role="alert">{{ err('detail') }}</p>

      <section class="card">
        <h2>Name</h2>
        <p class="hint">How you appear to colleagues and on your articles.</p>

        <div class="row">
          <label>
            FIRST NAME
            <input v-model.trim="form.first_name" autocomplete="given-name" />
          </label>
          <label>
            LAST NAME
            <input v-model.trim="form.last_name" autocomplete="family-name" />
          </label>
        </div>
        <p v-if="err('name')" class="fielderr" role="alert">{{ err('name') }}</p>
      </section>

      <section class="card">
        <h2>Sign-in email</h2>
        <p class="hint">
          This is the address you sign in with. Changing it changes how you
          authenticate, so your current password is required.
        </p>

        <label>
          EMAIL
          <input v-model.trim="form.email" type="email" autocomplete="username"
                 :aria-invalid="!!err('email')" />
        </label>
        <p v-if="err('email')" class="fielderr" role="alert">{{ err('email') }}</p>

        <label v-if="emailChanged" class="pw">
          CURRENT PASSWORD
          <input v-model="currentPassword" type="password"
                 autocomplete="current-password"
                 :aria-invalid="!!err('current_password')" />
        </label>
        <p v-if="err('current_password')" class="fielderr" role="alert">
          {{ err('current_password') }}
        </p>
      </section>

      <section class="card muted">
        <h2>Password</h2>
        <p class="hint">
          Changing your own password is not yet available. Ask an administrator
          to reset it for you.
        </p>
      </section>

      <div class="actions">
        <UiButton v-if="dirty" @click="revert">Discard changes</UiButton>
        <UiButton variant="primary" :loading="saving" :disabled="!dirty"
                  @click="save">
          Save changes
        </UiButton>
      </div>
    </div>
  </component>
</template>

<style scoped>
.page { max-width: 620px; }
.page.boss { margin: 0 auto; padding: var(--s-8) var(--s-5) var(--s-9);
             font-family: var(--font-ui); }
.page.boss h1 { font-family: var(--font-serif); font-size: var(--t-2xl);
                color: var(--boss-text); margin: 0 0 var(--s-6);
                font-weight: 500; }

.card { background: var(--nv-surface); border: 1px solid var(--nv-line);
        border-radius: var(--r-md); padding: var(--s-5); margin-bottom: var(--s-3); }
.page.boss .card { background: var(--boss-surface); border-color: var(--boss-line); }
.card.muted { opacity: .75; }

h2 { font-size: 15px; margin: 0 0 4px; color: var(--nv-text); }
.page.boss h2 { color: var(--boss-text); }
.hint { font-size: 13px; line-height: 1.6; color: var(--nv-text-faint);
        margin: 0 0 var(--s-4); }
.page.boss .hint { color: var(--boss-text-muted); }
.card.muted .hint { margin: 0; }

.row { display: flex; gap: var(--s-3); }
.row label { flex: 1; }
label { display: block; font-size: 12px; letter-spacing: .04em;
        color: var(--nv-text-muted); margin-bottom: var(--s-3); }
.page.boss label { color: var(--boss-text-muted); }
input { width: 100%; margin-top: 6px; padding: 11px 13px; font-size: 15px;
        font-family: inherit; border: 1px solid var(--nv-line-strong);
        border-radius: var(--r-sm); background: var(--nv-surface);
        color: var(--nv-text); }
.page.boss input { background: var(--boss-surface-2);
                   border-color: var(--boss-line); color: var(--boss-text); }
input[aria-invalid="true"] { border-color: var(--bad); }

.pw { margin-top: var(--s-2); padding-top: var(--s-4);
      border-top: 1px solid var(--nv-line); }
.page.boss .pw { border-top-color: var(--boss-line); }

.fielderr { font-size: 13px; color: var(--bad); margin: -8px 0 var(--s-3); }
.ok { background: var(--ok-bg); border: 1px solid var(--ok-line); color: var(--ok);
      padding: 11px 14px; border-radius: var(--r-sm); font-size: 14px;
      margin: 0 0 var(--s-4); }
.bad { background: var(--bad-bg); border: 1px solid var(--bad-line); color: var(--bad);
       padding: 11px 14px; border-radius: var(--r-sm); font-size: 14px;
       margin: 0 0 var(--s-4); }

.actions { display: flex; gap: var(--s-3); justify-content: flex-end;
           margin-top: var(--s-5); }
</style>
