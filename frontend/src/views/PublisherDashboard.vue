<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import api from '../services/api'
import { useAuthStore } from '../stores/auth'
import StaffLayout from '../components/StaffLayout.vue'
import SlideOver from '../components/SlideOver.vue'
import ConfirmDialog from '../components/ConfirmDialog.vue'
import UiBadge from '../components/ui/UiBadge.vue'
import UiEmpty from '../components/ui/UiEmpty.vue'
import UiSkeleton from '../components/ui/UiSkeleton.vue'
import UiButton from '../components/ui/UiButton.vue'

const auth = useAuthStore()
const router = useRouter()

const issues = ref([])
const standalone = ref([])
const signoff = ref([])
const pendingSign = ref(null)
const loading = ref(true)
const tab = ref('signoff')
const error = ref('')
const busy = ref(null)

const newOpen = ref(false)
const form = ref({ number: '', title: '', target_release_date: '' })
const pendingArticle = ref(null)

const prep = computed(() => issues.value.filter(i =>
  !['PUBLISHED', 'ARCHIVED'].includes(i.status)))
const ready = computed(() => prep.value.filter(i => i.is_ready))
const live = computed(() => issues.value.filter(i => i.status === 'PUBLISHED'))

const TABS = computed(() => [
  { key: 'signoff', label: 'Needs sign-off', count: signoff.value.length },
  { key: 'prep',   label: 'In preparation', count: prep.value.length },
  { key: 'single', label: 'Single articles', count: standalone.value.length },
  { key: 'live',   label: 'Published',      count: live.value.length },
])

async function load() {
  const [i, a] = await Promise.all([
    api.get('/publication/issues/'),
    api.get('/editorial/articles/'),
  ])
  issues.value = i.data.results ?? i.data
  const all = a.data.results ?? a.data
  standalone.value = all.filter(x => x.status === 'APPROVED' && !x.issue)
  // Editor-authored copy waiting on a second reader. Nobody signs off
  // their own work, so it lands here rather than in the editor's queue.
  signoff.value = all.filter(x => x.status === 'PENDING_SIGNOFF')
}

onMounted(async () => {
  try {
    if (!auth.user) await auth.fetchUser()
    await load()
  } finally { loading.value = false }
})

async function createIssue() {
  error.value = ''
  if (!form.value.number || !form.value.title) {
    error.value = 'An issue number and title are required.'
    return
  }
  try {
    await api.post('/publication/issues/', {
      number: form.value.number,
      title: form.value.title,
      target_release_date: form.value.target_release_date || null,
    })
    form.value = { number: '', title: '', target_release_date: '' }
    newOpen.value = false
    await load()
  } catch (e) {
    error.value = e.response?.data?.number?.[0] || 'Could not create the issue.'
  }
}

async function publishSingle() {
  const a = pendingArticle.value
  pendingArticle.value = null
  error.value = ''
  busy.value = a.id
  try { await api.post(`/editorial/articles/${a.id}/publish/`); await load() }
  catch (e) { error.value = e.response?.data?.detail || 'Publishing failed.' }
  finally { busy.value = null }
}

async function doSignOff() {
  const a = pendingSign.value
  pendingSign.value = null
  error.value = ''
  busy.value = a.id
  try { await api.post(`/editorial/articles/${a.id}/sign-off/`); await load() }
  catch (e) { error.value = e.response?.data?.detail || 'Sign-off failed.' }
  finally { busy.value = null }
}

const pct = (i) => i.total_articles
  ? Math.round((i.approved_articles / i.total_articles) * 100) : 0
</script>

<template>
  <StaffLayout title="Publishing" subtitle="Issues, releases, and standalone articles">

    <template #action>
      <UiButton variant="primary" @click="newOpen = true">+ New issue</UiButton>
    </template>

    <p v-if="error" class="alert" role="alert">{{ error }}</p>

    <div class="toolbar">
      <nav class="tabs" role="tablist" aria-label="Publishing groups">
        <button v-for="t in TABS" :key="t.key" role="tab"
                :aria-selected="tab === t.key" :class="{ on: tab === t.key }"
                @click="tab = t.key">
          {{ t.label }}<span class="count">{{ t.count }}</span>
        </button>
      </nav>
    </div>

    <UiSkeleton v-if="loading" :rows="3" label="Loading issues" />

    <!-- editor-authored copy awaiting a second reader -->
    <template v-else-if="tab === 'signoff'">
      <UiEmpty v-if="!signoff.length" icon="✓" title="Nothing to sign off"
               body="Articles written by an editor arrive here for your approval, since nobody signs off their own copy." />
      <ul v-else class="rows">
        <li v-for="a in signoff" :key="a.id" class="row">
          <div class="meta">
            <span class="t">{{ a.title }}</span>
            <span class="sub">
              By {{ a.writer_name }} · {{ a.category || 'Uncategorised' }}
              · {{ a.reading_time }} min read
            </span>
            <p v-if="a.excerpt" class="ex">{{ a.excerpt }}</p>
          </div>
          <span v-if="a.latest_score" class="score">{{ a.latest_score }}</span>
          <div class="sacts">
            <UiButton size="sm" @click="router.push(`/editor/review/${a.id}`)">
              Read it
            </UiButton>
            <UiButton variant="primary" size="sm" :loading="busy === a.id"
                      @click="pendingSign = a">Sign off</UiButton>
          </div>
        </li>
      </ul>
    </template>

    <!-- issues in preparation -->
    <template v-else-if="tab === 'prep'">
      <UiEmpty v-if="!prep.length" icon="□" title="No issues in preparation"
               body="Create an issue, then an editor assigns approved articles to it.">
        <template #action>
          <UiButton variant="primary" @click="newOpen = true">Create an issue</UiButton>
        </template>
      </UiEmpty>

      <ul v-else class="rows">
        <li v-for="i in prep" :key="i.id" class="issue" tabindex="0" role="button"
            @click="router.push(`/publisher/issue/${i.id}`)"
            @keyup.enter="router.push(`/publisher/issue/${i.id}`)">
          <div class="itop">
            <div>
              <span class="num">Issue {{ i.number }}</span>
              <span class="t">{{ i.title }}</span>
            </div>
            <UiBadge :tone="i.is_ready ? 'ok' : 'neutral'">
              {{ i.is_ready ? 'Ready to publish' : 'In preparation' }}
            </UiBadge>
          </div>

          <div class="bar">
            <div class="track">
              <i :style="{ width: pct(i) + '%' }" :class="{ full: i.is_ready }"></i>
            </div>
            <span class="cnt">
              {{ i.approved_articles }} of {{ i.total_articles }} articles approved
            </span>
          </div>

          <div class="flags">
            <span :class="i.replica_available ? 'yes' : 'no'">
              {{ i.replica_available ? '✓' : '○' }} Digital edition
            </span>
            <span v-if="i.target_release_date" class="date">
              Target {{ i.target_release_date }}
            </span>
          </div>
        </li>
      </ul>
    </template>

    <!-- standalone -->
    <template v-else-if="tab === 'single'">
      <UiEmpty v-if="!standalone.length" icon="○" title="No standalone articles"
               body="Approved articles not assigned to an issue appear here and publish on their own." />
      <ul v-else class="rows">
        <li v-for="a in standalone" :key="a.id" class="row">
          <div class="meta">
            <span class="t">{{ a.title }}</span>
            <span class="sub">{{ a.writer_name }} · {{ a.category || 'Uncategorised' }}</span>
          </div>
          <UiButton variant="primary" size="sm" :loading="busy === a.id"
                    @click="pendingArticle = a">Publish</UiButton>
        </li>
      </ul>
    </template>

    <!-- published -->
    <template v-else>
      <UiEmpty v-if="!live.length" icon="★" title="Nothing published yet"
               body="Published issues appear here and on the public archive." />
      <ul v-else class="rows">
        <li v-for="i in live" :key="i.id" class="row" tabindex="0" role="button"
            @click="router.push(`/publisher/issue/${i.id}`)"
            @keyup.enter="router.push(`/publisher/issue/${i.id}`)">
          <div class="meta">
            <span class="t">Issue {{ i.number }} — {{ i.title }}</span>
            <span class="sub">{{ i.total_articles }} articles · published</span>
          </div>
          <UiBadge tone="ok">Live</UiBadge>
        </li>
      </ul>
    </template>

    <template #rail>
      <div class="glance">
        <h2>At a glance</h2>
        <dl>
          <div :class="{ warn: signoff.length }">
            <dt>Needs sign-off</dt><dd>{{ signoff.length }}</dd>
          </div>
          <div><dt>In preparation</dt><dd>{{ prep.length }}</dd></div>
          <div :class="{ ok: ready.length }">
            <dt>Ready to publish</dt><dd>{{ ready.length }}</dd>
          </div>
          <div><dt>Standalone waiting</dt><dd>{{ standalone.length }}</dd></div>
          <div><dt>Published</dt><dd>{{ live.length }}</dd></div>
        </dl>
      </div>

      <div v-if="ready.length" class="glance">
        <h2>Ready now</h2>
        <ul class="ready">
          <li v-for="i in ready" :key="i.id" tabindex="0" role="button"
              @click="router.push(`/publisher/issue/${i.id}`)"
              @keyup.enter="router.push(`/publisher/issue/${i.id}`)">
            <span class="rt">Issue {{ i.number }} — {{ i.title }}</span>
            <span class="rs">{{ i.total_articles }} articles</span>
          </li>
        </ul>
      </div>
    </template>
  </StaffLayout>

  <SlideOver :open="newOpen" title="New issue"
             subtitle="Give the issue a number, a title, and a target release date."
             @close="newOpen = false">
    <label>ISSUE NUMBER
      <input v-model="form.number" type="number" placeholder="14" />
    </label>
    <label>TITLE
      <input v-model="form.title" placeholder="The April Issue" />
    </label>
    <label>TARGET RELEASE DATE
      <input v-model="form.target_release_date" type="date" />
    </label>
    <p class="hint">
      Editors assign approved articles to this issue. It can be published once
      every assigned article is approved.
    </p>
    <p v-if="error" class="ferr" role="alert">{{ error }}</p>
    <UiButton variant="primary" full @click="createIssue">Create issue</UiButton>
  </SlideOver>

  <ConfirmDialog
    :open="!!pendingSign"
    title="Sign off this article?"
    :message="pendingSign
      ? `“${pendingSign.title}” by ${pendingSign.writer_name} will be approved and become eligible for publication.`
      : ''"
    confirm-label="Sign off"
    :points="[
      'You are acting as the second reader on editor-authored copy.',
      'It can then be assigned to an issue or published on its own.',
    ]"
    @confirm="doSignOff"
    @cancel="pendingSign = null" />

  <ConfirmDialog
    :open="!!pendingArticle"
    title="Publish this article?"
    :message="pendingArticle
      ? `“${pendingArticle.title}” goes live on the reader portal immediately.`
      : ''"
    confirm-label="Publish"
    :points="[
      'It is not part of an issue, so it publishes on its own.',
      'The writer is notified.',
    ]"
    @confirm="publishSingle"
    @cancel="pendingArticle = null" />
</template>

<style scoped>
.alert { background: var(--bad-bg); border: 1px solid var(--bad-line);
         color: var(--bad); padding: var(--s-4) var(--s-5);
         border-radius: var(--r-md); font-size: 15px; margin: 0 0 var(--s-4); }

.toolbar { margin-bottom: var(--s-5); }
.tabs { display: flex; gap: var(--s-1); }
.tabs button { display: inline-flex; align-items: center; gap: 8px;
               background: none; border: 0; border-radius: var(--r-sm);
               padding: 10px 16px; font-size: 15px; font-weight: 500;
               color: var(--nv-text-muted); cursor: pointer;
               transition: background var(--dur-fast) var(--ease-out); }
.tabs button:hover { background: var(--nv-bg); color: var(--nv-text); }
.tabs button.on { background: var(--nv-navy-2); color: #fff; font-weight: 600; }
.count { font-size: 13px; font-weight: 700; padding: 1px 8px;
         border-radius: var(--r-full); background: var(--nv-line); color: var(--nv-text-muted); }
.tabs button.on .count { background: rgba(255,255,255,.22); color: #fff; }

.rows { list-style: none; margin: 0; padding: 0;
        display: flex; flex-direction: column; gap: 10px; }

.issue { background: var(--nv-surface); border: 1px solid var(--nv-line);
         border-radius: var(--r-md); padding: 18px; cursor: pointer;
         transition: border-color var(--dur-fast) var(--ease-out),
                     box-shadow var(--dur-fast) var(--ease-out); }
.issue:hover { border-color: var(--nv-line-strong); box-shadow: var(--shadow-sm); }
.itop { display: flex; justify-content: space-between; align-items: flex-start;
        gap: var(--s-4); }
.num { display: block; font-size: 13px; color: var(--nv-text-muted); }
.t { font-size: 17px; font-weight: 600; color: var(--nv-text); }

.bar { margin-top: 14px; }
.track { height: 8px; background: var(--nv-line); border-radius: 4px; overflow: hidden; }
.track i { display: block; height: 100%; background: var(--nv-accent);
           transition: width var(--dur-base) var(--ease-out); }
.track i.full { background: var(--ok); }
.cnt { display: block; margin-top: 7px; font-size: 14px; color: var(--nv-text-muted); }

.flags { display: flex; gap: var(--s-5); margin-top: 12px; font-size: 14px; }
.flags .yes { color: var(--ok); }
.flags .no { color: var(--nv-text-faint); }
.flags .date { color: var(--nv-text-muted); margin-left: auto; }

.row { display: flex; align-items: flex-start; gap: var(--s-4);
       padding: 14px 18px; background: var(--nv-surface);
       border: 1px solid var(--nv-line); border-radius: var(--r-md); }
.meta { flex: 1; min-width: 0; }
.meta .t { display: block; font-size: 16px; margin-bottom: 3px; }
.sub { font-size: 14px; color: var(--nv-text-muted); }
.ex { margin: 8px 0 0; font-size: 14px; line-height: 1.55;
      color: var(--nv-text-muted); }
.sacts { display: flex; gap: 8px; flex-shrink: 0; }
.score { min-width: 42px; padding: 5px 10px; border-radius: var(--r-sm);
         text-align: center; font-size: 15px; font-weight: 700;
         border: 1px solid var(--ok-line); color: var(--ok);
         background: var(--ok-bg); flex-shrink: 0; }

.glance { background: var(--nv-surface); border: 1px solid var(--nv-line);
          border-radius: var(--r-md); padding: var(--s-5); }
.glance h2 { font-size: 13px; letter-spacing: .06em; text-transform: uppercase;
             color: var(--nv-text-faint); margin: 0 0 var(--s-4); font-weight: 600; }
dl { margin: 0; }
dl > div { display: flex; justify-content: space-between; align-items: baseline;
           padding: 10px 0; border-bottom: 1px solid var(--nv-line); }
dl > div:last-child { border-bottom: 0; }
dt { font-size: 14px; color: var(--nv-text-muted); }
dd { margin: 0; font-size: 20px; font-weight: 700; color: var(--nv-text);
     font-variant-numeric: tabular-nums; }
dl > div.ok dd { color: var(--ok); }

.ready { list-style: none; margin: 0; padding: 0; }
.ready li { padding: 9px 0; border-bottom: 1px solid var(--nv-line); cursor: pointer; }
.ready li:last-child { border-bottom: 0; }
.ready li:hover .rt { color: var(--nv-accent); }
.rt { display: block; font-size: 14px; color: var(--nv-text); overflow: hidden;
      text-overflow: ellipsis; white-space: nowrap; }
.rs { font-size: 13px; color: var(--nv-text-muted); }

/* slide-over form */
label { display: block; font-size: 13px; color: var(--nv-text-muted);
        letter-spacing: .04em; margin-bottom: 16px; }
label input { width: 100%; margin-top: 6px; padding: 11px 13px; font-size: 15px;
              border: 1px solid var(--nv-line-strong); border-radius: var(--r-sm);
              font-family: inherit; }
.hint { font-size: 14px; color: var(--nv-text-muted); line-height: 1.6;
        margin: 0 0 var(--s-4); }
.ferr { color: var(--bad); font-size: 14px; margin: 0 0 var(--s-3); }
</style>
