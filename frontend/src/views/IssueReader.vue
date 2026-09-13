<script setup>
import { ref, onMounted, computed, nextTick } from 'vue'
import { useRoute } from 'vue-router'
import api from '../services/api'
import BossShell from '../components/BossShell.vue'
import FlipbookReader from '../components/FlipbookReader.vue'
import { useIntro, useReveal } from '../composables/useReveal'

const route = useRoute()
const issue = ref(null)
const loading = ref(true)
const missing = ref(false)
const reading = ref(false)
const replicaUrl = ref(null)
const fetching = ref(false)
const downloadError = ref('')

/* The layout is no longer publicly addressable, so the URL is requested when
   the reader asks for it and signed on the spot. It expires in fifteen
   minutes, which is why it is fetched on demand rather than with the page. */
async function requestDownload() {
  downloadError.value = ''
  fetching.value = true
  try {
    const { data } = await api.get(`/content/issues/${route.params.id}/download/`)
    replicaUrl.value = data.url
    return data.url
  } catch (e) {
    downloadError.value = e.response?.status === 403
      ? 'The digital edition is available to subscribers.'
      : 'That edition could not be opened just now.'
    return null
  } finally { fetching.value = false }
}

async function openReader() {
  const url = replicaUrl.value || await requestDownload()
  if (!url) return
  replicaUrl.value = url
  console.log('opening reader with:', url)
  await nextTick()
  reading.value = true
}

async function download() {
  const url = replicaUrl.value || await requestDownload()
  if (!url) return
  const a = document.createElement('a')
  a.href = url
  a.download = `BOSS-Issue-${issue.value.number}.pdf`
  a.click()
}

onMounted(async () => {
  try {
    const { data } = await api.get(`/content/issues/${route.params.id}/`)
    issue.value = data
    document.title = `Issue ${data.number} — ${data.title} — BOSS Magazine PH`
  } catch { missing.value = true }
  finally { loading.value = false }
})

useIntro('[data-intro]')
useReveal('[data-reveal]')

const fmt = (d) => d ? new Date(d).toLocaleDateString('en-PH',
  { year: 'numeric', month: 'long', day: 'numeric' }) : ''

// Layouts are PDF-only by validation, so no runtime check is needed.
</script>

<template>
  <BossShell>
    <p v-if="loading" class="state" role="status">Loading issue…</p>
    <p v-else-if="missing" class="state">That issue isn’t available.</p>

    <template v-else>
      <!-- masthead -->
      <section class="hero">
        <div class="cover" data-intro>
          <img v-if="issue.cover_image" :src="issue.cover_image"
               :alt="`Cover of Issue ${issue.number}, ${issue.title}`" />
          <div v-else class="placeholder" aria-hidden="true">
            <span class="n">№ {{ issue.number }}</span>
            <span class="t">{{ issue.title }}</span>
          </div>
        </div>

        <div class="info">
          <p class="eyebrow" data-intro>
            <span>Issue {{ issue.number }}</span>
            <span class="rule" aria-hidden="true"></span>
          </p>
          <h1 data-intro>{{ issue.title }}</h1>
          <p class="date" data-intro>
            {{ fmt(issue.published_at) }} · {{ issue.article_count }} articles
          </p>

          <template v-if="issue.replica_available">
            <div v-if="issue.can_access" data-intro>
              <div class="actions">
                <button class="read" :disabled="fetching" @click="openReader">
                  {{ fetching ? 'Opening…' : 'Read this issue' }}
                </button>
                <button class="dl" :disabled="fetching" @click="download">
                  Download the edition
                </button>
              </div>
              <p v-if="downloadError" class="dlerr" role="alert">
                {{ downloadError }}
              </p>
            </div>

            <div v-else class="locked" data-intro>
              <span class="badge">Subscribers only</span>
              <p>
                The digital edition is available to subscribers. Contact the
                editorial team to have a subscription activated on your account.
              </p>
              <router-link to="/login" class="sign">Sign in →</router-link>
            </div>
          </template>

          <p v-else class="nodigital" data-intro>
            No digital edition is available for this issue.
          </p>
        </div>
      </section>

      <!-- contents -->
      <section class="contents" aria-labelledby="contents-heading">
        <h2 id="contents-heading">In this issue</h2>

        <ol class="arts">
          <li v-for="(a, i) in issue.articles" :key="a.id" data-reveal>
            <router-link :to="`/read/${a.id}`">
              <span class="idx" aria-hidden="true">
                {{ String(i + 1).padStart(2, '0') }}
              </span>
              <span class="body">
                <span class="cat">
                  {{ a.category || 'General' }}
                  <span v-if="a.is_premium" class="lock">· Subscriber</span>
                </span>
                <span class="head">{{ a.title }}</span>
                <span v-if="a.excerpt" class="ex">{{ a.excerpt }}</span>
                <span class="by">
                  {{ a.author_name }} · {{ a.reading_time }} min read
                </span>
              </span>
              <span v-if="a.hero_image" class="thumb">
                <img :src="a.hero_image" :alt="''" aria-hidden="true" loading="lazy" />
              </span>
            </router-link>
          </li>
        </ol>
      </section>
    </template>
  </BossShell>

  <FlipbookReader v-if="reading && replicaUrl" :src="replicaUrl"
                  :title="`Issue ${issue.number} — ${issue.title}`"
                  @close="reading = false" />
</template>

<style scoped>
.state { color: var(--boss-text-muted); text-align: center; padding: var(--s-9);
         font-family: var(--font-ui); }

/* ---- masthead ---- */
.hero { max-width: 1100px; margin: 0 auto; padding: var(--s-8) var(--s-7);
        display: grid; grid-template-columns: 300px 1fr; gap: var(--s-8);
        align-items: start; }

.cover { aspect-ratio: 3/4; overflow: hidden;
         box-shadow: 0 20px 60px rgba(0,0,0,.55); }
.cover img { width: 100%; height: 100%; object-fit: cover; }
.placeholder { width: 100%; height: 100%; display: flex; flex-direction: column;
               align-items: center; justify-content: center; gap: var(--s-4);
               padding: var(--s-6); text-align: center;
               background: linear-gradient(150deg, #141210, #1f1a12); }
.placeholder .n { font-size: var(--t-sm); letter-spacing: var(--track-wide);
                  color: var(--boss-gold-deep); }
.placeholder .t { font-family: var(--font-serif); font-size: var(--t-xl);
                  color: var(--boss-text); line-height: var(--lh-snug); }

.info { padding-top: var(--s-3); }
.eyebrow { display: flex; align-items: center; gap: var(--s-4);
           font-family: var(--font-ui); font-size: var(--t-xs);
           letter-spacing: var(--track-caps); text-transform: uppercase;
           color: var(--boss-gold); margin: 0 0 var(--s-4); }
.rule { width: 50px; height: 1px; background: var(--boss-gold-deep); }
h1 { font-family: var(--font-serif); font-size: var(--t-3xl); font-weight: 500;
     line-height: var(--lh-tight); margin: 0 0 var(--s-3); color: var(--boss-text); }
.date { font-family: var(--font-ui); font-size: var(--t-sm);
        color: var(--boss-text-muted); margin: 0 0 var(--s-6); }

.actions { display: flex; gap: var(--s-3); flex-wrap: wrap; }
.read { background: var(--boss-gold); color: #0a0a0a; border: 0;
        padding: var(--s-4) var(--s-6); font-family: var(--font-ui);
        font-size: var(--t-xs); font-weight: 700;
        letter-spacing: var(--track-caps); text-transform: uppercase;
        cursor: pointer; transition: background var(--dur-base) var(--ease-out); }
.read:hover { background: var(--boss-gold-bright); }
.dlerr { margin: var(--s-3) 0 0; font-family: var(--font-ui);
         font-size: var(--t-sm); color: #e09a9a; }
.dl { border: 1px solid var(--boss-line); color: var(--boss-text-muted);
      background: transparent; cursor: pointer; font-family: var(--font-ui);
      padding: var(--s-4) var(--s-6); font-family: var(--font-ui);
      font-size: var(--t-xs); letter-spacing: var(--track-caps);
      text-transform: uppercase;
      transition: all var(--dur-base) var(--ease-out); }
.dl:hover { border-color: var(--boss-gold); color: var(--boss-gold); }

.locked { border: 1px solid var(--boss-gold-deep);
          background: rgba(212,164,55,.06); border-radius: var(--r-md);
          padding: var(--s-5); font-family: var(--font-ui); }
.badge { display: inline-block; font-size: var(--t-xs);
         letter-spacing: var(--track-caps); text-transform: uppercase;
         color: var(--boss-gold); margin-bottom: var(--s-3); }
.locked p { font-size: var(--t-sm); line-height: var(--lh-body);
            color: var(--boss-text-muted); margin: 0 0 var(--s-3); }
.sign { font-size: var(--t-xs); letter-spacing: var(--track-caps);
        text-transform: uppercase; color: var(--boss-gold); }
.nodigital { font-family: var(--font-ui); font-size: var(--t-sm);
             color: var(--boss-text-faint); }

/* ---- contents ---- */
.contents { max-width: 1100px; margin: 0 auto; padding: 0 var(--s-7) var(--s-9); }
.contents h2 { font-family: var(--font-ui); font-size: var(--t-xs);
               letter-spacing: var(--track-caps); text-transform: uppercase;
               color: var(--boss-text-faint); border-top: 1px solid var(--boss-line);
               padding-top: var(--s-5); margin: 0 0 var(--s-5); font-weight: 600; }

.arts { list-style: none; margin: 0; padding: 0;
        counter-reset: none; }
.arts li { border-bottom: 1px solid var(--boss-line); }
.arts a { display: grid; grid-template-columns: 46px 1fr 130px;
          gap: var(--s-5); align-items: start; padding: var(--s-5) 0;
          transition: opacity var(--dur-fast) var(--ease-out); }
.arts a:hover { opacity: .85; }
.idx { font-family: var(--font-serif); font-size: var(--t-lg);
       color: var(--boss-gold-deep); line-height: 1.1; }
.body { display: flex; flex-direction: column; gap: var(--s-2); min-width: 0; }
.cat { font-family: var(--font-ui); font-size: var(--t-xs);
       letter-spacing: var(--track-caps); text-transform: uppercase;
       color: var(--boss-gold); }
.lock { color: var(--boss-gold-deep); }
.head { font-family: var(--font-serif); font-size: var(--t-lg); font-weight: 600;
        color: var(--boss-text); line-height: var(--lh-snug); }
.arts a:hover .head { color: var(--boss-gold-bright); }
.ex { font-family: var(--font-ui); font-size: var(--t-sm);
      line-height: var(--lh-body); color: var(--boss-text-muted); }
.by { font-family: var(--font-ui); font-size: var(--t-xs);
      color: var(--boss-text-faint); }
.thumb { overflow: hidden; aspect-ratio: 4/3; }
.thumb img { width: 100%; height: 100%; object-fit: cover; }

@media (max-width: 860px) {
  .hero { grid-template-columns: 1fr; padding: var(--s-6) var(--s-4); }
  .cover { max-width: 260px; }
  .contents { padding: 0 var(--s-4) var(--s-8); }
  h1 { font-size: var(--t-2xl); }
  .arts a { grid-template-columns: 32px 1fr; }
  .thumb { display: none; }
}
</style>
