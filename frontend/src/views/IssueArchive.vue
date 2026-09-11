<script setup>
import { ref, onMounted } from 'vue'
import api from '../services/api'
import BossShell from '../components/BossShell.vue'
import { useReveal, useIntro } from '../composables/useReveal'

const issues = ref([])
const loading = ref(true)

onMounted(async () => {
  document.title = 'All Issues — BOSS Magazine PH'
  try {
    const { data } = await api.get('/content/issues/')
    issues.value = data.results ?? data
  } finally { loading.value = false }
})

useIntro('[data-intro]')
useReveal('[data-reveal]')

const fmt = (d) => d ? new Date(d).toLocaleDateString('en-PH',
  { year: 'numeric', month: 'long' }) : ''
</script>

<template>
  <BossShell>
    <header class="intro">
      <p class="eyebrow" data-intro>
        <span>Portfolio</span><span class="rule" aria-hidden="true"></span>
      </p>
      <h1 data-intro>All Issues</h1>
      <p class="sub" data-intro>
        Every issue of BOSS Magazine PH — select any cover to read.
      </p>
    </header>

    <section class="wrap" aria-label="Published issues">
      <p v-if="loading" class="state" role="status">Loading issues…</p>
      <p v-else-if="!issues.length" class="state">No issues published yet.</p>

      <div v-else class="grid">
        <router-link v-for="i in issues" :key="i.id" :to="`/issues/${i.id}`"
                     class="issue" data-reveal>
          <div class="cover">
            <img v-if="i.cover_image" :src="i.cover_image"
                 :alt="`Cover of Issue ${i.number}, ${i.title}`" loading="lazy" />
            <div v-else class="placeholder" aria-hidden="true">
              <span class="n">№ {{ i.number }}</span>
              <span class="t">{{ i.title }}</span>
            </div>
            <span class="sheen" aria-hidden="true"></span>
          </div>
          <div class="meta">
            <span class="num">Issue {{ i.number }}</span>
            <h2>{{ i.title }}</h2>
            <p>{{ fmt(i.published_at) }} · {{ i.article_count }} articles</p>
          </div>
        </router-link>
      </div>
    </section>
  </BossShell>
</template>

<style scoped>
.intro { max-width: 1200px; margin: 0 auto; padding: var(--s-9) var(--s-7) var(--s-7);
         border-bottom: 1px solid var(--boss-line); }
.eyebrow { display: flex; align-items: center; gap: var(--s-4);
           font-size: var(--t-xs); letter-spacing: var(--track-caps);
           text-transform: uppercase; color: var(--boss-gold); margin: 0 0 var(--s-5); }
.rule { width: 60px; height: 1px; background: var(--boss-gold-deep); }
h1 { font-family: var(--font-serif); font-size: var(--t-3xl); font-weight: 400;
     margin: 0 0 var(--s-4); color: var(--boss-text); line-height: var(--lh-tight); }
.sub { color: var(--boss-text-muted); font-size: var(--t-md); margin: 0; }

.wrap { max-width: 1200px; margin: 0 auto; padding: var(--s-8) var(--s-7) 0; }
.state { color: var(--boss-text-muted); text-align: center; padding: var(--s-9); }

.grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(230px, 1fr));
        gap: var(--s-8) var(--s-6); }
.issue { display: block; }
.cover { position: relative; aspect-ratio: 3/4; overflow: hidden;
         background: var(--boss-surface-2);
         box-shadow: 0 6px 24px rgba(0,0,0,.5);
         transition: transform var(--dur-base) var(--ease-out),
                     box-shadow var(--dur-base) var(--ease-out); }
.issue:hover .cover { transform: translateY(-6px);
                      box-shadow: var(--shadow-gold), 0 14px 40px rgba(0,0,0,.6); }
.cover img { width: 100%; height: 100%; object-fit: cover; }
.placeholder { width: 100%; height: 100%; display: flex; flex-direction: column;
               align-items: center; justify-content: center; gap: var(--s-4);
               padding: var(--s-5); text-align: center;
               background: linear-gradient(150deg, #141210, #1f1a12); }
.placeholder .n { font-size: var(--t-sm); letter-spacing: var(--track-wide);
                  color: var(--boss-gold-deep); }
.placeholder .t { font-family: var(--font-serif); font-size: var(--t-lg);
                  color: var(--boss-text); line-height: var(--lh-snug); }

/* A slow sheen across the cover on hover, like light on paper stock. */
.sheen { position: absolute; inset: 0; pointer-events: none;
         background: linear-gradient(105deg, transparent 40%,
                     rgba(255,255,255,.13) 50%, transparent 60%);
         transform: translateX(-100%);
         transition: transform var(--dur-slow) var(--ease-out); }
.issue:hover .sheen { transform: translateX(100%); }

.meta { margin-top: var(--s-4); }
.num { font-size: var(--t-xs); letter-spacing: var(--track-caps);
       text-transform: uppercase; color: var(--boss-gold); }
.meta h2 { font-family: var(--font-serif); font-size: var(--t-lg);
           font-weight: 600; margin: var(--s-2) 0 var(--s-1);
           line-height: var(--lh-snug); color: var(--boss-text);
           transition: color var(--dur-fast) var(--ease-out); }
.issue:hover .meta h2 { color: var(--boss-gold-bright); }
.meta p { font-size: var(--t-xs); color: var(--boss-text-faint); margin: 0; }

@media (max-width: 760px) {
  .intro, .wrap { padding-left: var(--s-4); padding-right: var(--s-4); }
  h1 { font-size: var(--t-2xl); }
}
</style>
