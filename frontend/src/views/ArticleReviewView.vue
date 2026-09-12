<script setup>
import { computed, ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import api from '../services/api'
import EvaluationPanel from '../components/EvaluationPanel.vue'
import PublishingPanel from '../components/PublishingPanel.vue'
import MessageThread from '../components/MessageThread.vue'
import StatusTimeline from '../components/StatusTimeline.vue'
import VersionHistory from '../components/VersionHistory.vue'
import ImageManager from '../components/ImageManager.vue'
import ConfirmDialog from '../components/ConfirmDialog.vue'

const route = useRoute()
const router = useRouter()
const id = route.params.id

const article = ref(null)
const loading = ref(true)
const busy = ref(false)
const error = ref('')

const showComposer = ref(false)
const notes = ref([])
const overrideOpen = ref(false)

// An article the gate returned can only be approved through Override AI,
// which forces a written justification (UC-1.8).
const wasReturned = computed(() =>
  article.value?.returned_by_ai
  && !article.value?.latest_evaluation?.is_overridden)
const withdrawOpen = ref(false)
const pullBackOpen = ref(false)
const pullBackReason = ref('')
const confirmApprove = ref(false)

/* Once an article is approved, published or withdrawn the editorial
   decision is made. Leaving the action bar visible invites approving
   something twice, which the backend rejects but the interface
   should not offer in the first place. */
/* Editorial actions only make sense on an article that has been
   submitted and assessed. A draft belongs to its writer. */
const isReviewable = computed(() =>
  article.value?.status === 'UNDER_REVIEW')

const isDecided = computed(() =>
  ['APPROVED', 'PUBLISHED', 'WITHDRAWN'].includes(article.value?.status))
const withdrawReason = ref('')
const overrideReason = ref('')

async function load() {
  const { data } = await api.get(`/editorial/articles/${id}/`)
  article.value = data
  loading.value = false
}
onMounted(load)

function startRevision() {
  // Prefill from the AI's suggestions (UC-1.7): the Editor accepts, edits, or removes.
  const s = article.value?.latest_evaluation?.suggestions || []
  notes.value = s.length
    ? s.map(x => ({ ...x }))
    : [{ section: '', note_type: 'STRUCTURE', instruction: '', priority: 'MEDIUM' }]
  showComposer.value = true
}
const addNote = () =>
  notes.value.push({ section: '', note_type: 'STRUCTURE', instruction: '', priority: 'MEDIUM' })
const removeNote = (i) => notes.value.splice(i, 1)

async function act(fn) {
  error.value = ''
  busy.value = true
  try { await fn(); router.push('/editor') }
  catch (e) { error.value = e.response?.data?.detail || 'Action failed.' }
  finally { busy.value = false }
}

const approve = () => act(() => api.post(`/editorial/articles/${id}/approve/`))

const pullBack = () => act(() => {
  if (pullBackReason.value.trim().length < 5)
    throw { response: { data: { detail: 'Give a reason for pulling this back.' } } }
  return api.post(`/editorial/articles/${id}/pull-back/`,
                  { reason: pullBackReason.value })
})
const doApprove = () => { confirmApprove.value = false; approve() }

const withdraw = () => act(() => {
  if (withdrawReason.value.trim().length < 5)
    throw { response: { data: { detail: 'Give a reason for withdrawing.' } } }
  return api.post(`/editorial/articles/${id}/withdraw/`, { reason: withdrawReason.value })
})

const sendRevision = () => act(() => {
  const payload = notes.value.filter(n => n.instruction.trim())
  if (!payload.length) throw { response: { data: { detail: 'Add at least one note.' } } }
  return api.post(`/editorial/articles/${id}/request-revision/`, { notes: payload })
})

const submitOverride = () => act(() => {
  if (overrideReason.value.trim().length < 10)
    throw { response: { data: { detail: 'A justification of at least 10 characters is required.' } } }
  return api.post(`/editorial/articles/${id}/override/`, { reason: overrideReason.value })
})
</script>

<template>
  <div class="wrap" v-if="!loading && article">
    <header>
      <h2>ARTICLE REVIEW</h2>
      <router-link to="/editor" class="back">Back to dashboard</router-link>
    </header>

    <h1>{{ article.title }}</h1>
    <p class="byline">
      {{ article.writer_name }} · {{ article.category || 'Uncategorised' }} ·
      <b>{{ article.status.replace('_', ' ') }}</b>
    </p>

    <p v-if="wasReturned" class="gatenote">
      Pre-screening returned this article. Approving it requires an override
      with a written justification, which is recorded against the evaluation.
    </p>

        <EvaluationPanel
      :evaluation="article.latest_evaluation"
      :returned-by-ai="article.returned_by_ai"
      :threshold="70" />

    <div class="review-grid">
      <div class="reading">
        <div class="body" v-html="article.body"></div>
      </div>

      <aside class="context" aria-label="Review context">

    <div v-if="article.revision_notes?.length" class="history">
      <h5>Revision history</h5>
      <div v-for="n in article.revision_notes" :key="n.id" class="hnote">
        <span class="tag">{{ n.note_type }}</span>
        <span class="tag">{{ n.priority }}</span>
        <em>{{ n.editor_name || 'Automated pre-screening' }}</em>
        <p>{{ n.instruction }}</p>
      </div>
    </div>

        <PublishingPanel
      v-if="['APPROVED', 'PUBLISHED'].includes(article.status)"
      :article="article" @changed="load" />

        <ImageManager :article="article" @changed="load" />

        <VersionHistory :versions="article.versions || []"
                    :current-title="article.title"
                    :current-body="article.body" />

        <StatusTimeline :article-id="article.id" />

        <MessageThread :article-id="article.id" />

    <ConfirmDialog
      :open="confirmApprove"
      title="Approve this article?"
      :message="`&quot;${article.title}&quot; will be marked approved and released to the next stage.`"
      confirm-label="Approve"
      :busy="busy"
      :points="[
        'The writer is notified and can no longer edit it directly.',
        'It becomes available for assignment to an issue.',
        'The graphics designer can read it for layout.',
      ]"
      @confirm="doApprove"
      @cancel="confirmApprove = false" />

    <p v-if="error" class="err" role="alert">{{ error }}</p>

    <!-- Revision composer -->
    <div v-if="showComposer" class="composer">
      <h5>Revision notes</h5>
      <p class="hint" v-if="article.latest_evaluation?.suggestions?.length">
        Prefilled from the automated evaluation. Edit or remove anything you disagree with.
      </p>
      <div v-for="(n, i) in notes" :key="i" class="note-row">
        <div class="row">
          <input v-model="n.section" placeholder="Section" />
          <select v-model="n.note_type">
            <option>GRAMMAR</option><option>TONE</option>
            <option>STRUCTURE</option><option>FACTUAL</option>
          </select>
          <select v-model="n.priority">
            <option>LOW</option><option>MEDIUM</option><option>HIGH</option>
          </select>
          <button class="x" @click="removeNote(i)">×</button>
        </div>
        <textarea v-model="n.instruction" rows="2"
                  placeholder="Specific instruction for the writer…"></textarea>
      </div>
      <button class="ghost sm" @click="addNote">+ Add another note</button>
    </div>

    <div v-if="withdrawOpen" class="composer">
      <h5>Withdraw this article</h5>
      <p class="hint">
        It leaves the active pipeline and is removed from any issue it belongs to.
      </p>
      <textarea v-model="withdrawReason" rows="2"
                placeholder="Why is this being withdrawn?"></textarea>
    </div>

    <!-- Override -->
    <div v-if="overrideOpen" class="composer">
      <h5>Override justification</h5>
      <p class="hint">Recorded against this evaluation for audit and reporting.</p>
      <textarea v-model="overrideReason" rows="3"
                placeholder="Why are you setting aside the automated verdict?"></textarea>
    </div>

      </aside>
    </div>

    <div v-if="isDecided" class="settled" role="status">
      <div class="stext">
        This article is <b>{{ article.status.replace(/_/g, ' ').toLowerCase() }}</b>.
        <template v-if="article.status === 'APPROVED'">
          Set its issue and reader access below.
        </template>
      </div>
      <button v-if="article.status === 'APPROVED'" class="pullback"
              @click="pullBackOpen = true">
        Pull back into review
      </button>
    </div>

    <div v-else-if="!isReviewable" class="settled waiting" role="status">
      This article is <b>{{ article.status.replace(/_/g, ' ').toLowerCase() }}</b>
      and has not been submitted for review yet. You can read it and leave a
      message, but it cannot be approved until the writer submits it and it
      passes pre-screening.
    </div>

    <div v-if="pullBackOpen" class="composer">
      <h5>Pull this article back into review</h5>
      <p class="hint">
        It returns to your review queue and the writer is notified. If it is in
        an issue, it will be removed and the issue's readiness corrected.
      </p>
      <textarea v-model="pullBackReason" rows="2"
                placeholder="Why is this coming back?"></textarea>
      <div class="pbacts">
        <button class="ghost" @click="pullBackOpen = false">Cancel</button>
        <button class="warn" :disabled="busy" @click="pullBack">
          Pull back
        </button>
      </div>
    </div>

    <div v-else class="actions">
      <template v-if="showComposer">
        <button class="ghost" @click="showComposer = false">Cancel</button>
        <button class="warn" :disabled="busy" @click="sendRevision">Send to Writer</button>
      </template>
      <template v-else-if="overrideOpen">
        <button class="ghost" @click="overrideOpen = false">Cancel</button>
        <button class="primary" :disabled="busy" @click="submitOverride">
          Override and Approve
        </button>
      </template>
      <template v-else-if="withdrawOpen">
        <button class="ghost" @click="withdrawOpen = false">Cancel</button>
        <button class="warn" :disabled="busy" @click="withdraw">Confirm Withdrawal</button>
      </template>
      <template v-else>
        <button class="ghost" @click="withdrawOpen = true">Withdraw</button>
        <button class="ghost" @click="startRevision">Request Revisions</button>
        <!-- Only offered when the gate returned the article: there is
             nothing to override on a verdict that already passed. -->
        <button v-if="wasReturned" class="primary" @click="overrideOpen = true">
          Override AI and Approve
        </button>
        <button v-if="!wasReturned" class="primary" :disabled="busy"
                @click="confirmApprove = true">Approve</button>
      </template>
    </div>
  </div>
  <p v-else class="wrap">Loading…</p>
</template>

<style scoped>
.wrap { max-width: 1240px; margin: 40px auto; font-family: system-ui; padding: 0 16px 60px; }
header { display: flex; justify-content: space-between; align-items: center; }
h2 { margin: 0; letter-spacing: 1px; font-size: 16px; }
.back { font-size: 13px; color: var(--nv-text-muted); }
h1 { margin: 18px 0 4px; font-size: 27px; line-height: 1.25; }
.byline { margin: 0 0 20px; font-size: 13px; color: #777; }
/* Two columns: copy on the left at a readable measure, reference on the
   right. Stacking them meant the body was always squeezed between panels. */
.review-grid { display: grid; grid-template-columns: minmax(0, 1fr) 380px;
               gap: var(--s-5); align-items: start; margin-top: var(--s-5); }
.reading { min-width: 0; }
.context { position: sticky; top: var(--s-4); display: flex;
           flex-direction: column; gap: var(--s-4);
           max-height: calc(100vh - 32px); overflow-y: auto; padding-right: 2px; }

.body { border: 1px solid var(--nv-line); border-radius: var(--r-md);
        padding: var(--s-6); background: var(--nv-surface);
        font-size: 17px; line-height: 1.75; color: var(--nv-text); }
.body :deep(p) { margin: 0 0 18px; }
.body :deep(h2) { font-size: 22px; margin: 28px 0 12px; }
.body :deep(h3) { font-size: 19px; margin: 22px 0 10px; }
.body :deep(img) { width: 100%; border-radius: var(--r-sm); margin: 20px 0; }
.body :deep(blockquote) { border-left: 3px solid var(--nv-line-strong);
                          padding-left: 18px; color: var(--nv-text-muted); }

@media (max-width: 1080px) {
  .review-grid { grid-template-columns: 1fr; }
  .context { position: static; max-height: none; }
}
.body :deep(h2) { font-size: 20px; margin: 18px 0 8px; }
.body :deep(p) { margin: 0 0 12px; }
.history { margin-top: 24px; }
.history h5, .composer h5 { margin: 0 0 8px; font-size: 12px; letter-spacing: .5px;
                            text-transform: uppercase; color: var(--nv-text-muted); }
.hnote { border-top: 1px solid var(--nv-line); padding: 10px 0; }
.hnote em { font-size: 11px; color: var(--nv-text-faint); font-style: normal; margin-left: 6px; }
.hnote p { margin: 5px 0 0; font-size: 13px; }
.tag { font-size: 10px; padding: 2px 7px; border-radius: 10px; background: var(--info-bg); color: var(--nv-text); margin-right: 4px; }
.composer { margin-top: 24px; border: 1px solid var(--nv-line); border-radius: 8px; padding: 16px; background: var(--nv-bg); }
.hint { margin: 0 0 12px; font-size: 12px; color: var(--nv-text-faint); }
.note-row { margin-bottom: 12px; }
.row { display: flex; gap: 6px; margin-bottom: 6px; }
.row input, .row select { padding: 7px; border: 1px solid var(--nv-line-strong); border-radius: 5px; font-size: 13px; }
.row input { flex: 1; }
.x { border: 1px solid var(--nv-line-strong); background: var(--nv-surface); border-radius: 5px; width: 30px; cursor: pointer; }
textarea { width: 100%; padding: 9px; border: 1px solid var(--nv-line-strong); border-radius: 5px;
           font-family: inherit; font-size: 13px; resize: vertical; }
.actions { display: flex; gap: 10px; margin-top: 24px; }
.ghost { flex: 1; padding: 12px; border: 1px solid var(--nv-line-strong); background: var(--nv-surface); border-radius: 6px; cursor: pointer; }
.ghost.sm { flex: none; padding: 7px 12px; font-size: 13px; }
.primary { flex: 1; padding: 12px; border: 0; background: var(--nv-navy-2); color: #fff;
           border-radius: 6px; font-weight: 600; cursor: pointer; }
.warn { flex: 1; padding: 12px; border: 0; background: #b5651d; color: #fff;
        border-radius: 6px; font-weight: 600; cursor: pointer; }
button:disabled { opacity: .55; }
.gatenote { background: var(--warn-bg); border: 1px solid #f0d9b5; color: #8a6321;
            padding: 11px 14px; border-radius: 8px; font-size: 13px;
            line-height: 1.6; margin: 0 0 16px; }
.settled { background: var(--ok-bg); border: 1px solid var(--ok-line);
           color: var(--ok); padding: 14px 18px; border-radius: var(--r-md);
           font-size: 15px; line-height: 1.6; margin-top: var(--s-5); }
.settled { display: flex; align-items: center; gap: var(--s-4); }
.stext { flex: 1; }
.settled b { text-transform: capitalize; }
.pullback { background: transparent; border: 1px solid currentColor;
            color: inherit; padding: 8px 14px; border-radius: var(--r-sm);
            font-size: 13px; cursor: pointer; white-space: nowrap;
            font-family: inherit; opacity: .75; }
.pullback:hover { opacity: 1; }
.pbacts { display: flex; gap: 8px; margin-top: var(--s-3); }
.pbacts button { flex: 1; padding: 10px; border-radius: var(--r-sm);
                 cursor: pointer; font-size: 13px; font-family: inherit; }
.settled.waiting { background: var(--nv-bg); border-color: var(--nv-line-strong);
                   color: var(--nv-text-muted); }
.err { color: var(--bad); font-size: 13px; margin-top: 14px; }
</style>
