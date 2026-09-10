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

    <p v-if="loading" class="state">Loading…</p>
    <p v-else-if="missing" class="state">That article isn't available.</p>

    <article v-else>
      <header>
        <span class="cat">{{ article.category || 'General' }}</span>
        <h1>{{ article.title }}</h1>
        <p v-if="article.excerpt" class="stand">{{ article.excerpt }}</p>
        <p class="meta">
          {{ article.author_name }} · {{ fmt(article.published_at) }}
          · {{ article.reading_time }} min read
        </p>
      </header>

      <figure v-if="article.hero_image" class="hero">
        <img :src="article.hero_image" alt="" />
        <figcaption v-if="article.hero_caption">{{ article.hero_caption }}</figcaption>
      </figure>

      <div class="body" v-html="article.body"></div>

      <router-link to="/read" class="back">← All articles</router-link>
    </article>
  </div>
</template>

<style scoped>
.site { font-family: Georgia, serif; }
nav { padding: 20px 32px; border-bottom: 1px solid #eee; }
.brand { font-size: 24px; letter-spacing: 5px; font-weight: 700; color: inherit; }

article { max-width: 720px; margin: 0 auto; padding: 46px 24px 90px; }
header { margin-bottom: 30px; }
.cat { font-family: system-ui; font-size: 10px; letter-spacing: 1.5px;
       text-transform: uppercase; color: #4a7fb5; }
h1 { font-size: 40px; line-height: 1.18; margin: 10px 0 14px; }
.stand { font-size: 20px; line-height: 1.55; color: #555; margin: 0 0 16px; }
.meta { font-family: system-ui; font-size: 13px; color: #999; margin: 0;
        padding-bottom: 20px; border-bottom: 1px solid #eee; }

.hero { margin: 0 0 32px; }
.hero img { width: 100%; border-radius: 8px; display: block; }
.hero figcaption { font-family: system-ui; font-size: 12px; color: #999; margin-top: 9px; }

.body { font-size: 18px; line-height: 1.78; }
.body :deep(h2) { font-size: 25px; margin: 34px 0 12px; line-height: 1.3; }
.body :deep(h3) { font-size: 20px; margin: 26px 0 10px; }
.body :deep(p) { margin: 0 0 20px; }
.body :deep(img) { width: 100%; border-radius: 8px; margin: 26px 0; }
.body :deep(blockquote) { border-left: 3px solid #d8d8d8; padding-left: 20px;
                          margin: 26px 0; font-style: italic; color: #555; }
.body :deep(ul), .body :deep(ol) { padding-left: 26px; margin: 0 0 20px; }

.back { display: inline-block; margin-top: 44px; font-family: system-ui;
        font-size: 13px; color: #4a7fb5; }
.state { color: #888; font-family: system-ui; text-align: center; padding: 60px; }
</style>
