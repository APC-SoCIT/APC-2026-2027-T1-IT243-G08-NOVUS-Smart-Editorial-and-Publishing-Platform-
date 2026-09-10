<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import api from '../services/api'
import ConfirmDialog from '../components/ConfirmDialog.vue'

const route = useRoute()
const router = useRouter()
const issue = ref(null)
const loading = ref(true)
const busy = ref(false)
const error = ref('')
const reasons = ref([])
const confirmPublish = ref(false)

async function load() {
  const { data } = await api.get(`/publication/issues/${route.params.id}/`)
  issue.value = data
  loading.value = false
}
onMounted(load)

async function doPublish() {
  confirmPublish.value = false
  await publish()
}

async function publish() {
  error.value = ''; reasons.value = []
  busy.value = true
  try {
    await api.post(`/publication/issues/${route.params.id}/publish/`)
    await load()
  } catch (e) {
    error.value = e.response?.data?.detail || 'Publishing failed.'
    reasons.value = e.response?.data?.reasons || []
  } finally { busy.value = false }
}

const label = (s) => s.replace(/_/g, ' ')
</script>

<template>
  <div class="wrap" v-if="!loading && issue">
    <header>
      <h2>ISSUE #{{ issue.number }}</h2>
      <router-link to="/publisher" class="back">Back to pipeline</router-link>
    </header>

    <h1>{{ issue.title }}</h1>
    <p class="sub">
      <b>{{ label(issue.status) }}</b>
      <template v-if="issue.target_release_date"> · target {{ issue.target_release_date }}</template>
      <template v-if="issue.published_at"> · published</template>
    </p>

    <div class="check" :class="issue.is_ready ? 'go' : 'stop'">
      <h4>{{ issue.is_ready ? 'Ready for release' : 'Not ready for release' }}</h4>
      <ul v-if="issue.blocking_reasons.length">
        <li v-for="(r, i) in issue.blocking_reasons" :key="i">{{ r }}</li>
      </ul>
      <p v-else class="fine">
        All {{ issue.total_articles }} articles approved and the layout is signed off.
      </p>
    </div>

    <h3>Articles in this issue</h3>
    <p v-if="!issue.articles.length" class="empty">
      No articles assigned yet — an editor assigns approved articles to an issue.
    </p>
    <ul v-else class="arts">
      <li v-for="a in issue.articles" :key="a.id">
        <div class="meta">
          <span class="t">{{ a.title }}</span>
          <em>{{ a.writer_name }} · {{ a.category || 'Uncategorised' }}</em>
        </div>
        <span class="badge" :class="['APPROVED','PUBLISHED'].includes(a.status) ? 'ok' : 'wip'">
          {{ label(a.status) }}
        </span>
      </li>
    </ul>

    <h3>Magazine layout</h3>
    <div v-if="issue.design" class="design">
      <div class="meta">
        <span class="t">{{ issue.design.version }}</span>
        <em>{{ issue.design.designer_name }} · {{ issue.design.file_name }}</em>
      </div>
      <a :href="issue.design.file" target="_blank" class="view">Open</a>
    </div>
    <p v-else class="empty">No approved layout yet.</p>

    <ConfirmDialog
      :open="confirmPublish"
      :title="`Publish Issue #${issue.number}?`"
      message="Every article in this issue goes live at once and becomes publicly readable."
      :confirm-label="`Publish Issue #${issue.number}`"
      tone="danger"
      :busy="busy"
      :require-text="`Issue ${issue.number}`"
      :points="[
        `${issue.total_articles} articles will be published simultaneously.`,
        'Their writers are notified.',
        'Publication cannot be undone — a published issue can only be archived.',
      ]"
      @confirm="doPublish"
      @cancel="confirmPublish = false" />

    <p v-if="error" class="err" role="alert">{{ error }}</p>
    <ul v-if="reasons.length" class="err-list">
      <li v-for="(r, i) in reasons" :key="i">{{ r }}</li>
    </ul>

    <button v-if="issue.status !== 'PUBLISHED' && issue.status !== 'ARCHIVED'"
            class="publish" :disabled="busy || !issue.is_ready"
            @click="confirmPublish = true">
      {{ busy ? 'Publishing…' : `Confirm and Publish Issue #${issue.number}` }}
    </button>
    <p v-else class="done">This issue is live on the reader portal.</p>
  </div>
  <p v-else class="wrap">Loading…</p>
</template>

<style scoped>
.wrap { max-width: 780px; margin: 40px auto; font-family: system-ui; padding: 0 16px 70px; }
header { display: flex; justify-content: space-between; align-items: center; }
h2 { margin: 0; font-size: 15px; letter-spacing: 1px; }
.back { font-size: 13px; color: #555; }
h1 { margin: 16px 0 4px; font-size: 30px; }
.sub { margin: 0 0 22px; font-size: 13px; color: #777; text-transform: capitalize; }
.check { border-radius: 10px; padding: 16px 18px; margin-bottom: 8px; }
.check.go { background: #f4fbf7; border: 1px solid #c9e6d4; }
.check.stop { background: #fffaf7; border: 1px solid #f0d9c9; }
.check h4 { margin: 0 0 8px; font-size: 15px; }
.check.go h4 { color: #1c6b45; }
.check.stop h4 { color: #a3561c; }
.check ul { margin: 0; padding-left: 18px; }
.check li { font-size: 13px; line-height: 1.7; color: #555; }
.fine { margin: 0; font-size: 13px; color: #555; }
h3 { margin: 28px 0 10px; font-size: 15px; }
ul.arts { list-style: none; padding: 0; margin: 0; }
.arts li, .design { display: flex; justify-content: space-between; align-items: center;
                    border: 1px solid #eee; border-radius: 8px; padding: 12px 14px; margin-bottom: 8px; }
.meta { display: flex; flex-direction: column; gap: 3px; }
.t { font-weight: 600; font-size: 14px; }
em { font-size: 12px; color: #888; font-style: normal; }
.badge { font-size: 11px; padding: 4px 10px; border-radius: 12px; text-transform: capitalize; }
.badge.ok { background: #eaf7f0; color: #1c6b45; }
.badge.wip { background: #fdf2e0; color: #96631a; }
.view { font-size: 13px; color: #4a7fb5; }
.publish { width: 100%; margin-top: 26px; padding: 15px; border: 0; background: #1a2744;
           color: #fff; border-radius: 8px; font-weight: 600; font-size: 15px; cursor: pointer; }
.publish:disabled { opacity: .4; cursor: not-allowed; }
.done { margin-top: 26px; text-align: center; color: #1c6b45; font-size: 14px; }
.empty { color: #888; font-size: 14px; }
.err { color: #c00; font-size: 13px; margin-top: 18px; }
.err-list { color: #c00; font-size: 13px; padding-left: 18px; }
</style>
