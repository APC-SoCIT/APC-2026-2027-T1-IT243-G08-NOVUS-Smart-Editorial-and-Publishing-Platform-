<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRoute } from 'vue-router'
import api from '../services/api'

const route = useRoute()
const article = ref(null)
const loading = ref(true)
const copied = ref('')

onMounted(async () => {
  const { data } = await api.get(`/editorial/articles/${route.params.id}/`)
  article.value = data
  loading.value = false
})

const wordCount = computed(() => {
  if (!article.value?.body) return 0
  const text = article.value.body.replace(/<[^>]*>/g, ' ')
  return text.trim().split(/\s+/).filter(Boolean).length
})

function plainText() {
  const el = document.createElement('div')
  el.innerHTML = article.value.body
  // Preserve paragraph breaks that innerText would otherwise collapse.
  return `${article.value.title}\n\n${el.innerText.trim()}`
}

async function copy(what) {
  const text = what === 'title' ? article.value.title : plainText()
  await navigator.clipboard.writeText(text)
  copied.value = what
  setTimeout(() => (copied.value = ''), 1800)
}
</script>

<template>
  <div class="wrap" v-if="!loading && article">
    <header>
      <h2>ARTICLE FOR LAYOUT</h2>
      <router-link to="/designer" class="back">Back to workspace</router-link>
    </header>

    <div class="specs">
      <div><span>STATUS</span><b>{{ article.status }}</b></div>
      <div><span>CATEGORY</span><b>{{ article.category || '—' }}</b></div>
      <div><span>WORDS</span><b>{{ wordCount }}</b></div>
      <div><span>AUTHOR</span><b>{{ article.writer_name }}</b></div>
    </div>

    <div class="tools">
      <button @click="copy('title')">
        {{ copied === 'title' ? 'Copied' : 'Copy headline' }}
      </button>
      <button @click="copy('all')">
        {{ copied === 'all' ? 'Copied' : 'Copy full text' }}
      </button>
    </div>

    <h1>{{ article.title }}</h1>
    <div class="body" v-html="article.body"></div>

    <p class="note">
      This is the approved copy. Any change to the text has to go back through
      the editor.
    </p>
  </div>
  <p v-else class="wrap">Loading…</p>
</template>

<style scoped>
.wrap { max-width: 760px; margin: 40px auto; font-family: system-ui; padding: 0 16px 70px; }
header { display: flex; justify-content: space-between; align-items: center; }
h2 { margin: 0; font-size: 15px; letter-spacing: 1px; }
.back { font-size: 13px; color: #555; }
.specs { display: flex; gap: 26px; margin: 22px 0 16px; padding: 14px 16px;
         border: 1px solid #eee; border-radius: 8px; background: #fafafa; }
.specs div { display: flex; flex-direction: column; gap: 3px; }
.specs span { font-size: 10px; letter-spacing: .6px; color: #999; }
.specs b { font-size: 13px; }
.tools { display: flex; gap: 8px; margin-bottom: 24px; }
.tools button { border: 1px solid #ccc; background: #fff; border-radius: 6px;
                padding: 8px 14px; font-size: 13px; cursor: pointer; }
.tools button:hover { background: #f4f4f4; }
h1 { font-size: 30px; line-height: 1.25; margin: 0 0 20px; font-family: Georgia, serif; }
.body { font-family: Georgia, serif; font-size: 17px; line-height: 1.75;
        border: 1px solid #eee; border-radius: 8px; padding: 26px; background: #fff; }
.body :deep(h2) { font-size: 22px; margin: 22px 0 10px; }
.body :deep(p) { margin: 0 0 16px; }
.body :deep(blockquote) { border-left: 3px solid #ddd; padding-left: 14px; color: #555; }
.note { margin-top: 20px; font-size: 12px; color: #999; }
</style>
