<script setup>
import { ref, onMounted } from 'vue'
import api from '../services/api'

const issues = ref([])
const loading = ref(true)

onMounted(async () => {
  try {
    const { data } = await api.get('/content/issues/')
    issues.value = data.results ?? data
  } finally { loading.value = false }
})

const fmt = (d) => d ? new Date(d).toLocaleDateString('en-PH',
  { year: 'numeric', month: 'long' }) : ''
</script>

<template>
  <div class="site">
    <nav>
      <router-link to="/read" class="brand">BOSS</router-link>
      <div class="links">
        <router-link to="/read">Articles</router-link>
        <router-link to="/issues" class="on">Issues</router-link>
      </div>
      <router-link to="/login" class="signin">Sign in</router-link>
    </nav>

    <main>
      <header class="intro">
        <h1>The archive</h1>
        <p>Every issue of BOSS Magazine, to read online or download.</p>
      </header>

      <p v-if="loading" class="state">Loading…</p>
      <p v-else-if="!issues.length" class="state">No issues published yet.</p>

      <div v-else class="grid">
        <router-link v-for="i in issues" :key="i.id" :to="`/issues/${i.id}`"
                     class="issue">
          <div class="cover" :class="{ blank: !i.cover_image }">
            <img v-if="i.cover_image" :src="i.cover_image" alt="" />
            <div v-else class="placeholder">
              <span class="num">№ {{ i.number }}</span>
              <span class="ttl">{{ i.title }}</span>
            </div>
          </div>
          <div class="meta">
            <span class="n">Issue {{ i.number }}</span>
            <h4>{{ i.title }}</h4>
            <p>{{ fmt(i.published_at) }} · {{ i.article_count }} articles</p>
          </div>
        </router-link>
      </div>
    </main>
  </div>
</template>

<style scoped>
.site { font-family: Georgia, serif; }
nav { display: flex; align-items: center; gap: 28px; padding: 20px 32px;
      border-bottom: 1px solid #eee; }
.brand { font-size: 26px; letter-spacing: 5px; font-weight: 700; color: inherit; }
.links { display: flex; gap: 20px; flex: 1; font-family: system-ui; font-size: 12px; }
.links a { color: #777; letter-spacing: .8px; text-transform: uppercase; }
.links a.on { color: #111; font-weight: 600; }
.signin { font-family: system-ui; font-size: 13px; color: #4a7fb5; }

main { max-width: 1040px; margin: 0 auto; padding: 44px 24px 70px; }
.intro { margin-bottom: 40px; }
.intro h1 { font-size: 38px; margin: 0 0 8px; }
.intro p { color: #888; font-size: 16px; margin: 0; }

.grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
        gap: 34px; }
.issue { color: inherit; }
.cover { aspect-ratio: 3/4; border-radius: 6px; overflow: hidden;
         box-shadow: 0 4px 16px rgba(0,0,0,.13); transition: transform .25s; }
.issue:hover .cover { transform: translateY(-4px); }
.cover img { width: 100%; height: 100%; object-fit: cover; display: block; }
.placeholder { width: 100%; height: 100%; background: #0d1526; color: #fff;
               display: flex; flex-direction: column; justify-content: center;
               align-items: center; gap: 12px; padding: 24px; text-align: center; }
.num { font-size: 13px; letter-spacing: 3px; color: #7f8fab; }
.ttl { font-size: 21px; line-height: 1.3; }
.meta { margin-top: 14px; }
.n { font-family: system-ui; font-size: 10px; letter-spacing: 1.2px;
     text-transform: uppercase; color: #4a7fb5; }
.meta h4 { font-size: 18px; margin: 5px 0 4px; line-height: 1.3; }
.meta p { font-family: system-ui; font-size: 12px; color: #999; margin: 0; }
.state { color: #888; font-family: system-ui; }
</style>
