<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { EditorContent, useEditor } from '@tiptap/vue-3'
import StarterKit from '@tiptap/starter-kit'
import Link from '@tiptap/extension-link'
import Image from '@tiptap/extension-image'
import api from '../services/api'
import EvaluationPanel from '../components/EvaluationPanel.vue'
import ScanningOverlay from '../components/ScanningOverlay.vue'
import MessageThread from '../components/MessageThread.vue'
import VersionHistory from '../components/VersionHistory.vue'

const route = useRoute()
const router = useRouter()
const title = ref('')
const category = ref('')
const articleId = ref(route.params.id || null)
const saving = ref(false)
const submitting = ref(false)
const message = ref('')
const error = ref('')
const evaluation = ref(null)
const returnedByAi = ref(false)
const status = ref('DRAFTING')
const briefText = ref('')
const excerpt = ref('')
const heroFile = ref(null)
const heroPreview = ref(null)
const heroCaption = ref('')
const uploadingImage = ref(false)
const versions = ref([])
const scanning = ref(false)
const scanResult = ref(null)
const withdrawOpen = ref(false)
const withdrawReason = ref('')
const withdrawing = ref(false)
const deadline = ref(null)

const editor = useEditor({
  content: '',
  extensions: [StarterKit, Link.configure({ openOnClick: false }), Image],
  editorProps: { attributes: { class: 'prose-area' } },
})

onMounted(async () => {
  if (!articleId.value) return
  const { data } = await api.get(`/editorial/articles/${articleId.value}/`)
  title.value = data.title
  category.value = data.category
  status.value = data.status
  briefText.value = data.brief || ''
  excerpt.value = data.excerpt || ''
  heroCaption.value = data.hero_caption || ''
  heroPreview.value = data.hero_image
  versions.value = data.versions || []
  deadline.value = data.deadline
  evaluation.value = data.latest_evaluation
  returnedByAi.value = data.returned_by_ai
  editor.value?.commands.setContent(data.body)
})

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

function pickHero(e) {
  const f = e.target.files[0]
  if (!f) return
  heroFile.value = f
  heroPreview.value = URL.createObjectURL(f)
}

function clearHero() {
  heroFile.value = null
  heroPreview.value = null
  const el = document.getElementById('hero-file')
  if (el) el.value = ''
}

async function insertImage(e) {
  const f = e.target.files[0]
  if (!f) return
  if (!articleId.value) {
    error.value = 'Save the draft first, then add images.'
    return
  }
  uploadingImage.value = true
  try {
    const fd = new FormData()
    fd.append('article', articleId.value)
    fd.append('image', f)
    const { data } = await api.post('/editorial/images/', fd, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    editor.value?.chain().focus().setImage({ src: data.image }).run()
  } catch {
    error.value = 'Could not upload the image.'
  } finally {
    uploadingImage.value = false
    e.target.value = ''
  }
}

async function saveDraft() {
  error.value = ''; message.value = ''
  if (!title.value.trim()) { error.value = 'A headline is required.'; return false }
  saving.value = true
  try {
    const { data: body, config } = payload()
    if (articleId.value) {
      await api.patch(`/editorial/articles/${articleId.value}/`, body, config)
    } else {
      const { data } = await api.post('/editorial/articles/', body, config)
      articleId.value = data.id
      router.replace(`/writer/compose/${data.id}`)
    }
    message.value = 'Draft saved.'
    return true
  } catch (e) {
    error.value = JSON.stringify(e.response?.data) || 'Could not save the draft.'
    return false
  } finally { saving.value = false }
}

async function submitForReview() {
  const ok = await saveDraft()
  if (!ok) return
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
  if (passed) router.push('/writer')
  else window.location.reload()
}

async function withdraw() {
  error.value = ''
  if (withdrawReason.value.trim().length < 5) {
    error.value = 'Give a reason for withdrawing this article.'
    return
  }
  withdrawing.value = true
  try {
    await api.post(`/editorial/articles/${articleId.value}/withdraw/`,
                   { reason: withdrawReason.value })
    router.push('/writer')
  } catch (e) {
    error.value = e.response?.data?.detail || 'Could not withdraw.'
  } finally { withdrawing.value = false }
}

const btn = (c) => editor.value?.chain().focus()[c]().run()
const active = (n, a) => editor.value?.isActive(n, a)
</script>

<template>
  <div class="wrap">
    <ScanningOverlay :active="scanning" :result="scanResult"
                     :threshold="70" @done="finishScan" />

    <header>
      <h2>{{ articleId ? 'EDIT SUBMISSION' : 'NEW SUBMISSION' }}</h2>
      <router-link to="/writer" class="back">Back to dashboard</router-link>
    </header>

    <div v-if="briefText" class="brief-box">
      <h5>Editor's brief</h5>
      <p>{{ briefText }}</p>
      <small v-if="deadline">Deadline: {{ deadline }}</small>
    </div>

    <EvaluationPanel
      :evaluation="evaluation"
      :returned-by-ai="returnedByAi"
      :threshold="70" />

    <label>HEADLINE</label>
    <input v-model="title" class="title-in" placeholder="Enter your headline" />

    <label>CATEGORY</label>
    <select v-model="category">
      <option value="">Select a category…</option>
      <option>Business</option><option>Tech</option><option>Life</option>
      <option>Innovation</option><option>Leadership</option>
    </select>

    <label>STANDFIRST <span class="opt">optional</span>
      <input v-model="excerpt" maxlength="300"
             placeholder="One sentence shown under the headline and on cards" />
    </label>

    <label>HERO IMAGE <span class="opt">optional</span></label>
    <div v-if="heroPreview" class="hero-prev">
      <img :src="heroPreview" alt="" />
      <button class="rm" @click="clearHero">Remove</button>
    </div>
    <input id="hero-file" type="file" accept="image/*" @change="pickHero" />
    <input v-if="heroPreview" v-model="heroCaption" class="cap"
           placeholder="Photo caption or credit" />

    <label>BODY</label>
    <div v-if="editor" class="toolbar">
      <button :class="{ on: active('bold') }" @click="btn('toggleBold')"><b>B</b></button>
      <button :class="{ on: active('italic') }" @click="btn('toggleItalic')"><i>I</i></button>
      <span class="sep"></span>
      <button :class="{ on: active('heading', { level: 2 }) }"
              @click="editor.chain().focus().toggleHeading({ level: 2 }).run()">H2</button>
      <button :class="{ on: active('heading', { level: 3 }) }"
              @click="editor.chain().focus().toggleHeading({ level: 3 }).run()">H3</button>
      <span class="sep"></span>
      <button :class="{ on: active('bulletList') }" @click="btn('toggleBulletList')">• List</button>
      <button :class="{ on: active('orderedList') }" @click="btn('toggleOrderedList')">1. List</button>
      <button :class="{ on: active('blockquote') }" @click="btn('toggleBlockquote')">" Quote</button>
      <span class="sep"></span>
      <label class="imgbtn">
        {{ uploadingImage ? 'Uploading…' : 'Image' }}
        <input type="file" accept="image/*" @change="insertImage" hidden />
      </label>
    </div>
    <editor-content :editor="editor" class="editor" />

    <p v-if="error" class="err">{{ error }}</p>
    <p v-if="message" class="ok">{{ message }}</p>

    <VersionHistory :versions="versions"
                    :current-title="title"
                    :current-body="editor?.getHTML() || ''" />

    <MessageThread v-if="articleId" :article-id="articleId" />

    <div v-if="withdrawOpen" class="withdraw">
      <h5>Withdraw this article</h5>
      <p>It leaves the active pipeline and is removed from any issue it belongs to.</p>
      <textarea v-model="withdrawReason" rows="2"
                placeholder="Why are you withdrawing it?"></textarea>
      <div class="wacts">
        <button class="ghost" @click="withdrawOpen = false">Cancel</button>
        <button class="danger" :disabled="withdrawing" @click="withdraw">
          {{ withdrawing ? 'Withdrawing…' : 'Confirm Withdrawal' }}
        </button>
      </div>
    </div>

    <div class="actions">
      <button class="ghost" :disabled="saving" @click="saveDraft">
        {{ saving ? 'Saving…' : 'Save Draft' }}
      </button>
      <button class="primary" :disabled="submitting" @click="submitForReview">
        {{ submitting ? 'Submitting…' : 'Submit for Review' }}
      </button>
    </div>

    <button v-if="articleId && !withdrawOpen && status !== 'PUBLISHED'"
            class="wlink" @click="withdrawOpen = true">
      Withdraw this article
    </button>
  </div>
</template>

<style scoped>
.brief-box { border-left: 3px solid #4a7fb5; background: #f7faff;
             padding: 14px 16px; border-radius: 0 8px 8px 0; margin-bottom: 20px; }
.brief-box h5 { margin: 0 0 6px; font-size: 11px; letter-spacing: .5px;
                text-transform: uppercase; color: #4a7fb5; }
.brief-box p { margin: 0; font-size: 13px; line-height: 1.6; color: #444; }
.brief-box small { display: block; margin-top: 8px; font-size: 12px; color: #888; }
.wrap { max-width: 800px; margin: 40px auto; font-family: system-ui; padding: 0 16px; }
header { display: flex; justify-content: space-between; align-items: center; }
h2 { margin: 0; letter-spacing: 1px; }
.back { font-size: 13px; color: #555; }
label { display: block; font-size: 11px; margin-top: 22px; color: #555; letter-spacing: .5px; }
.title-in, select { width: 100%; padding: 11px; border: 1px solid #ccc; border-radius: 6px; margin-top: 6px; }
.title-in { font-size: 18px; font-weight: 600; }
.toolbar { display: flex; gap: 4px; align-items: center; margin-top: 6px; border: 1px solid #ccc;
           border-bottom: 0; border-radius: 6px 6px 0 0; padding: 6px; background: #fafafa; }
.toolbar button { border: 0; background: transparent; padding: 5px 9px; border-radius: 4px; cursor: pointer; font-size: 13px; }
.toolbar button.on { background: #1a2744; color: #fff; }
.imgbtn { display: inline-block; padding: 5px 9px; border-radius: 4px;
          font-size: 13px; cursor: pointer; margin: 0; }
.imgbtn:hover { background: #eee; }
.opt { color: #aaa; font-weight: 400; text-transform: none; letter-spacing: 0; }
.hero-prev { position: relative; margin-top: 6px; }
.hero-prev img { width: 100%; max-height: 260px; object-fit: cover; border-radius: 8px; }
.rm { position: absolute; top: 10px; right: 10px; border: 0; background: rgba(0,0,0,.65);
      color: #fff; padding: 6px 12px; border-radius: 6px; font-size: 12px; cursor: pointer; }
.cap { margin-top: 8px; }
.sep { width: 1px; height: 18px; background: #ddd; margin: 0 4px; }
.editor { border: 1px solid #ccc; border-radius: 0 0 6px 6px; padding: 14px; min-height: 320px; background: #fff; }
.actions { display: flex; gap: 10px; margin-top: 24px; }
.ghost { flex: 1; padding: 12px; border: 1px solid #ccc; background: #fff; border-radius: 6px; cursor: pointer; }
.primary { flex: 2; padding: 12px; border: 0; background: #1a2744; color: #fff; border-radius: 6px; font-weight: 600; cursor: pointer; }
button:disabled { opacity: .55; }
.withdraw { border: 1px solid #f0d9d9; background: #fffafa; border-radius: 8px;
            padding: 14px 16px; margin-top: 20px; }
.withdraw h5 { margin: 0 0 6px; font-size: 13px; color: #a33; }
.withdraw p { margin: 0 0 10px; font-size: 12px; color: #777; line-height: 1.5; }
.withdraw textarea { width: 100%; padding: 9px; border: 1px solid #ccc;
                     border-radius: 6px; font-family: inherit; font-size: 13px; }
.wacts { display: flex; gap: 8px; margin-top: 10px; }
.wacts button { flex: 1; padding: 10px; border-radius: 6px; cursor: pointer; font-size: 13px; }
.danger { border: 0; background: #b53b3b; color: #fff; font-weight: 600; }
.wlink { display: block; margin: 22px auto 0; border: 0; background: none;
         color: #a33; font-size: 13px; cursor: pointer; text-decoration: underline; }
.err { color: #c00; font-size: 13px; }
.ok { color: #0a7; font-size: 13px; }
</style>
