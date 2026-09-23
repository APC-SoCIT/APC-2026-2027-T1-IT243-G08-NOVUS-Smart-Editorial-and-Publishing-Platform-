<script setup>
import { ref, onMounted, computed, watch, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { EditorContent, useEditor } from '@tiptap/vue-3'
import StarterKit from '@tiptap/starter-kit'
import Image from '@tiptap/extension-image'
import api from '../services/api'
import EvaluationPanel from '../components/EvaluationPanel.vue'
import QuickFixes from '../components/QuickFixes.vue'
import ScanningOverlay from '../components/ScanningOverlay.vue'
import MessageThread from '../components/MessageThread.vue'
import VersionHistory from '../components/VersionHistory.vue'
import SlideOver from '../components/SlideOver.vue'
import UiButton from '../components/ui/UiButton.vue'
import { useAuthStore } from '../stores/auth'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

const articleId = ref(route.params.id || null)
const title = ref('')
const excerpt = ref('')
const category = ref('')
const briefText = ref('')
const deadline = ref(null)
const status = ref('DRAFTING')
const versions = ref([])
const evaluation = ref(null)
const fixBusy = ref(null)
const fixError = ref('')
const returnedByAi = ref(false)

const heroFile = ref(null)
const heroPreview = ref(null)
const heroCaption = ref('')

const saving = ref(false)
const savedAt = ref(null)
const submitting = ref(false)
const error = ref('')
const scanning = ref(false)
const scanResult = ref(null)

const detailsOpen = ref(false)
const withdrawOpen = ref(false)
const withdrawReason = ref('')
const withdrawing = ref(false)
const uploadingImage = ref(false)

const editor = useEditor({
  content: '',
  extensions: [StarterKit, Image],
  editorProps: { attributes: { class: 'canvas' } },
  onUpdate: () => { dirty.value = true },
})

const dirty = ref(false)
let autosave = null

const words = computed(() => {
  const text = (editor.value?.getText() || '').trim()
  return text ? text.split(/\s+/).length : 0
})
const minutes = computed(() => Math.max(1, Math.round(words.value / 200)))

const canEdit = computed(() =>
  ['ASSIGNED', 'DRAFTING', 'REVISION_REQUESTED'].includes(status.value))

const savedLabel = computed(() => {
  if (saving.value) return 'Saving…'
  if (dirty.value) return 'Unsaved changes'
  if (savedAt.value) {
    const s = Math.floor((Date.now() - savedAt.value) / 1000)
    if (s < 60) return 'Saved just now'
    return `Saved ${Math.floor(s / 60)} min ago`
  }
  return ''
})

onMounted(async () => {
  if (articleId.value) await loadArticle()
  // A writer should never lose work to a closed tab. Autosave every 20s
  // while there is something unsaved.
  autosave = setInterval(() => {
    if (dirty.value && articleId.value && canEdit.value && !fixBusy.value) save(true)
  }, 20000)
})
onUnmounted(() => clearInterval(autosave))

async function loadArticle() {
  const { data } = await api.get(`/editorial/articles/${articleId.value}/`)
  title.value = data.title
  excerpt.value = data.excerpt || ''
  category.value = data.category || ''
  briefText.value = data.brief || ''
  deadline.value = data.deadline
  status.value = data.status
  versions.value = data.versions || []
  evaluation.value = data.latest_evaluation
  returnedByAi.value = data.returned_by_ai
  heroCaption.value = data.hero_caption || ''
  heroPreview.value = data.hero_image
  editor.value?.commands.setContent(data.body)
  dirty.value = false
}

function payload() {
  const base = {
    title: title.value,
    body: editor.value?.getHTML() || '',
    category: category.value,
    excerpt: excerpt.value,
    hero_caption: heroCaption.value,
  }
  if (!heroFile.value) return { data: base, config: {} }
  const fd = new FormData()
  Object.entries(base).forEach(([k, v]) => fd.append(k, v))
  fd.append('hero_image', heroFile.value)
  return { data: fd, config: { headers: { 'Content-Type': 'multipart/form-data' } } }
}

async function save(quiet = false) {
  if (!title.value.trim()) {
    if (!quiet) error.value = 'Give the article a headline before saving.'
    return false
  }
  error.value = ''
  saving.value = true
  try {
    const { data: body, config } = payload()
    if (articleId.value) {
      await api.patch(`/editorial/articles/${articleId.value}/`, body, config)
    } else {
      const { data } = await api.post('/editorial/articles/', body, config)
      articleId.value = data.id
      // Keep the path the writer arrived on, so an editor is not sent
      // into a writer-shaped URL.
      const base = route.path.startsWith('/compose') ? '/compose' : '/writer/compose'
      router.replace(`${base}/${data.id}`)
    }
    heroFile.value = null
    savedAt.value = Date.now()
    dirty.value = false
    return true
  } catch (e) {
    error.value = 'Could not save. Your work is still here — try again.'
    return false
  } finally { saving.value = false }
}

// A fix is applied on the server to the saved copy. Saving first, locking
// the editor for the request, and loading the corrected copy afterwards is
// what stops autosave from quietly writing the old sentence back.
async function decideFix(fix, decision) {
  fixError.value = ''
  if (dirty.value && !(await save(true))) {
    fixError.value = 'Save your changes before applying a fix.'
    return
  }
  fixBusy.value = fix.id
  editor.value?.setEditable(false)
  try {
    const { data } = await api.post(
      `/editorial/articles/${articleId.value}/fixes/${fix.id}/${decision}/`)
    evaluation.value = data.evaluation
    if (decision === 'apply') {
      editor.value?.commands.setContent(data.body, false)
      dirty.value = false
    }
  } catch (e) {
    fixError.value = e.response?.data?.detail || 'Could not update that fix.'
    if (e.response?.data?.state === 'stale') fix.state = 'stale'
  } finally {
    editor.value?.setEditable(canEdit.value)
    fixBusy.value = null
  }
}

async function submit() {
  if (!(await save())) return
  if (words.value < 50) {
    error.value = 'This looks too short to submit. Aim for at least 50 words.'
    return
  }
  submitting.value = true
  scanning.value = true
  scanResult.value = null
  try {
    const { data } = await api.post(`/editorial/articles/${articleId.value}/submit/`)
    scanResult.value = data
  } catch (e) {
    scanning.value = false
    error.value = e.response?.data?.detail || 'Submission failed.'
  } finally { submitting.value = false }
}

function finishScan() {
  const passed = (scanResult.value?.overall_score ?? 0) >= 70
  scanning.value = false
  if (passed) router.push(auth.role === 'EDITOR' ? '/editor' : '/writer')
  else loadArticle()
}

function pickHero(e) {
  const f = e.target.files[0]
  if (!f) return
  heroFile.value = f
  heroPreview.value = URL.createObjectURL(f)
  dirty.value = true
}
function clearHero() { heroFile.value = null; heroPreview.value = null; dirty.value = true }

async function insertImage(e) {
  const f = e.target.files[0]
  if (!f) return
  if (!articleId.value) { error.value = 'Save the draft first, then add images.'; return }
  uploadingImage.value = true
  try {
    const fd = new FormData()
    fd.append('article', articleId.value)
    fd.append('image', f)
    const { data } = await api.post('/editorial/images/', fd,
      { headers: { 'Content-Type': 'multipart/form-data' } })
    editor.value?.chain().focus().setImage({ src: data.image }).run()
  } catch { error.value = 'Could not upload that image.' }
  finally { uploadingImage.value = false; e.target.value = '' }
}

async function withdraw() {
  if (withdrawReason.value.trim().length < 5) {
    error.value = 'Give a reason for withdrawing.'
    return
  }
  withdrawing.value = true
  try {
    await api.post(`/editorial/articles/${articleId.value}/withdraw/`,
                   { reason: withdrawReason.value })
    router.push(auth.role === 'EDITOR' ? '/editor' : '/writer')
  } catch (e) {
    error.value = e.response?.data?.detail || 'Could not withdraw.'
  } finally { withdrawing.value = false }
}

const cmd = (c) => editor.value?.chain().focus()[c]().run()
const on = (n, a) => editor.value?.isActive(n, a)
const back = () => router.push(auth.role === 'EDITOR' ? '/editor' : '/writer')
</script>

<template>
  <div class="composer">
    <ScanningOverlay :active="scanning" :result="scanResult"
                     :threshold="70" @done="finishScan" />

    <!-- ============ top bar ============ -->
    <header class="bar">
      <button class="back" @click="back" aria-label="Back to dashboard">←</button>

      <span class="state" role="status">{{ savedLabel }}</span>

      <span class="stats">
        {{ words }} word{{ words === 1 ? '' : 's' }} · {{ minutes }} min read
      </span>

      <div class="acts">
        <UiButton size="sm" @click="detailsOpen = true">Details</UiButton>
        <UiButton size="sm" :loading="saving" :disabled="!canEdit" @click="save()">
          Save
        </UiButton>
        <UiButton variant="primary" size="sm" :loading="submitting"
                  :disabled="!canEdit" @click="submit">
          Submit for review
        </UiButton>
      </div>
    </header>

    <!-- ============ notices ============ -->
    <div class="notices">
      <p v-if="error" class="err" role="alert">{{ error }}</p>

      <div v-if="!canEdit" class="locked" role="status">
        This article is <b>{{ status.replace(/_/g, ' ').toLowerCase() }}</b>
        and cannot be edited right now.
      </div>
    </div>

    <div class="compose-grid">

    <!-- ============ the page ============ -->
    <div class="page">
      <input v-model="title" class="headline" placeholder="Headline"
             aria-label="Headline" :disabled="!canEdit"
             @input="dirty = true" />

      <input v-model="excerpt" class="stand" maxlength="300"
             placeholder="Standfirst — one sentence beneath the headline"
             aria-label="Standfirst" :disabled="!canEdit"
             @input="dirty = true" />

      <div v-if="heroPreview" class="hero">
        <img :src="heroPreview" :alt="heroCaption || 'Hero image'" />
        <button v-if="canEdit" class="hx" @click="clearHero"
                aria-label="Remove hero image">×</button>
      </div>

      <div v-if="editor && canEdit" class="tools" role="toolbar"
           aria-label="Formatting">
        <button :class="{ on: on('bold') }" @click="cmd('toggleBold')"
                aria-label="Bold"><b>B</b></button>
        <button :class="{ on: on('italic') }" @click="cmd('toggleItalic')"
                aria-label="Italic"><i>I</i></button>
        <span class="sep" aria-hidden="true"></span>
        <button :class="{ on: on('heading', { level: 2 }) }"
                @click="editor.chain().focus().toggleHeading({ level: 2 }).run()"
                aria-label="Heading">H2</button>
        <button :class="{ on: on('heading', { level: 3 }) }"
                @click="editor.chain().focus().toggleHeading({ level: 3 }).run()"
                aria-label="Subheading">H3</button>
        <span class="sep" aria-hidden="true"></span>
        <button :class="{ on: on('bulletList') }" @click="cmd('toggleBulletList')"
                aria-label="Bulleted list">•</button>
        <button :class="{ on: on('orderedList') }" @click="cmd('toggleOrderedList')"
                aria-label="Numbered list">1.</button>
        <button :class="{ on: on('blockquote') }" @click="cmd('toggleBlockquote')"
                aria-label="Quotation">"</button>
        <span class="sep" aria-hidden="true"></span>
        <label class="imgbtn">
          {{ uploadingImage ? 'Uploading…' : 'Image' }}
          <input type="file" accept="image/*" hidden @change="insertImage" />
        </label>
      </div>

      <editor-content :editor="editor" class="surface" />
    </div>

    <!-- ---- context rail: reference while writing, not a wall to scroll past ---- -->
    <aside class="rail" aria-label="Article context">
      <section v-if="briefText" class="brief">
        <h2>Your brief</h2>
        <p>{{ briefText }}</p>
        <small v-if="deadline">Deadline {{ deadline }}</small>
      </section>

      <EvaluationPanel v-if="evaluation" :evaluation="evaluation"
                       :returned-by-ai="returnedByAi" :threshold="70" />

      <QuickFixes v-if="evaluation" :evaluation="evaluation" :busy="fixBusy"
                  :can-edit="canEdit" :error="fixError" @decide="decideFix" />

      <MessageThread v-if="articleId" :article-id="articleId" />

      <VersionHistory v-if="articleId" :versions="versions"
                      :current-title="title"
                      :current-body="editor?.getHTML() || ''" />
    </aside>
    </div>

    <div class="after" v-if="articleId && canEdit">
      <button class="wd" @click="withdrawOpen = true">
        Withdraw this article
      </button>
    </div>

    <!-- ============ details ============ -->
    <SlideOver :open="detailsOpen" title="Article details"
               subtitle="Category, photography, and how this appears to readers."
               @close="detailsOpen = false">
      <label>CATEGORY
        <select v-model="category" :disabled="!canEdit" @change="dirty = true">
          <option value="">Uncategorised</option>
          <option>Business</option><option>Tech</option><option>Life</option>
          <option>Innovation</option><option>Leadership</option>
        </select>
      </label>

      <label>HERO IMAGE
        <input type="file" accept="image/*" :disabled="!canEdit" @change="pickHero" />
      </label>
      <p class="hint">Optional. Articles without one run as text-only.</p>

      <label v-if="heroPreview">CAPTION OR CREDIT
        <input v-model="heroCaption" :disabled="!canEdit"
               placeholder="Photographer, location, or context"
               @input="dirty = true" />
      </label>

      <UiButton variant="primary" full :loading="saving" :disabled="!canEdit"
                @click="() => { save(); detailsOpen = false }">
        Save details
      </UiButton>
    </SlideOver>

    <SlideOver :open="withdrawOpen" title="Withdraw this article"
               subtitle="It leaves the active pipeline and is removed from any issue."
               @close="withdrawOpen = false">
      <label>REASON
        <textarea v-model="withdrawReason" rows="4"
                  placeholder="Why is this being withdrawn?"></textarea>
      </label>
      <UiButton variant="danger" full :loading="withdrawing" @click="withdraw">
        Confirm withdrawal
      </UiButton>
    </SlideOver>
  </div>
</template>

<style scoped>
.composer { min-height: 100vh; background: var(--nv-bg);
            font-family: var(--font-ui); padding-bottom: var(--s-9); }

/* ---- bar ---- */
.bar { position: sticky; top: 0; z-index: 30; display: flex; align-items: center;
       gap: var(--s-4); padding: var(--s-3) var(--s-5);
       background: rgba(255,255,255,.94); backdrop-filter: blur(8px);
       border-bottom: 1px solid var(--nv-line); }
.back { background: none; border: 0; font-size: 20px; color: var(--nv-text-muted);
        cursor: pointer; padding: 0 var(--s-2); }
.back:hover { color: var(--nv-text); }
.state { font-size: 13px; color: var(--nv-text-faint); min-width: 118px; }
.stats { font-size: 13px; color: var(--nv-text-muted); margin-left: auto; }
.acts { display: flex; gap: var(--s-2); }

/* ---- notices ---- */
.notices { max-width: 1180px; margin: 0 auto; padding: var(--s-5) var(--s-5) 0; }

/* The sheet keeps its comfortable measure; context sits beside it so a
   writer can consult the brief without leaving the paragraph. */
.compose-grid { max-width: 1180px; margin: var(--s-5) auto 0;
                padding: 0 var(--s-5); display: grid;
                grid-template-columns: minmax(0, 1fr) 340px;
                gap: var(--s-5); align-items: start; }
.rail { position: sticky; top: 76px; display: flex; flex-direction: column;
        gap: var(--s-4); max-height: calc(100vh - 96px); overflow-y: auto;
        padding-right: 2px; }
.err { background: var(--bad-bg); border: 1px solid var(--bad-line);
       color: var(--bad); padding: 12px 16px; border-radius: var(--r-sm);
       font-size: 14px; margin: 0 0 var(--s-4); }
.locked { background: var(--info-bg); border: 1px solid #cfe0f5; color: var(--info);
          padding: 12px 16px; border-radius: var(--r-sm); font-size: 14px;
          margin-bottom: var(--s-4); }
.brief { border-left: 3px solid var(--nv-accent); background: var(--nv-accent-soft);
         padding: 14px 18px; border-radius: 0 var(--r-sm) var(--r-sm) 0;
         margin-bottom: var(--s-4); }
.brief h2 { font-size: 12px; letter-spacing: .06em; text-transform: uppercase;
            color: var(--nv-accent); margin: 0 0 6px; }
.brief p { margin: 0; font-size: 15px; line-height: 1.6; color: var(--nv-text); }
.brief small { display: block; margin-top: 8px; font-size: 13px;
               color: var(--nv-text-muted); }

/* ---- the page: a quiet sheet, not a form ---- */
.page { background: var(--nv-surface);
        border: 1px solid var(--nv-line); border-radius: var(--r-md);
        padding: var(--s-8) var(--s-7); }

.headline { width: 100%; border: 0; padding: 0; margin-bottom: var(--s-3);
            font-family: var(--font-serif); font-size: 40px; font-weight: 600;
            line-height: 1.15; color: var(--nv-text); background: none; }
.headline::placeholder { color: #c8ced6; }
.headline:focus { outline: none; }

.stand { width: 100%; border: 0; padding: 0 0 var(--s-5); background: none;
         font-family: var(--font-serif); font-size: 20px; font-style: italic;
         color: var(--nv-text-muted); border-bottom: 1px solid var(--nv-line);
         margin-bottom: var(--s-5); }
.stand::placeholder { color: #ccd2d9; }
.stand:focus { outline: none; }

.hero { position: relative; margin-bottom: var(--s-5); }
.hero img { width: 100%; max-height: 320px; object-fit: cover;
            border-radius: var(--r-sm); }
.hx { position: absolute; top: 10px; right: 10px; width: 30px; height: 30px;
      border-radius: 50%; background: rgba(0,0,0,.7); color: #fff; border: 0;
      font-size: 18px; cursor: pointer; }

.tools { display: flex; align-items: center; gap: 5px; margin-bottom: var(--s-4);
         padding-bottom: var(--s-3); border-bottom: 1px solid var(--nv-line); }
/* A borderless toolbar on a white sheet read as decoration rather than
   controls. Giving each button a surface makes it legible as a button. */
.tools button, .imgbtn { border: 1px solid var(--nv-line);
                         background: var(--nv-surface); padding: 7px 12px;
                         border-radius: var(--r-sm); font-size: 14px;
                         font-weight: 600; cursor: pointer;
                         color: var(--nv-text); font-family: inherit; margin: 0;
                         transition: background var(--dur-fast) var(--ease-out),
                                     border-color var(--dur-fast) var(--ease-out); }
.tools button:hover, .imgbtn:hover { background: var(--nv-bg);
                                     border-color: var(--nv-line-strong); }
.tools button.on { background: var(--nv-navy-2); color: #fff; }
.sep { width: 1px; height: 18px; background: var(--nv-line); margin: 0 6px; }

.surface :deep(.canvas) { outline: none; min-height: 420px;
                          font-family: var(--font-serif); font-size: 19px;
                          line-height: 1.75; color: var(--nv-text); }
.surface :deep(p) { margin: 0 0 18px; }
.surface :deep(h2) { font-size: 26px; margin: 30px 0 12px; font-weight: 600; }
.surface :deep(h3) { font-size: 21px; margin: 24px 0 10px; }
.surface :deep(blockquote) { border-left: 3px solid var(--nv-line-strong);
                             padding-left: 18px; margin: 0 0 18px;
                             color: var(--nv-text-muted); }
.surface :deep(img) { width: 100%; border-radius: var(--r-sm); margin: 20px 0; }
.surface :deep(ul), .surface :deep(ol) { padding-left: 26px; margin: 0 0 18px; }

.after { max-width: 1180px; margin: 0 auto; padding: 0 var(--s-5); }
.wd { display: block; margin: var(--s-6) auto 0; background: none; border: 0;
      color: var(--bad); font-size: 14px; cursor: pointer;
      text-decoration: underline; font-family: inherit; }

/* slide-over fields */
label { display: block; font-size: 13px; color: var(--nv-text-muted);
        letter-spacing: .04em; margin-bottom: 16px; }
label input, label select, label textarea {
  width: 100%; margin-top: 6px; padding: 11px 13px; font-size: 15px;
  border: 1px solid var(--nv-line-strong); border-radius: var(--r-sm);
  font-family: inherit; }
.hint { font-size: 13px; color: var(--nv-text-faint); margin: -8px 0 16px; }

@media (max-width: 1080px) {
  .compose-grid { grid-template-columns: 1fr; }
  .rail { position: static; max-height: none; }
}

@media (max-width: 780px) {
  .page { padding: var(--s-5) var(--s-4); border-radius: 0; border-left: 0;
          border-right: 0; }
  .headline { font-size: 28px; }
  .stats { display: none; }
}
</style>
