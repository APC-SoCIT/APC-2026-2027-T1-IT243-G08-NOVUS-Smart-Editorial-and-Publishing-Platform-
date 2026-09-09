<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { EditorContent, useEditor } from '@tiptap/vue-3'
import StarterKit from '@tiptap/starter-kit'
import Link from '@tiptap/extension-link'
import api from '../services/api'

const route = useRoute()
const router = useRouter()
const title = ref('')
const category = ref('')
const articleId = ref(route.params.id || null)
const saving = ref(false)
const submitting = ref(false)
const message = ref('')
const error = ref('')

const editor = useEditor({
  content: '',
  extensions: [StarterKit, Link.configure({ openOnClick: false })],
  editorProps: { attributes: { class: 'prose-area' } },
})

onMounted(async () => {
  if (!articleId.value) return
  const { data } = await api.get(`/editorial/articles/${articleId.value}/`)
  title.value = data.title
  category.value = data.category
  editor.value?.commands.setContent(data.body)
})

const payload = () => ({
  title: title.value,
  body: editor.value?.getHTML() || '',
  category: category.value,
})

async function saveDraft() {
  error.value = ''; message.value = ''
  if (!title.value.trim()) { error.value = 'A headline is required.'; return false }
  saving.value = true
  try {
    if (articleId.value) {
      await api.patch(`/editorial/articles/${articleId.value}/`, payload())
    } else {
      const { data } = await api.post('/editorial/articles/', payload())
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
  try {
    const { data } = await api.post(`/editorial/articles/${articleId.value}/submit/`)
    router.push({ path: '/writer', query: { score: data.overall_score } })
  } catch (e) {
    error.value = e.response?.data?.detail || 'Submission failed.'
  } finally { submitting.value = false }
}

const btn = (c) => editor.value?.chain().focus()[c]().run()
const active = (n, a) => editor.value?.isActive(n, a)
</script>

<template>
  <div class="wrap">
    <header>
      <h2>{{ articleId ? 'EDIT SUBMISSION' : 'NEW SUBMISSION' }}</h2>
      <router-link to="/writer" class="back">Back to dashboard</router-link>
    </header>

    <label>HEADLINE</label>
    <input v-model="title" class="title-in" placeholder="Enter your headline" />

    <label>CATEGORY</label>
    <select v-model="category">
      <option value="">Select a category…</option>
      <option>Business</option><option>Tech</option><option>Life</option>
      <option>Innovation</option><option>Leadership</option>
    </select>

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
    </div>
    <editor-content :editor="editor" class="editor" />

    <p v-if="error" class="err">{{ error }}</p>
    <p v-if="message" class="ok">{{ message }}</p>

    <div class="actions">
      <button class="ghost" :disabled="saving" @click="saveDraft">
        {{ saving ? 'Saving…' : 'Save Draft' }}
      </button>
      <button class="primary" :disabled="submitting" @click="submitForReview">
        {{ submitting ? 'Submitting…' : 'Submit for Review' }}
      </button>
    </div>
  </div>
</template>

<style scoped>
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
.sep { width: 1px; height: 18px; background: #ddd; margin: 0 4px; }
.editor { border: 1px solid #ccc; border-radius: 0 0 6px 6px; padding: 14px; min-height: 320px; background: #fff; }
.actions { display: flex; gap: 10px; margin-top: 24px; }
.ghost { flex: 1; padding: 12px; border: 1px solid #ccc; background: #fff; border-radius: 6px; cursor: pointer; }
.primary { flex: 2; padding: 12px; border: 0; background: #1a2744; color: #fff; border-radius: 6px; font-weight: 600; cursor: pointer; }
button:disabled { opacity: .55; }
.err { color: #c00; font-size: 13px; }
.ok { color: #0a7; font-size: 13px; }
</style>
