<script setup>
import { ref, onMounted, computed } from 'vue'
import api from '../services/api'
import BossShell from '../components/BossShell.vue'
import { useReveal, useIntro } from '../composables/useReveal'

const articles = ref([])
const loading = ref(true)
const active = ref('All')

const categories = computed(() => {
  const set = new Set(articles.value.map(a => a.category).filter(Boolean))
  return ['All', ...set]
})

const shown = computed(() =>
  active.value === 'All'
    ? articles.value
    : articles.value.filter(a => a.category === active.value))

const lead = computed(() => {
  const list = shown.value
  return list.find(a => a.is_featured) ?? list.find(a => a.hero_image) ?? list[0]
})
const rest = computed(() => shown.value.filter(a => a.id !== lead.value?.id))

onMounted(async () => {
  try {
    const { data } = await api.get('/content/articles/')
    articles.value = data.results ?? data
  } finally { loading.value = false }
})

useIntro('[data-intro]')
useReveal('[data-reveal]')

const fmt = (d) => d ? new Date(d).toLocaleDateString('en-PH',
  { year: 'numeric', month: 'long', day: 'numeric' }) : ''
</script>

<template>
  <BossShell>
    <!-- lead -->
    <section class="lead-wrap" aria-labelledby="lead-heading">
      <p v-if="loading" class="state" role="status">Loading articles…</p>
      <p v-else-if="!articles.length" class="state">No articles published yet.</p>

      <router-link v-else-if="lead" :to="`/read/${lead.id}`" class="lead"
                   :class="{ 'no-img': !lead.hero_image }">
        <div v-if="lead.hero_image" class="lead-img">
          <img :src="lead.hero_image"
               :alt="lead.hero_caption || `Cover image for ${lead.title}`" />
          <div class="scrim" aria-hidden="true"></div>
        </div>
        <div class="lead-text">
          <span class="kicker" data-intro>
            {{ lead.category || 'Featured' }}
            <span v-if="lead.is_premium" class="lock">· Subscriber</span>
          </span>
          <h1 id="lead-heading" data-intro>{{ lead.title }}</h1>
          <p v-if="lead.excerpt" class="stand" data-intro>{{ lead.excerpt }}</p>
          <p class="meta" data-intro>
            {{ lead.author_name }} · {{ fmt(lead.published_at) }}
            · {{ lead.reading_time }} min read
          </p>
          <span class="readnow" data-intro>Read the story →</span>
        </div>
      </router-link>
    </section>

    <!-- filters -->
    <section v-if="categories.length > 1" class="filters"
             aria-label="Filter articles by category">
      <button v-for="c in categories" :key="c" :class="{ on: active === c }"
              :aria-pressed="active === c" @click="active = c">{{ c }}</button>
    </section>

    <!-- grid -->
    <section v-if="rest.length" class="grid-wrap" aria-labelledby="latest-heading">
      <h2 id="latest-heading" class="section-title">Latest</h2>
      <div class="grid">
        <router-link v-for="a in rest" :key="a.id" :to="`/read/${a.id}`"
                     class="card" :class="{ 'no-img': !a.hero_image }" data-reveal>
          <div v-if="a.hero_image" class="thumb">
            <img :src="a.hero_image" :alt="`Cover image for ${a.title}`" loading="lazy" />
          </div>
          <span class="cat">
            {{ a.category || 'General' }}
            <span v-if="a.is_premium" class="lock">· Subscriber</span>
          </span>
          <h3>{{ a.title }}</h3>
          <p v-if="a.excerpt" class="ex">{{ a.excerpt }}</p>
          <p class="byline">By {{ a.author_name }} · {{ a.reading_time }} min</p>
        </router-link>
      </div>
    </section>
  </BossShell>
</template>

<style scoped>
.state { color: var(--boss-text-muted); text-align: center; padding: var(--s-9); }

.lead-wrap { max-width: 1200px; margin: 0 auto; padding: var(--s-6) var(--s-7) 0; }
.lead { display: block; position: relative; border-radius: var(--r-lg);
        overflow: hidden; min-height: 520px; display: flex; align-items: flex-end; }
.lead-img { position: absolute; inset: 0; }
.lead-img img { width: 100%; height: 100%; object-fit: cover;
                transition: transform var(--dur-slow) var(--ease-out); }
.lead:hover .lead-img img { transform: scale(1.03); }
.scrim { position: absolute; inset: 0;
         background: linear-gradient(0deg, rgba(10,10,10,.94) 0%,
                     rgba(10,10,10,.55) 45%, rgba(10,10,10,.15) 100%); }
.lead.no-img { background: linear-gradient(140deg, #141210 0%, #1f1a12 100%);
               border: 1px solid var(--boss-line); min-height: 380px; }
.lead-text { position: relative; padding: var(--s-8) var(--s-7); max-width: 760px; }

.kicker { display: inline-block; font-size: var(--t-xs);
          letter-spacing: var(--track-caps); text-transform: uppercase;
          color: var(--boss-gold); margin-bottom: var(--s-3); }
.lock { color: var(--boss-gold-deep); }

.lead h1 { font-family: var(--font-serif); font-size: var(--t-3xl);
           line-height: var(--lh-tight); margin: 0 0 var(--s-4);
           font-weight: 600; color: var(--boss-text); }
.stand { font-size: var(--t-md); line-height: var(--lh-body);
         color: var(--boss-text-muted); margin: 0 0 var(--s-4); max-width: 620px; }
.meta { font-size: var(--t-sm); color: var(--boss-text-faint); margin: 0 0 var(--s-5); }
.readnow { font-size: var(--t-xs); letter-spacing: var(--track-caps);
           text-transform: uppercase; color: var(--boss-gold);
           border-bottom: 1px solid transparent; padding-bottom: 2px;
           transition: border-color var(--dur-base) var(--ease-out); }
.lead:hover .readnow { border-bottom-color: var(--boss-gold); }

.filters { max-width: 1200px; margin: var(--s-7) auto 0; padding: 0 var(--s-7);
           display: flex; gap: var(--s-2); flex-wrap: wrap; }
.filters button { background: transparent; border: 1px solid var(--boss-line);
                  color: var(--boss-text-muted); padding: var(--s-2) var(--s-4);
                  font-size: var(--t-xs); letter-spacing: var(--track-caps);
                  text-transform: uppercase; cursor: pointer;
                  transition: all var(--dur-fast) var(--ease-out); }
.filters button:hover { border-color: var(--boss-gold-deep); color: var(--boss-text); }
.filters button.on { background: var(--boss-gold); border-color: var(--boss-gold);
                     color: var(--boss-bg); font-weight: 600; }

.grid-wrap { max-width: 1200px; margin: var(--s-7) auto 0; padding: 0 var(--s-7); }
.section-title { font-size: var(--t-xs); letter-spacing: var(--track-caps);
                 text-transform: uppercase; color: var(--boss-text-faint);
                 border-top: 1px solid var(--boss-line);
                 padding-top: var(--s-5); margin: 0 0 var(--s-6); font-weight: 600; }

.grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
        gap: var(--s-7) var(--s-6); }
.card { display: block; }
.thumb { overflow: hidden; margin-bottom: var(--s-4); aspect-ratio: 16/10; }
.thumb img { width: 100%; height: 100%; object-fit: cover;
             transition: transform var(--dur-slow) var(--ease-out); }
.card:hover .thumb img { transform: scale(1.045); }
.card.no-img { border-left: 2px solid var(--boss-gold-deep); padding-left: var(--s-4); }
.cat { font-size: var(--t-xs); letter-spacing: var(--track-caps);
       text-transform: uppercase; color: var(--boss-gold); }
.card h3 { font-family: var(--font-serif); font-size: var(--t-lg);
           line-height: var(--lh-snug); margin: var(--s-2) 0 var(--s-3);
           font-weight: 600; transition: color var(--dur-fast) var(--ease-out); }
.card:hover h3 { color: var(--boss-gold-bright); }
.ex { font-size: var(--t-sm); line-height: var(--lh-body);
      color: var(--boss-text-muted); margin: 0 0 var(--s-3); }
.byline { font-size: var(--t-xs); letter-spacing: .04em; text-transform: uppercase;
          color: var(--boss-text-faint); margin: 0; }

@media (max-width: 760px) {
  .lead-wrap, .filters, .grid-wrap { padding-left: var(--s-4); padding-right: var(--s-4); }
  .lead-text { padding: var(--s-6) var(--s-4); }
  .lead h1 { font-size: var(--t-2xl); }
}
</style>
