<script setup>
import { ref, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import api from '../services/api'
import BossShell from '../components/BossShell.vue'
import Paywall from '../components/Paywall.vue'
import { useIntro } from '../composables/useReveal'

const route = useRoute()
const article = ref(null)
const loading = ref(true)
const missing = ref(false)
const progress = ref(0)

async function load() {
  loading.value = true
  missing.value = false
  try {
    const { data } = await api.get(`/content/articles/${route.params.id}/`)
    article.value = data
    document.title = `${data.title} — BOSS Magazine PH`
  } catch { missing.value = true }
  finally { loading.value = false }
}
onMounted(load)
watch(() => route.params.id, load)

// Reading progress, a small orientation aid on long pieces.
onMounted(() => {
  const onScroll = () => {
    const h = document.documentElement.scrollHeight - window.innerHeight
    progress.value = h > 0 ? Math.min(100, (window.scrollY / h) * 100) : 0
  }
  window.addEventListener('scroll', onScroll, { passive: true })
})

useIntro('[data-intro]')

const fmt = (d) => d ? new Date(d).toLocaleDateString('en-PH',
  { year: 'numeric', month: 'long', day: 'numeric' }) : ''

async function share() {
  const url = window.location.href
  if (navigator.share) {
    try { await navigator.share({ title: article.value.title, url }) } catch {}
  } else {
    await navigator.clipboard.writeText(url)
    shared.value = true
    setTimeout(() => (shared.value = false), 2000)
  }
}
const shared = ref(false)
</script>

<template>
  <BossShell>
    <div class="progress" :style="{ width: progress + '%' }"
         role="progressbar" :aria-valuenow="Math.round(progress)"
         aria-valuemin="0" aria-valuemax="100"
         aria-label="Reading progress"></div>

    <p v-if="loading" class="state" role="status">Loading article…</p>
    <p v-else-if="missing" class="state">That article isn’t available.</p>

    <article v-else>
      <header class="head">
        <router-link :to="`/read?cat=${article.category}`" class="cat" data-intro>
          {{ article.category || 'General' }}
        </router-link>
        <h1 data-intro>{{ article.title }}</h1>
        <p v-if="article.excerpt" class="stand" data-intro>{{ article.excerpt }}</p>

        <div class="byline" data-intro>
          <div class="who">
            <span class="avatar" aria-hidden="true">
              {{ (article.author_name || '?').charAt(0) }}
            </span>
            <div>
              <b>{{ article.author_name }}</b>
              <span>{{ fmt(article.published_at) }} · {{ article.reading_time }} min read</span>
            </div>
          </div>
          <button class="share" @click="share">
            {{ shared ? 'Link copied' : 'Share' }}
          </button>
        </div>
      </header>

      <figure v-if="article.hero_image" class="hero">
        <img :src="article.hero_image"
             :alt="article.hero_caption || `Photograph accompanying ${article.title}`" />
        <figcaption v-if="article.hero_caption">{{ article.hero_caption }}</figcaption>
      </figure>

      <div class="body" :class="{ clipped: article.is_locked }" v-html="article.body"></div>

      <Paywall v-if="article.is_locked" />

      <footer v-else class="foot">
        <router-link to="/read" class="back">← All articles</router-link>
      </footer>
    </article>
  </BossShell>
</template>

<style scoped>
.progress { position: fixed; top: 0; left: 0; height: 2px;
            background: var(--boss-gold); z-index: 50;
            transition: width 90ms linear; }
.state { color: var(--boss-text-muted); text-align: center; padding: var(--s-9); }

article { max-width: 720px; margin: 0 auto; padding: var(--s-8) var(--s-5) var(--s-9); }

.cat { display: inline-block; font-size: var(--t-xs);
       letter-spacing: var(--track-caps); text-transform: uppercase;
       color: var(--boss-gold); margin-bottom: var(--s-4);
       transition: color var(--dur-fast) var(--ease-out); }
.cat:hover { color: var(--boss-gold-bright); }

h1 { font-family: var(--font-serif); font-size: var(--t-3xl);
     line-height: var(--lh-tight); font-weight: 600;
     margin: 0 0 var(--s-4); color: var(--boss-text); }
.stand { font-family: var(--font-serif); font-size: var(--t-lg);
         line-height: var(--lh-snug); color: var(--boss-text-muted);
         margin: 0 0 var(--s-6); font-style: italic; }

.byline { display: flex; justify-content: space-between; align-items: center;
          gap: var(--s-4); padding: var(--s-4) 0;
          border-top: 1px solid var(--boss-line);
          border-bottom: 1px solid var(--boss-line); }
.who { display: flex; align-items: center; gap: var(--s-3); }
.avatar { width: 38px; height: 38px; border-radius: var(--r-full);
          background: var(--boss-surface-2); border: 1px solid var(--boss-gold-deep);
          color: var(--boss-gold); display: flex; align-items: center;
          justify-content: center; font-weight: 600; flex-shrink: 0; }
.who b { display: block; font-size: var(--t-sm); }
.who span { font-size: var(--t-xs); color: var(--boss-text-faint); }
.share { background: transparent; border: 1px solid var(--boss-line);
         color: var(--boss-text-muted); padding: var(--s-2) var(--s-4);
         font-size: var(--t-xs); letter-spacing: var(--track-caps);
         text-transform: uppercase; cursor: pointer;
         transition: all var(--dur-fast) var(--ease-out); }
.share:hover { border-color: var(--boss-gold); color: var(--boss-gold); }

.hero { margin: var(--s-7) 0; }
.hero img { width: 100%; }
.hero figcaption { font-size: var(--t-xs); color: var(--boss-text-faint);
                   margin-top: var(--s-3); line-height: var(--lh-snug); }

.body { font-family: var(--font-serif); font-size: 1.25rem;
        line-height: var(--lh-loose); color: var(--boss-text); }
.body.clipped { max-height: 460px; overflow: hidden; }
.body :deep(p) { margin: 0 0 var(--s-5); }
.body :deep(p:first-of-type::first-letter) {
  float: left; font-size: 4.1rem; line-height: .82; padding: 6px 10px 0 0;
  color: var(--boss-gold); font-weight: 600;
}
.body :deep(h2) { font-size: var(--t-xl); margin: var(--s-7) 0 var(--s-4);
                  line-height: var(--lh-tight); font-weight: 600; }
.body :deep(h3) { font-size: var(--t-lg); margin: var(--s-6) 0 var(--s-3); }
.body :deep(blockquote) { border-left: 2px solid var(--boss-gold);
                          padding-left: var(--s-5); margin: var(--s-6) 0;
                          font-style: italic; color: var(--boss-gold-bright); }
.body :deep(img) { width: 100%; margin: var(--s-6) 0; }
.body :deep(ul), .body :deep(ol) { padding-left: var(--s-6); margin: 0 0 var(--s-5); }
.body :deep(a) { color: var(--boss-gold); border-bottom: 1px solid var(--boss-gold-deep); }

.foot { margin-top: var(--s-8); padding-top: var(--s-5);
        border-top: 1px solid var(--boss-line); }
.back { font-size: var(--t-xs); letter-spacing: var(--track-caps);
        text-transform: uppercase; color: var(--boss-text-muted); }
.back:hover { color: var(--boss-gold); }

@media (max-width: 760px) {
  h1 { font-size: var(--t-2xl); }
  .body { font-size: 1.12rem; }
}
</style>
