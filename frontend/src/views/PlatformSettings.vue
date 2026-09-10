<script setup>
import { ref, onMounted } from 'vue'
import api from '../services/api'
import StaffLayout from '../components/StaffLayout.vue'
import ConfirmDialog from '../components/ConfirmDialog.vue'

const form = ref(null)
const integrations = ref([])
const loading = ref(true)
const saving = ref(false)
const error = ref('')
const saved = ref('')
const confirmMaintenance = ref(false)

async function load() {
  const { data } = await api.get('/platform/settings/')
  integrations.value = data.integrations
  form.value = { ...data }
  delete form.value.integrations
  loading.value = false
}
onMounted(load)

async function save(extra = {}) {
  error.value = ''; saved.value = ''
  saving.value = true
  try {
    const payload = { ...form.value, ...extra }
    delete payload.updated_at
    const { data } = await api.patch('/platform/settings/', payload)
    integrations.value = data.integrations
    saved.value = 'Settings saved.'
    setTimeout(() => (saved.value = ''), 2500)
  } catch (e) {
    error.value = e.response?.data?.detail || 'Could not save. Administrator access is required.'
  } finally { saving.value = false }
}

function toggleMaintenance() {
  if (!form.value.maintenance_mode) {
    confirmMaintenance.value = true      // turning it ON needs confirming
  } else {
    form.value.maintenance_mode = false
    save()
  }
}

function doEnable() {
  confirmMaintenance.value = false
  form.value.maintenance_mode = true
  save()
}
</script>

<template>
  <StaffLayout title="Platform settings" subtitle="Site configuration and integration status">
    <p v-if="loading">Loading…</p>

    <template v-else>
      <p v-if="error" class="err" role="alert">{{ error }}</p>
      <p v-if="saved" class="ok" role="status">{{ saved }}</p>

      <div class="card" :class="{ live: form.maintenance_mode }">
        <div class="mhead">
          <div>
            <h4>Maintenance mode</h4>
            <p v-if="form.maintenance_mode" class="on">
              The public site is currently held. Staff can still work.
            </p>
            <p v-else class="off">The site is live and accepting readers.</p>
          </div>
          <button class="toggle" :class="{ active: form.maintenance_mode }"
                  :disabled="saving" @click="toggleMaintenance">
            {{ form.maintenance_mode ? 'Bring site back online' : 'Enable maintenance' }}
          </button>
        </div>
        <label>MESSAGE SHOWN TO READERS
          <input v-model="form.maintenance_message" @blur="save()" />
        </label>
      </div>

      <div class="card">
        <h4>Site</h4>
        <div class="row">
          <label class="grow">SITE NAME
            <input v-model="form.site_name" @blur="save()" />
          </label>
          <label>ACCENT COLOUR
            <div class="colour">
              <input v-model="form.accent_colour" type="color" @change="save()" />
              <span>{{ form.accent_colour }}</span>
            </div>
          </label>
        </div>
        <label>TAGLINE
          <input v-model="form.tagline" placeholder="Shown beneath the masthead"
                 @blur="save()" />
        </label>
        <label class="narrow">ARTICLES PER PAGE
          <input v-model.number="form.articles_per_page" type="number" min="4" max="48"
                 @blur="save()" />
        </label>
      </div>

      <div class="card">
        <h4>Integrations</h4>
        <p class="cap">
          Status only. Credentials are held in the server environment and are
          never editable from this interface.
        </p>
        <div v-for="i in integrations" :key="i.name" class="int">
          <span class="dot" :class="{ on: i.configured }"></span>
          <div class="idesc">
            <b>{{ i.name }}</b>
            <em>{{ i.purpose }}</em>
          </div>
          <span class="istate" :class="{ on: i.configured }">
            {{ i.configured ? 'Connected' : 'Not configured' }}
          </span>
          <small class="idetail">{{ i.detail }}</small>
        </div>
      </div>
    </template>

    <ConfirmDialog
      :open="confirmMaintenance"
      title="Enable maintenance mode?"
      message="Readers will not be able to reach the public site until you turn this off."
      confirm-label="Enable maintenance"
      tone="warn"
      :busy="saving"
      :points="[
        'The public portal and article pages return a maintenance notice.',
        'Editorial staff can continue working normally.',
        'Sign-in stays available so you can turn this off again.',
      ]"
      @confirm="doEnable"
      @cancel="confirmMaintenance = false" />
  </StaffLayout>
</template>

<style scoped>
.err { background: #fdeeee; border: 1px solid #f0cfcf; color: #a33;
       padding: 11px 14px; border-radius: 8px; font-size: 13px; margin: 0 0 16px; }
.ok { background: #eef8f2; border: 1px solid #c9e6d4; color: #1c6b45;
      padding: 11px 14px; border-radius: 8px; font-size: 13px; margin: 0 0 16px; }
.card { background: #fff; border: 1px solid #eaecef; border-radius: 9px;
        padding: 18px; margin-bottom: 16px; }
.card.live { border-color: #f0d9b5; background: #fffdf8; }
h4 { margin: 0 0 4px; font-size: 14px; }
.cap { margin: 0 0 16px; font-size: 12px; color: #99a; line-height: 1.55; }
.mhead { display: flex; justify-content: space-between; align-items: flex-start;
         gap: 20px; margin-bottom: 16px; }
.mhead p { margin: 3px 0 0; font-size: 13px; }
.on { color: #96631a; }
.off { color: #778; }
.toggle { border: 1px solid #d5dae0; background: #fff; border-radius: 7px;
          padding: 9px 16px; font-size: 13px; cursor: pointer; white-space: nowrap; }
.toggle.active { background: #b5651d; border-color: #b5651d; color: #fff; }
.toggle:disabled { opacity: .5; }
label { display: block; font-size: 11px; color: #667; letter-spacing: .5px;
        margin-bottom: 14px; }
label.narrow { max-width: 200px; }
.row { display: flex; gap: 14px; }
.row label { flex: 1; }
.row label.grow { flex: 3; }
input { width: 100%; padding: 9px 11px; border: 1px solid #d7dbe0; border-radius: 7px;
        font-size: 13px; margin-top: 5px; font-family: inherit; }
input:focus { outline: none; border-color: #4a7fb5; }
.colour { display: flex; align-items: center; gap: 9px; margin-top: 5px; }
.colour input { width: 42px; height: 34px; padding: 2px; cursor: pointer; margin: 0; }
.colour span { font-size: 12px; color: #778; font-family: monospace; }
.int { display: grid; grid-template-columns: 12px 1fr auto; gap: 10px 12px;
       align-items: center; padding: 12px 0; border-top: 1px solid #f2f4f6; }
.dot { width: 8px; height: 8px; border-radius: 50%; background: #d5dae0; }
.dot.on { background: #2e9e63; }
.idesc b { display: block; font-size: 13px; }
.idesc em { font-size: 12px; color: #99a; font-style: normal; }
.istate { font-size: 11px; padding: 3px 10px; border-radius: 10px;
          background: #f2f4f6; color: #778; }
.istate.on { background: #eaf7f0; color: #1c6b45; }
.idetail { grid-column: 2 / -1; font-size: 11px; color: #aab; }
</style>
