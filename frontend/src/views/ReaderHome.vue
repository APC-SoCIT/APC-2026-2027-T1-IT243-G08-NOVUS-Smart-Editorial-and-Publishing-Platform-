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
  active.value === 'All'
    ? articles.value
    : articles.value.filter(a => a.category === active.value))

// The featured article takes the banner; otherwise the most recent piece
// with a hero image, falling back to the most recent of any kind.
const lead = computed(() => {
  const list = shown.value
  return list.find(a => a.is_featured)
    ?? list.find(a => a.hero_image)
    ?? list[0]
})
const rest = computed(() => shown.value.filter(a => a.id !== lead.value?.id))

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
      <router-link to="/read" class="brand">BOSS</router-link>
      <div class="links">
        <a v-for="c in categories" :key="c"
           :class="{ on: active === c }" @click="active = c">{{ c }}</a>
      </div>
      <router-link to="/issues" class="issues">Issues</router-link>
      <router-link to="/login" class="signin">Sign in</router-link>
    </nav>

    <main>
      <p v-if="loading" class="state">Loading…</p>
      <p v-else-if="!articles.length" class="state">Nothing published yet.</p>

      <template v-else>
        <router-link v-if="lead" :to="`/read/${lead.id}`" class="lead"
                     :class="{ 'no-img': !lead.hero_image }">
          <div v-if="lead.hero_image" class="lead-img">
            <img :src="lead.hero_image" alt="" />
          </div>
          <div class="lead-text">
            <span class="kicker">
              {{ lead.category || 'Featured' }}
              <span v-if="lead.is_premium" class="lock">· Subscriber</span>
            </span>
            <h1>{{ lead.title }}</h1>
            <p v-if="lead.excerpt" class="stand">{{ lead.excerpt }}</p>
            <p class="meta">
              {{ lead.author_name }} · {{ fmt(lead.published_at) }}
              · {{ lead.reading_time }} min read
            </p>
          </div>
        </router-link>

        <h3 v-if="rest.length">Latest</h3>
        <div class="grid">
          <router-link v-for="a in rest" :key="a.id" :to="`/read/${a.id}`"
                       class="card" :class="{ 'no-img': !a.hero_image }">
            <div v-if="a.hero_image" class="thumb">
              <img :src="a.hero_image" alt="" />
            </div>
            <span class="cat">
              {{ a.category || 'General' }}
              <span v-if="a.is_premium" class="lock">· Subscriber</span>
            </span>
            <h4>{{ a.title }}</h4>
            <p v-if="a.excerpt" class="ex">{{ a.excerpt }}</p>
            <p class="meta">
              {{ a.author_name }} · {{ a.reading_time }} min read
            </p>
          </router-link>
        </div>
      </template>
    </main>

    <footer>
      <span>BOSS Magazine PH</span>
      <router-link to="/staff/login">Editorial login</router-link>
    </footer>
  </div>
</template>

<style scoped>
.site { font-family: Georgia, serif; }
nav { display: flex; align-items: center; gap: 28px; padding: 20px 32px;
      border-bottom: 1px solid #eee; position: sticky; top: 0; background: #fff; z-index: 5; }
.brand { font-size: 26px; letter-spacing: 5px; font-weight: 700; color: inherit; }
.links { display: flex; gap: 20px; flex: 1; font-family: system-ui; font-size: 12px; }
.links a { cursor: pointer; color: #777; letter-spacing: .8px; text-transform: uppercase; }
.links a.on { color: #111; font-weight: 600; }
.issues { font-family: system-ui; font-size: 12px; color: #777;
          letter-spacing: .8px; text-transform: uppercase; }
.signin { font-family: system-ui; font-size: 13px; color: #4a7fb5; }

main { max-width: 1040px; margin: 0 auto; padding: 40px 24px 60px; }

.lead { display: block; color: inherit; margin-bottom: 52px; }
.lead-img { border-radius: 12px; overflow: hidden; margin-bottom: 22px; }
.lead-img img { width: 100%; height: 420px; object-fit: cover; display: block; }
.lead.no-img { background: #0d1526; color: #fff; border-radius: 12px; padding: 52px 44px; }
.lead.no-img .stand, .lead.no-img .meta { color: rgba(255,255,255,.72); }
.lead-text { max-width: 720px; }
.kicker { font-family: system-ui; font-size: 10px; letter-spacing: 2px;
          text-transform: uppercase; color: #4a7fb5; }
.lead h1 { font-size: 42px; line-height: 1.15; margin: 10px 0 12px; }
.stand { font-size: 19px; line-height: 1.55; color: #555; margin: 0 0 14px; }
.meta { font-family: system-ui; font-size: 12px; color: #999; margin: 0; }

h3 { font-family: system-ui; font-size: 12px; letter-spacing: 1.4px;
     text-transform: uppercase; color: #999; margin: 0 0 20px;
     border-top: 1px solid #eee; padding-top: 22px; }
.grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 32px; }
.card { color: inherit; }
.thumb { border-radius: 8px; overflow: hidden; margin-bottom: 12px; }
.thumb img { width: 100%; height: 180px; object-fit: cover; display: block;
             transition: transform .3s; }
.card:hover .thumb img { transform: scale(1.03); }
.card.no-img { border-left: 3px solid #e6e6e6; padding-left: 16px; }
.cat { font-family: system-ui; font-size: 10px; letter-spacing: 1.2px;
       text-transform: uppercase; color: #4a7fb5; }
.lock { color: #96631a; }
.lead.no-img .lock { color: #d9ad6a; }
.card h4 { font-size: 20px; line-height: 1.3; margin: 7px 0; }
.ex { font-size: 14px; line-height: 1.55; color: #666; margin: 0 0 9px; }

footer { display: flex; justify-content: space-between; max-width: 1040px;
         margin: 0 auto; padding: 26px 24px 50px; border-top: 1px solid #eee;
         font-family: system-ui; font-size: 12px; color: #999; }
footer a { color: #4a7fb5; }
.state { color: #888; font-family: system-ui; }
</style>
