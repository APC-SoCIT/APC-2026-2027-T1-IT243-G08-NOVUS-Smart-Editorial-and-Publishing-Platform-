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
const confirmArchive = ref(false)
const confirmClose = ref(false)
const reopenOpen = ref(false)
const reopenReason = ref('')

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

async function close() {
  confirmClose.value = false
  error.value = ''
  busy.value = true
  try {
    await api.post(`/publication/issues/${route.params.id}/close/`)
    await load()
  } catch (e) {
    error.value = e.response?.data?.detail || 'Could not close this issue.'
  } finally { busy.value = false }
}

async function reopen() {
  error.value = ''
  if (reopenReason.value.trim().length < 5) {
    error.value = 'Give a reason for reopening this issue.'
    return
  }
  busy.value = true
  try {
    await api.post(`/publication/issues/${route.params.id}/reopen/`,
                   { reason: reopenReason.value })
    reopenOpen.value = false
    reopenReason.value = ''
    await load()
  } catch (e) {
    error.value = e.response?.data?.detail || 'Could not reopen this issue.'
  } finally { busy.value = false }
}

async function archive() {
  confirmArchive.value = false
  error.value = ''
  busy.value = true
  try {
    await api.post(`/publication/issues/${route.params.id}/archive/`)
    await load()
  } catch (e) {
    error.value = e.response?.data?.detail || 'Could not archive this issue.'
  } finally { busy.value = false }
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
      :open="confirmClose"
      :title="`Close Issue #${issue.number}?`"
      message="The table of contents is fixed. Editors can no longer assign or remove articles."
      confirm-label="Close the issue"
      :busy="busy"
      :points="[
        `${issue.total_articles} articles are in this issue.`,
        'The designer can lay it out knowing the contents will not change.',
        'You can reopen it, with a reason, if a late story warrants it.',
      ]"
      @confirm="close"
      @cancel="confirmClose = false" />

    <ConfirmDialog
      :open="confirmArchive"
      :title="`Archive Issue #${issue.number}?`"
      message="It moves out of the active publishing list. Readers keep access to it in the public archive."
      confirm-label="Archive"
      :busy="busy"
      :points="[
        'It stops appearing among issues in preparation.',
        'Its articles remain published and readable.',
        'No new articles can be assigned to it.',
      ]"
      @confirm="archive"
      @cancel="confirmArchive = false" />

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

    <div v-if="issue.status === 'PLANNING'" class="closebar">
      <div>
        <b>This issue is open.</b>
        <p>
          Articles can still be added or removed. Close it to fix the table of
          contents so the layout can be finalised.
        </p>
      </div>
      <button class="close-btn" :disabled="busy || !issue.total_articles"
              @click="confirmClose = true">
        Close this issue
      </button>
    </div>

    <div v-else-if="issue.status === 'COMPILED'" class="closebar closed">
      <div>
        <b>This issue is closed.</b>
        <p>
          Its contents are fixed. Reopening is recorded, so do it when a late
          story genuinely warrants it rather than as a matter of course.
        </p>
        <p v-if="issue.reopen_reason" class="prev">
          Previously reopened: {{ issue.reopen_reason }}
        </p>
      </div>
      <button v-if="!reopenOpen" class="close-btn"
              @click="reopenOpen = true">Reopen</button>
    </div>

    <div v-if="reopenOpen" class="composer">
      <label for="reopen-why">WHY IS THIS BEING REOPENED?</label>
      <textarea id="reopen-why" v-model="reopenReason" rows="2"
                placeholder="A late feature was confirmed for this issue…"></textarea>
      <div class="racts">
        <button class="ghost" @click="reopenOpen = false">Cancel</button>
        <button class="warn" :disabled="busy" @click="reopen">Reopen issue</button>
      </div>
    </div>

    <button v-if="issue.status !== 'PUBLISHED' && issue.status !== 'ARCHIVED'"
            class="publish" :disabled="busy || !issue.is_ready"
            @click="confirmPublish = true">
      {{ busy ? 'Publishing…' : `Confirm and Publish Issue #${issue.number}` }}
    </button>
    <div v-else-if="issue.status === 'PUBLISHED'" class="live">
      <p>This issue is live on the reader portal.</p>
      <button class="archive" :disabled="busy" @click="confirmArchive = true">
        Archive this issue
      </button>
    </div>

    <p v-else-if="issue.status === 'ARCHIVED'" class="done">
      This issue is archived. Readers can still find it in the public archive;
      it no longer appears among issues in preparation.
    </p>
  </div>
  <p v-else class="wrap">Loading…</p>
</template>

<style scoped>
.wrap { max-width: 780px; margin: 40px auto; font-family: system-ui; padding: 0 16px 70px; }
header { display: flex; justify-content: space-between; align-items: center; }
h2 { margin: 0; font-size: 15px; letter-spacing: 1px; }
.back { font-size: 13px; color: var(--nv-text-muted); }
h1 { margin: 16px 0 4px; font-size: 30px; }
.sub { margin: 0 0 22px; font-size: 13px; color: #777; text-transform: capitalize; }
.check { border-radius: 10px; padding: 16px 18px; margin-bottom: 8px; }
.check.go { background: #f4fbf7; border: 1px solid #c9e6d4; }
.check.stop { background: var(--nv-surface)af7; border: 1px solid #f0d9c9; }
.check h4 { margin: 0 0 8px; font-size: 15px; }
.check.go h4 { color: var(--ok); }
.check.stop h4 { color: #a3561c; }
.check ul { margin: 0; padding-left: 18px; }
.check li { font-size: 13px; line-height: 1.7; color: var(--nv-text-muted); }
.fine { margin: 0; font-size: 13px; color: var(--nv-text-muted); }
h3 { margin: 28px 0 10px; font-size: 15px; }
ul.arts { list-style: none; padding: 0; margin: 0; }
.arts li, .design { display: flex; justify-content: space-between; align-items: center;
                    border: 1px solid var(--nv-line); border-radius: 8px; padding: 12px 14px; margin-bottom: 8px; }
.meta { display: flex; flex-direction: column; gap: 3px; }
.t { font-weight: 600; font-size: 14px; }
em { font-size: 12px; color: var(--nv-text-faint); font-style: normal; }
.badge { font-size: 11px; padding: 4px 10px; border-radius: 12px; text-transform: capitalize; }
.badge.ok { background: var(--ok-bg); color: var(--ok); }
.badge.wip { background: var(--warn-bg); color: var(--warn); }
.view { font-size: 13px; color: var(--nv-accent); }
.publish { width: 100%; margin-top: 26px; padding: 15px; border: 0; background: var(--nv-navy-2);
           color: #fff; border-radius: 8px; font-weight: 600; font-size: 15px; cursor: pointer; }
.publish:disabled { opacity: .4; cursor: not-allowed; }
.closebar { display: flex; align-items: flex-start; gap: var(--s-5);
            background: var(--nv-surface); border: 1px solid var(--nv-line);
            border-radius: var(--r-md); padding: var(--s-5);
            margin-top: var(--s-5); }
.closebar.closed { background: var(--info-bg); border-color: #cfe0f5; }
.closebar b { font-size: 15px; color: var(--nv-text); }
.closebar p { margin: 5px 0 0; font-size: 14px; line-height: 1.6;
              color: var(--nv-text-muted); max-width: 58ch; }
.closebar .prev { font-size: 13px; color: var(--nv-text-faint);
                  font-style: italic; }
.close-btn { flex-shrink: 0; border: 1px solid var(--nv-navy-2);
             background: var(--nv-surface); color: var(--nv-navy-2);
             padding: 10px 18px; border-radius: var(--r-sm); font-size: 14px;
             font-weight: 600; cursor: pointer; font-family: inherit; }
.close-btn:hover:not(:disabled) { background: var(--nv-navy-2); color: #fff; }
.close-btn:disabled { opacity: .45; cursor: not-allowed; }
.composer { margin-top: var(--s-3); background: var(--nv-surface);
            border: 1px solid var(--nv-line); border-radius: var(--r-md);
            padding: var(--s-5); }
.composer label { display: block; font-size: 12px; letter-spacing: .04em;
                  color: var(--nv-text-muted); margin-bottom: 6px; }
.composer textarea { width: 100%; padding: 10px; font-size: 14px;
                     font-family: inherit; border: 1px solid var(--nv-line-strong);
                     border-radius: var(--r-sm); resize: vertical;
                     background: var(--nv-surface); color: var(--nv-text); }
.racts { display: flex; gap: 8px; margin-top: var(--s-3); }
.racts button { flex: 1; padding: 10px; border-radius: var(--r-sm);
                cursor: pointer; font-size: 14px; font-family: inherit; }
.racts .ghost { border: 1px solid var(--nv-line-strong);
                background: var(--nv-surface); color: var(--nv-text); }
.racts .warn { border: 0; background: var(--warn); color: #fff; font-weight: 600; }
.live { margin-top: 26px; text-align: center; }
.live p { color: var(--ok); font-size: 14px; margin: 0 0 14px; }
.archive { border: 1px solid var(--nv-line-strong);
           background: var(--nv-surface); color: var(--nv-text-muted);
           padding: 10px 20px; border-radius: var(--r-sm);
           font-size: 14px; cursor: pointer; font-family: inherit; }
.archive:hover { border-color: var(--nv-text-faint); color: var(--nv-text); }
.done { margin-top: 26px; text-align: center; color: var(--ok); font-size: 14px; }
.empty { color: var(--nv-text-faint); font-size: 14px; }
.err { color: var(--bad); font-size: 13px; margin-top: 18px; }
.err-list { color: var(--bad); font-size: 13px; padding-left: 18px; }
</style>
