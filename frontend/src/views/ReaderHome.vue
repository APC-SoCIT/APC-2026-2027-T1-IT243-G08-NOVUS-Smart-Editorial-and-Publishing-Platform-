<script setup>
import { ref, onMounted, computed } from 'vue'
import api from '../services/api'

const articles = ref([])
const loading = ref(true)
const active = ref('All')

const categories = computed(() => {
  const set = new Set(articles.value.map(a => a.category).filter(Boolean))
  return ['All', ...set]
})
const shown = computed(() =>
  active.value === 'All' ? articles.value : articles.value.filter(a => a.category === active.value))

onMounted(async () => {
  try {
    const { data } = await api.get('/content/articles/')
    articles.value = data.results ?? data
  } finally { loading.value = false }
})

const fmt = (d) => d ? new Date(d).toLocaleDateString('en-PH',
  { year: 'numeric', month: 'long', day: 'numeric' }) : ''
</script>

<template>
  <div class="site">
    <nav>
      <span class="brand">BOSS</span>
      <div class="links">
        <a v-for="c in categories" :key="c"
           :class="{ on: active === c }" @click="active = c">{{ c }}</a>
      </div>
      <router-link to="/login" class="signin">Sign in</router-link>
    </nav>

    <main>
      <p v-if="loading" class="state">Loading…</p>
      <p v-else-if="!articles.length" class="state">No articles published yet.</p>

      <template v-else>
        <article v-if="shown.length" class="hero">
          <span class="kicker">FEATURED</span>
          <h1>{{ shown[0].title }}</h1>
          <p class="meta">{{ shown[0].author_name }} · {{ fmt(shown[0].published_at) }}</p>
          <router-link :to="`/read/${shown[0].id}`" class="cta">Read now →</router-link>
        </article>

        <h3 v-if="shown.length > 1">Latest articles</h3>
        <div class="grid">
          <router-link v-for="a in shown.slice(1)" :key="a.id"
                       :to="`/read/${a.id}`" class="card">
            <span class="cat">{{ a.category || 'General' }}</span>
            <h4>{{ a.title }}</h4>
            <p>{{ a.author_name }} · {{ fmt(a.published_at) }}</p>
          </router-link>
        </div>
      </template>
    </main>
  </div>
</template>

<style scoped>
.site { font-family: Georgia, serif; }
nav { display: flex; align-items: center; gap: 28px; padding: 18px 32px; border-bottom: 1px solid #eee; }
.brand { font-size: 26px; letter-spacing: 5px; font-weight: 700; }
.links { display: flex; gap: 18px; flex: 1; font-family: system-ui; font-size: 13px; }
.links a { cursor: pointer; color: #666; letter-spacing: .5px; }
.links a.on { color: #111; font-weight: 600; }
.signin { font-family: system-ui; font-size: 13px; color: #4a7fb5; }
main { max-width: 940px; margin: 0 auto; padding: 36px 24px 80px; }
.hero { background: #0d1526; color: #fff; border-radius: 12px; padding: 46px 40px; margin-bottom: 40px; }
.kicker { font-family: system-ui; font-size: 10px; letter-spacing: 2px; opacity: .7; }
.hero h1 { font-size: 40px; line-height: 1.15; margin: 12px 0 10px; }
.hero .meta { font-family: system-ui; font-size: 13px; opacity: .75; margin: 0 0 22px; }
.cta { font-family: system-ui; font-size: 14px; color: #fff; border: 1px solid rgba(255,255,255,.4);
       padding: 9px 18px; border-radius: 6px; }
h3 { font-family: system-ui; font-size: 13px; letter-spacing: 1px; text-transform: uppercase;
     color: #888; margin: 0 0 16px; }
.grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: 22px; }
.card { border: 1px solid #eee; border-radius: 10px; padding: 20px; color: inherit; }
.card:hover { border-color: #ccc; }
.cat { font-family: system-ui; font-size: 10px; letter-spacing: 1px; color: #4a7fb5; }
.card h4 { font-size: 19px; line-height: 1.3; margin: 8px 0; }
.card p { font-family: system-ui; font-size: 12px; color: #888; margin: 0; }
.state { color: #888; font-family: system-ui; }
</style>
