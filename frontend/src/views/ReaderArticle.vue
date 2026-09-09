<script setup>
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import api from '../services/api'

const route = useRoute()
const article = ref(null)
const loading = ref(true)
const missing = ref(false)

onMounted(async () => {
  try {
    const { data } = await api.get(`/content/articles/${route.params.id}/`)
    article.value = data
  } catch { missing.value = true }
  finally { loading.value = false }
})

const fmt = (d) => d ? new Date(d).toLocaleDateString('en-PH',
  { year: 'numeric', month: 'long', day: 'numeric' }) : ''
</script>

<template>
  <div class="site">
    <nav><router-link to="/read" class="brand">BOSS</router-link></nav>
    <main>
      <p v-if="loading" class="state">Loading…</p>
      <p v-else-if="missing" class="state">That article isn't available.</p>
      <article v-else>
        <span class="cat">{{ article.category || 'General' }}</span>
        <h1>{{ article.title }}</h1>
        <p class="meta">{{ article.author_name }} · {{ fmt(article.published_at) }}</p>
        <div class="body" v-html="article.body"></div>
        <router-link to="/read" class="back">← All articles</router-link>
      </article>
    </main>
  </div>
</template>

<style scoped>
.site { font-family: Georgia, serif; }
nav { padding: 18px 32px; border-bottom: 1px solid #eee; }
.brand { font-size: 24px; letter-spacing: 5px; font-weight: 700; color: inherit; }
main { max-width: 700px; margin: 0 auto; padding: 44px 24px 90px; }
.cat { font-family: system-ui; font-size: 10px; letter-spacing: 1.5px; color: #4a7fb5; }
h1 { font-size: 38px; line-height: 1.2; margin: 10px 0 8px; }
.meta { font-family: system-ui; font-size: 13px; color: #888; margin: 0 0 30px;
        padding-bottom: 20px; border-bottom: 1px solid #eee; }
.body { font-size: 18px; line-height: 1.75; }
.body :deep(h2) { font-size: 24px; margin: 30px 0 10px; }
.body :deep(p) { margin: 0 0 18px; }
.body :deep(blockquote) { border-left: 3px solid #ddd; padding-left: 16px; color: #555; margin: 0 0 18px; }
.back { display: inline-block; margin-top: 36px; font-family: system-ui; font-size: 13px; color: #4a7fb5; }
.state { color: #888; font-family: system-ui; }
</style>
