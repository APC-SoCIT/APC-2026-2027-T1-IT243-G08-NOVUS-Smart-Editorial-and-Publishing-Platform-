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
import StaffLayout from '../components/StaffLayout.vue'
import UiBadge from '../components/ui/UiBadge.vue'
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
const overrideReason = ref('')
const withdrawOpen = ref(false)
const withdrawReason = ref('')
const pullBackOpen = ref(false)
const pullBackReason = ref('')
const confirmApprove = ref(false)

/* What the editor may do, as one exhaustive value rather than several
   overlapping booleans. Every status maps to exactly one state, so no article
   can fall between branches — which is what previously left an article
   returned by the gate showing the full action bar.

     settled  — decided; pull back, set issue and reader access
     review   — submitted and passed; approve, revise or withdraw
     override — the gate returned it; UC-1.8 is the only way past
     waiting  — with the writer; read and discuss only
*/
const reviewState = computed(() => {
  const a = article.value
  if (!a) return 'waiting'
  if (['APPROVED', 'PUBLISHED', 'WITHDRAWN'].includes(a.status)) return 'settled'
  if (a.status === 'UNDER_REVIEW') return 'review'
  if (a.status === 'REVISION_REQUESTED'
      && a.returned_by_ai
      && !a.latest_evaluation?.is_overridden) return 'override'
  return 'waiting'
})

async function load() {
  const { data } = await api.get(`/editorial/articles/${id}/`)
  article.value = data
  loading.value = false
}
onMounted(load)

function startRevision() {
  // Prefilled from the evaluation (UC-1.7): the editor accepts, edits or removes.
  const s = article.value?.latest_evaluation?.suggestions || []
  notes.value = s.length
    ? s.map(x => ({ ...x }))
    : [{ section: '', note_type: 'STRUCTURE', instruction: '', priority: 'MEDIUM' }]
  showComposer.value = true
}
const addNote = () =>
  notes.value.push({ section: '', note_type: 'STRUCTURE', instruction: '', priority: 'MEDIUM' })
const removeNote = (i) => notes.value.splice(i, 1)

async function act(fn, stay = false) {
  error.value = ''
  busy.value = true
  try {
    await fn()
    if (stay) await load()
    else router.push('/editor')
  } catch (e) {
    error.value = e.response?.data?.detail || 'Action failed.'
  } finally { busy.value = false }
}

const approve = () => act(() => api.post(`/editorial/articles/${id}/approve/`))
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

// Staying on the page after an override lets the editor see the decision take
// effect, and then set the issue and access without navigating back in.
const submitOverride = () => act(async () => {
  if (overrideReason.value.trim().length < 10)
    throw { response: { data: { detail: 'A justification of at least 10 characters is required.' } } }
  await api.post(`/editorial/articles/${id}/override/`, { reason: overrideReason.value })
  overrideOpen.value = false
  overrideReason.value = ''
}, true)

const pullBack = () => act(async () => {
  if (pullBackReason.value.trim().length < 5)
    throw { response: { data: { detail: 'Give a reason for pulling this back.' } } }
  await api.post(`/editorial/articles/${id}/pull-back/`, { reason: pullBackReason.value })
  pullBackOpen.value = false
  pullBackReason.value = ''
}, true)
</script>

<template>
  <StaffLayout v-if="!loading && article"
               :title="article.title"
               :subtitle="`${article.writer_name} · ${article.category || 'Uncategorised'} · ${article.reading_time} min read`">

    <div class="topline">
      <router-link to="/editor" class="back">← Back to dashboard</router-link>
      <UiBadge :status="article.status" dot />
    </div>

    <p v-if="reviewState === 'override'" class="gatenote">
      Pre-screening returned this article. Approving it requires an override
      with a written justification, which is recorded against the evaluation.
    </p>

    <EvaluationPanel
      v-if="article.latest_evaluation"
      :evaluation="article.latest_evaluation"
      :returned-by-ai="article.returned_by_ai"
      :threshold="70" />

    <!-- ======== copy on the left, reference on the right ======== -->
    <div class="review-grid">
      <div class="reading">
        <div class="body" v-html="article.body"></div>
      </div>

      <aside class="context" aria-label="Review context">
        <PublishingPanel
          v-if="['APPROVED', 'PUBLISHED'].includes(article.status)"
          :article="article" @changed="load" />

        <div v-if="article.revision_notes?.length" class="history">
          <h5>Revision notes</h5>
          <div v-for="n in article.revision_notes" :key="n.id" class="hnote">
            <span class="tag">{{ n.note_type }}</span>
            <span class="tag">{{ n.priority }}</span>
            <em>{{ n.editor_name || 'Automated pre-screening' }}</em>
            <p>{{ n.instruction }}</p>
          </div>
        </div>

        <ImageManager :article="article" @changed="load" />
        <VersionHistory :versions="article.versions || []"
                        :current-title="article.title"
                        :current-body="article.body" />
        <StatusTimeline :article-id="article.id" />
        <MessageThread :article-id="article.id" />
      </aside>
    </div>

    <p v-if="error" class="err" role="alert">{{ error }}</p>

    <!-- ======== revision composer ======== -->
    <div v-if="showComposer" class="composer">
      <h5>Revision notes</h5>
      <p v-if="article.latest_evaluation?.suggestions?.length" class="hint">
        Prefilled from the automated evaluation. Edit or remove anything you
        disagree with.
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
          <button class="x" aria-label="Remove note" @click="removeNote(i)">×</button>
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
        <button class="warn" :disabled="busy" @click="pullBack">Pull back</button>
      </div>
    </div>

    <!-- ======== one branch per state ======== -->
    <div v-if="reviewState === 'settled'" class="settled" role="status">
      <div class="stext">
        This article is <b>{{ article.status.replace(/_/g, ' ').toLowerCase() }}</b>.
        <template v-if="article.status === 'APPROVED'">
          Set its issue and reader access in the panel on the right.
        </template>
      </div>
      <button v-if="article.status === 'APPROVED' && !pullBackOpen"
              class="pullback" @click="pullBackOpen = true">
        Pull back into review
      </button>
    </div>

    <div v-else-if="reviewState === 'waiting'" class="settled waiting" role="status">
      This article is <b>{{ article.status.replace(/_/g, ' ').toLowerCase() }}</b>
      and is currently with its writer. You can read it and leave a message; it
      returns to your queue when they submit it again.
    </div>

    <div v-else class="actions">
      <template v-if="showComposer">
        <button class="ghost" @click="showComposer = false">Cancel</button>
        <button class="warn" :disabled="busy" @click="sendRevision">Send to Writer</button>
      </template>

      <template v-else-if="withdrawOpen">
        <button class="ghost" @click="withdrawOpen = false">Cancel</button>
        <button class="warn" :disabled="busy" @click="withdraw">Confirm Withdrawal</button>
      </template>

      <!-- The gate returned it: override is the only route past, and it forces
           a written justification. Requesting revisions would be redundant,
           since the writer already has the AI's notes. -->
      <template v-else-if="reviewState === 'override'">
        <button class="ghost" @click="withdrawOpen = true">Withdraw</button>
        <button class="primary" @click="overrideOpen = true">
          Override AI and Approve
        </button>
      </template>

      <template v-else>
        <button class="ghost" @click="withdrawOpen = true">Withdraw</button>
        <button class="ghost" @click="startRevision">Request Revisions</button>
        <button class="primary" :disabled="busy"
                @click="confirmApprove = true">Approve</button>
      </template>
    </div>

    <ConfirmDialog
      :open="confirmApprove"
      title="Approve this article?"
      :message="`“${article.title}” will be marked approved and released to the next stage.`"
      confirm-label="Approve"
      :busy="busy"
      :points="[
        'The writer is notified and can no longer edit it directly.',
        'It becomes available for assignment to an issue.',
        'Once assigned, the designer can read it for layout.',
      ]"
      @confirm="doApprove"
      @cancel="confirmApprove = false" />
  </StaffLayout>

  <p v-else class="loading">Loading…</p>

  <!-- Override lives in a modal: it is a recorded decision, and an inline
       panel below a long article was invisible from the button that opened it. -->
  <teleport to="body">
    <transition name="fade">
      <div v-if="overrideOpen" class="omask" @click.self="overrideOpen = false">
        <div class="omodal" role="dialog" aria-modal="true" aria-labelledby="ov-title">
          <h3 id="ov-title">Override the pre-screening verdict</h3>

          <div v-if="article?.latest_evaluation" class="verdict">
            <span class="oscore">{{ article.latest_evaluation.overall_score }}</span>
            <p>
              Pre-screening returned this article, below the passing mark of 70.
              Approving it anyway is recorded with your name and reason.
            </p>
          </div>

          <label for="ov-reason">EDITORIAL JUSTIFICATION</label>
          <textarea id="ov-reason" v-model="overrideReason" rows="4"
                    placeholder="Why should this run despite the score?"></textarea>
          <p class="ohint">
            At least ten characters. This appears in the AI evaluation report
            and in the article's history.
          </p>

          <p v-if="error" class="oerr" role="alert">{{ error }}</p>

          <div class="oacts">
            <button class="ghost" @click="overrideOpen = false">Cancel</button>
            <button class="owarn" :disabled="busy" @click="submitOverride">
              {{ busy ? 'Approving…' : 'Override and approve' }}
            </button>
          </div>
        </div>
      </div>
    </transition>
  </teleport>
</template>

<style scoped>
.topline { display: flex; justify-content: space-between; align-items: center;
           gap: var(--s-4); margin-bottom: var(--s-4); flex-wrap: wrap; }
.topline > * { flex: 0 0 auto; }
.back { font-size: 14px; color: var(--nv-text-muted); }
.back:hover { color: var(--nv-accent); }
.loading { padding: 60px; text-align: center; color: var(--nv-text-faint); }

/* Copy on the left at a readable measure, reference on the right. Stacking
   them meant the body was always squeezed between panels. */
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

.history { border: 1px solid var(--nv-line); border-radius: var(--r-md);
           padding: var(--s-5); background: var(--nv-surface); }
.history h5, .composer h5 { margin: 0 0 var(--s-3); font-size: 12px;
                            letter-spacing: .5px; text-transform: uppercase;
                            color: var(--nv-text-muted); }
.hnote { border-top: 1px solid var(--nv-line); padding: 10px 0; }
.hnote:first-of-type { border-top: 0; padding-top: 0; }
.hnote em { font-size: 11px; color: var(--nv-text-faint); font-style: normal;
            margin-left: 6px; }
.hnote p { margin: 5px 0 0; font-size: 13px; line-height: 1.55;
           color: var(--nv-text); }
.tag { font-size: 10px; padding: 2px 7px; border-radius: 10px;
       background: var(--info-bg); color: var(--info); margin-right: 4px; }

.composer { margin-top: var(--s-5); border: 1px solid var(--nv-line);
            border-radius: var(--r-md); padding: var(--s-5);
            background: var(--nv-surface); }
.hint { margin: 0 0 12px; font-size: 13px; color: var(--nv-text-faint);
        line-height: 1.55; }
.note-row { margin-bottom: 12px; }
.row { display: flex; gap: 6px; margin-bottom: 6px; }
.row input, .row select { padding: 8px; border: 1px solid var(--nv-line-strong);
                          border-radius: var(--r-sm); font-size: 13px;
                          font-family: inherit; background: var(--nv-surface);
                          color: var(--nv-text); }
.row input { flex: 1; }
.x { border: 1px solid var(--nv-line-strong); background: var(--nv-surface);
     color: var(--nv-text); border-radius: var(--r-sm); width: 32px; cursor: pointer; }
textarea { width: 100%; padding: 10px; border: 1px solid var(--nv-line-strong);
           border-radius: var(--r-sm); font-family: inherit; font-size: 14px;
           resize: vertical; background: var(--nv-surface); color: var(--nv-text); }

.actions { display: flex; gap: 10px; margin-top: var(--s-5); }
.ghost { flex: 1; padding: 12px; border: 1px solid var(--nv-line-strong);
         background: var(--nv-surface); color: var(--nv-text);
         border-radius: var(--r-sm); cursor: pointer; font-family: inherit;
         font-size: 14px; }
.ghost.sm { flex: none; padding: 8px 14px; font-size: 13px; }
.primary { flex: 1; padding: 12px; border: 0; background: var(--nv-navy-2);
           color: #fff; border-radius: var(--r-sm); font-weight: 600;
           cursor: pointer; font-family: inherit; font-size: 14px; }
.warn { flex: 1; padding: 12px; border: 0; background: var(--warn); color: #fff;
        border-radius: var(--r-sm); font-weight: 600; cursor: pointer;
        font-family: inherit; font-size: 14px; }
button:disabled { opacity: .55; cursor: not-allowed; }

.gatenote { background: var(--warn-bg); border: 1px solid var(--warn-line);
            color: var(--warn); padding: 12px 16px; border-radius: var(--r-sm);
            font-size: 14px; line-height: 1.6; margin: 0 0 var(--s-4); }

.settled { display: flex; align-items: center; gap: var(--s-4);
           background: var(--ok-bg); border: 1px solid var(--ok-line);
           color: var(--ok); padding: 14px 18px; border-radius: var(--r-md);
           font-size: 15px; line-height: 1.6; margin-top: var(--s-5); }
.stext { flex: 1; }
.settled b { text-transform: capitalize; }
.settled.waiting { background: var(--nv-bg); border-color: var(--nv-line-strong);
                   color: var(--nv-text-muted); }
.pullback { background: transparent; border: 1px solid currentColor;
            color: inherit; padding: 8px 14px; border-radius: var(--r-sm);
            font-size: 13px; cursor: pointer; white-space: nowrap;
            font-family: inherit; opacity: .75; }
.pullback:hover { opacity: 1; }
.pbacts { display: flex; gap: 8px; margin-top: var(--s-3); }
.pbacts button { flex: 1; padding: 10px; border-radius: var(--r-sm);
                 cursor: pointer; font-size: 13px; font-family: inherit; }

.err { color: var(--bad); font-size: 14px; margin-top: var(--s-4); }

/* override modal */
.omask { position: fixed; inset: 0; z-index: 90; background: rgba(13,21,38,.6);
         backdrop-filter: blur(2px); display: flex; align-items: center;
         justify-content: center; padding: var(--s-5); }
.omodal { background: var(--nv-surface); border-radius: var(--r-lg);
          padding: var(--s-6); width: 480px; max-width: 100%;
          box-shadow: var(--shadow-lg); border-top: 4px solid var(--warn);
          font-family: var(--font-ui); }
.omodal h3 { margin: 0 0 var(--s-4); font-size: 18px; color: var(--nv-text); }
.verdict { display: flex; gap: var(--s-4); align-items: flex-start;
           background: var(--bad-bg); border: 1px solid var(--bad-line);
           border-radius: var(--r-sm); padding: 14px; margin-bottom: var(--s-5); }
.oscore { font-size: 28px; font-weight: 700; color: var(--bad); line-height: 1;
          font-variant-numeric: tabular-nums; }
.verdict p { margin: 0; font-size: 14px; line-height: 1.6; color: var(--bad); }
.omodal label { display: block; font-size: 12px; letter-spacing: .04em;
                color: var(--nv-text-muted); margin-bottom: 6px; }
.ohint { font-size: 13px; color: var(--nv-text-faint); margin: 8px 0 0;
         line-height: 1.5; }
.oerr { color: var(--bad); font-size: 14px; margin: var(--s-3) 0 0; }
.oacts { display: flex; gap: 10px; margin-top: var(--s-5); }
.oacts button { flex: 1; padding: 12px; border-radius: var(--r-sm);
                font-weight: 600; font-size: 14px; cursor: pointer;
                font-family: inherit; }
.owarn { border: 0; background: var(--warn); color: #fff; }

.fade-enter-active, .fade-leave-active { transition: opacity var(--dur-base); }
.fade-enter-from, .fade-leave-to { opacity: 0; }

@media (max-width: 1080px) {
  .review-grid { grid-template-columns: 1fr; }
  .context { position: static; max-height: none; }
}
</style>
