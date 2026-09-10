<script setup>
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import api from '../services/api'

const route = useRoute()
const issue = ref(null)
const loading = ref(true)
const missing = ref(false)
const viewing = ref(false)

onMounted(async () => {
  try {
    const { data } = await api.get(`/content/issues/${route.params.id}/`)
    issue.value = data
  } catch { missing.value = true }
  finally { loading.value = false }
})

const fmt = (d) => d ? new Date(d).toLocaleDateString('en-PH',
  { year: 'numeric', month: 'long', day: 'numeric' }) : ''

const isPdf = () => (issue.value?.replica_url || '').toLowerCase().endsWith('.pdf')
</script>

<template>
  <div class="site">
    <nav>
      <router-link to="/read" class="brand">BOSS</router-link>
      <router-link to="/issues" class="back">← All issues</router-link>
    </nav>

    <p v-if="loading" class="state">Loading…</p>
    <p v-else-if="missing" class="state">That issue isn't available.</p>

    <main v-else>
      <div class="head">
        <div class="cover">
          <img v-if="issue.cover_image" :src="issue.cover_image" alt="" />
          <div v-else class="placeholder">
            <span class="num">№ {{ issue.number }}</span>
            <span class="ttl">{{ issue.title }}</span>
          </div>
        </div>

        <div class="info">
          <span class="n">Issue {{ issue.number }}</span>
          <h1>{{ issue.title }}</h1>
          <p class="date">
            {{ fmt(issue.published_at) }} · {{ issue.article_count }} articles
          </p>

          <template v-if="issue.replica_available">
            <div v-if="issue.can_access" class="actions">
              <button class="read" @click="viewing = true">Read this issue</button>
              <a class="dl" :href="issue.replica_url" download>Download PDF</a>
            </div>
            <div v-else class="locked">
              <p><b>Subscribers only.</b> Contact the editorial team to activate
                 a subscription.</p>
              <router-link to="/login" class="link">Sign in</router-link>
            </div>
          </template>
          <p v-else class="nodigital">
            No digital edition is available for this issue.
          </p>
        </div>
      </div>

      <h3>In this issue</h3>
      <ul class="arts">
        <li v-for="a in issue.articles" :key="a.id">
          <router-link :to="`/read/${a.id}`">
            <span class="cat">
              {{ a.category || 'General' }}
              <span v-if="a.is_premium" class="lock">· Subscriber</span>
            </span>
            <h4>{{ a.title }}</h4>
            <p v-if="a.excerpt">{{ a.excerpt }}</p>
            <small>{{ a.author_name }} · {{ a.reading_time }} min read</small>
          </router-link>
        </li>
      </ul>
    </main>

    <div v-if="viewing" class="viewer" @click.self="viewing = false">
      <div class="vtop">
        <span>Issue {{ issue.number }} — {{ issue.title }}</span>
        <div>
          <a :href="issue.replica_url" download class="vdl">Download</a>
          <button class="vclose" @click="viewing = false">Close</button>
        </div>
      </div>
      <iframe v-if="isPdf()" :src="issue.replica_url" title="Digital edition"></iframe>
      <div v-else class="notpdf">
        <p>This layout can't be read in the browser. Download it instead.</p>
        <a :href="issue.replica_url" download class="dl">Download the file</a>
      </div>
    </div>
  </div>
</template>

<style scoped>
.site { font-family: Georgia, serif; }
nav { display: flex; align-items: center; justify-content: space-between;
      padding: 20px 32px; border-bottom: 1px solid #eee; }
.brand { font-size: 26px; letter-spacing: 5px; font-weight: 700; color: inherit; }
.back { font-family: system-ui; font-size: 13px; color: #888; }
main { max-width: 900px; margin: 0 auto; padding: 44px 24px 80px; }
.head { display: flex; gap: 44px; margin-bottom: 52px; }
.cover { width: 250px; flex-shrink: 0; aspect-ratio: 3/4; border-radius: 6px;
         overflow: hidden; box-shadow: 0 6px 24px rgba(0,0,0,.16); }
.cover img { width: 100%; height: 100%; object-fit: cover; display: block; }
.placeholder { width: 100%; height: 100%; background: #0d1526; color: #fff;
               display: flex; flex-direction: column; justify-content: center;
               align-items: center; gap: 14px; padding: 26px; text-align: center; }
.num { font-size: 13px; letter-spacing: 3px; color: #7f8fab; }
.ttl { font-size: 23px; line-height: 1.3; }
.info { padding-top: 6px; }
.n { font-family: system-ui; font-size: 11px; letter-spacing: 1.4px;
     text-transform: uppercase; color: #4a7fb5; }
h1 { font-size: 36px; margin: 8px 0; line-height: 1.2; }
.date { font-family: system-ui; font-size: 13px; color: #999; margin: 0 0 26px; }
.actions { display: flex; gap: 10px; }
.read { border: 0; background: #111; color: #fff; padding: 12px 26px;
        border-radius: 8px; font-family: system-ui; font-weight: 600;
        font-size: 14px; cursor: pointer; }
.dl { border: 1px solid #ccc; padding: 12px 22px; border-radius: 8px;
      font-family: system-ui; font-size: 14px; color: #445; }
.locked { background: #fdf9f0; border: 1px solid #f0e3c8; border-radius: 10px;
          padding: 16px 18px; font-family: system-ui; }
.locked p { margin: 0 0 9px; font-size: 13px; line-height: 1.6; color: #6b5a3a; }
.link { font-size: 13px; color: #4a7fb5; }
.nodigital { font-family: system-ui; font-size: 13px; color: #aaa; }
h3 { font-family: system-ui; font-size: 12px; letter-spacing: 1.4px;
     text-transform: uppercase; color: #999; margin: 0 0 20px;
     border-top: 1px solid #eee; padding-top: 24px; }
.arts { list-style: none; padding: 0; margin: 0; }
.arts li { border-bottom: 1px solid #f0f0f0; }
.arts a { display: block; padding: 20px 0; color: inherit; }
.arts a:hover { background: #fcfcfc; }
.cat { font-family: system-ui; font-size: 10px; letter-spacing: 1.2px;
       text-transform: uppercase; color: #4a7fb5; }
.lock { color: #96631a; }
.arts h4 { font-size: 21px; margin: 7px 0; line-height: 1.3; }
.arts p { font-size: 14px; color: #666; margin: 0 0 7px; line-height: 1.55; }
.arts small { font-family: system-ui; font-size: 12px; color: #aaa; }
.viewer { position: fixed; inset: 0; background: #1a1a1a; z-index: 100;
          display: flex; flex-direction: column; }
.vtop { display: flex; justify-content: space-between; align-items: center;
        padding: 12px 20px; color: #fff; font-family: system-ui; font-size: 13px;
        background: #111; }
.vtop div { display: flex; gap: 10px; align-items: center; }
.vdl { color: #9fb0cc; font-size: 13px; }
.vclose { border: 1px solid #444; background: none; color: #fff;
          padding: 6px 14px; border-radius: 6px; font-size: 13px; cursor: pointer; }
iframe { flex: 1; border: 0; background: #333; }
.notpdf { flex: 1; display: flex; flex-direction: column; align-items: center;
          justify-content: center; gap: 18px; color: #ccc; font-family: system-ui; }
.notpdf p { max-width: 380px; text-align: center; line-height: 1.6; }
.notpdf .dl { border-color: #555; color: #fff; }
.state { color: #888; font-family: system-ui; text-align: center; padding: 60px; }
</style>
