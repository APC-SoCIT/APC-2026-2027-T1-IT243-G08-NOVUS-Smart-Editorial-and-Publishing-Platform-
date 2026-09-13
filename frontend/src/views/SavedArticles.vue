<script setup>
import { ref, onMounted } from 'vue'
import api from '../services/api'
import BossShell from '../components/BossShell.vue'
import BookmarkButton from '../components/BookmarkButton.vue'
import { useIntro, useReveal } from '../composables/useReveal'

const articles = ref([])
const loading = ref(true)

async function load() {
  try {
    const { data } = await api.get('/content/bookmarks/')
    articles.value = data.results ?? data
  } finally { loading.value = false }
}
onMounted(() => { document.title = 'Saved — BOSS Magazine PH'; load() })

useIntro('[data-intro]')
useReveal('[data-reveal]')

/* Removing from this page should take the article off it. Leaving a card
   behind that says "Save" would be confusing — the reader just unsaved it. */
function onChanged(id, saved) {
  if (!saved) articles.value = articles.value.filter(a => a.id !== id)
}

const fmt = (d) => d
  ? new Date(d).toLocaleDateString('en-PH',
      { year: 'numeric', month: 'long', day: 'numeric' })
  : ''
</script>

<template>
  <BossShell>
    <header class="intro">
      <p class="eyebrow" data-intro>
        <span>Your library</span><span class="rule" aria-hidden="true"></span>
      </p>
      <h1 data-intro>Saved articles</h1>
      <p class="sub" data-intro>Pieces you have kept to return to.</p>
    </header>

    <section class="wrap">
      <p v-if="loading" class="state" role="status">Loading…</p>

      <div v-else-if="!articles.length" class="empty">
        <p class="big">Nothing saved yet.</p>
        <p>
          Select the bookmark on any article to keep it here. Saved pieces stay
          available whether or not they are still on the homepage.
        </p>
        <router-link to="/read" class="cta">Browse articles</router-link>
      </div>

      <ul v-else class="list">
        <li v-for="a in articles" :key="a.id" data-reveal>
          <router-link :to="`/read/${a.id}`" class="card">
            <div v-if="a.hero_image" class="thumb">
              <img :src="a.hero_image" :alt="`Cover image for ${a.title}`"
                   loading="lazy" />
            </div>

            <div class="body">
              <span class="cat">
                {{ a.category || 'General' }}
                <span v-if="a.is_premium" class="lock">· Subscriber</span>
              </span>
              <h2>{{ a.title }}</h2>
              <p v-if="a.excerpt">{{ a.excerpt }}</p>
              <span class="meta">
                {{ a.author_name }} · {{ fmt(a.published_at) }}
                · {{ a.reading_time }} min read
              </span>
            </div>
          </router-link>

          <BookmarkButton :article-id="a.id" :saved="true"
                          @changed="v => onChanged(a.id, v)" />
        </li>
      </ul>
    </section>
  </BossShell>
</template>

<style scoped>
.intro { max-width: 900px; margin: 0 auto;
         padding: var(--s-9) var(--s-7) var(--s-6);
         border-bottom: 1px solid var(--boss-line); }
.eyebrow { display: flex; align-items: center; gap: var(--s-4);
           font-family: var(--font-ui); font-size: var(--t-xs);
           letter-spacing: var(--track-caps); text-transform: uppercase;
           color: var(--boss-gold); margin: 0 0 var(--s-4); }
.rule { width: 50px; height: 1px; background: var(--boss-gold-deep); }
h1 { font-family: var(--font-serif); font-size: var(--t-3xl); font-weight: 400;
     margin: 0 0 var(--s-3); color: var(--boss-text);
     line-height: var(--lh-tight); }
.sub { color: var(--boss-text-muted); font-size: var(--t-md); margin: 0;
       font-family: var(--font-ui); }

.wrap { max-width: 900px; margin: 0 auto; padding: var(--s-7) var(--s-7) var(--s-9); }
.state { color: var(--boss-text-muted); font-family: var(--font-ui); }

.empty { text-align: center; padding: var(--s-9) var(--s-5);
         font-family: var(--font-ui); }
.big { font-family: var(--font-serif); font-size: var(--t-xl);
       color: var(--boss-text); margin: 0 0 var(--s-3); }
.empty p { color: var(--boss-text-muted); font-size: var(--t-sm);
           line-height: var(--lh-body); max-width: 44ch; margin: 0 auto; }
.cta { display: inline-block; margin-top: var(--s-5);
       border: 1px solid var(--boss-gold); color: var(--boss-gold);
       padding: var(--s-3) var(--s-5); font-size: var(--t-xs);
       letter-spacing: var(--track-caps); text-transform: uppercase;
       transition: background var(--dur-base) var(--ease-out),
                   color var(--dur-base) var(--ease-out); }
.cta:hover { background: var(--boss-gold); color: var(--boss-bg); }

.list { list-style: none; margin: 0; padding: 0; }
.list li { display: flex; align-items: flex-start; gap: var(--s-4);
           padding: var(--s-5) 0; border-bottom: 1px solid var(--boss-line); }
.card { display: flex; gap: var(--s-5); flex: 1; min-width: 0; color: inherit; }
.thumb { width: 160px; flex-shrink: 0; aspect-ratio: 4/3; overflow: hidden; }
.thumb img { width: 100%; height: 100%; object-fit: cover;
             transition: transform var(--dur-slow) var(--ease-out); }
.card:hover .thumb img { transform: scale(1.04); }

.body { min-width: 0; }
.cat { font-family: var(--font-ui); font-size: var(--t-xs);
       letter-spacing: var(--track-caps); text-transform: uppercase;
       color: var(--boss-gold); }
.lock { color: var(--boss-gold-deep); }
h2 { font-family: var(--font-serif); font-size: var(--t-lg); font-weight: 600;
     margin: var(--s-2) 0; line-height: var(--lh-snug); color: var(--boss-text);
     transition: color var(--dur-fast) var(--ease-out); }
.card:hover h2 { color: var(--boss-gold-bright); }
.body p { font-family: var(--font-ui); font-size: var(--t-sm);
          line-height: var(--lh-body); color: var(--boss-text-muted);
          margin: 0 0 var(--s-3); }
.meta { font-family: var(--font-ui); font-size: var(--t-xs);
        color: var(--boss-text-faint); }

@media (max-width: 700px) {
  .intro, .wrap { padding-left: var(--s-4); padding-right: var(--s-4); }
  h1 { font-size: var(--t-2xl); }
  .thumb { display: none; }
}
</style>
