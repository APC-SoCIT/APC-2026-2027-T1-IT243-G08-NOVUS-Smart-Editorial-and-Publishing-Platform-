<script setup>
import { onMounted } from 'vue'
import { useRoute } from 'vue-router'
import BossShell from '../components/BossShell.vue'

const route = useRoute()
onMounted(() => { document.title = 'Page not found — BOSS Magazine PH' })
</script>

<template>
  <BossShell>
    <section class="nf" aria-labelledby="nf-heading">
      <p class="code">404</p>
      <h1 id="nf-heading">This page isn't here</h1>
      <p class="sub">
        Nothing is published at <code>{{ route.fullPath }}</code>. The link may be
        old, or the address may have a typo.
      </p>
      <div class="actions">
        <router-link to="/read" class="primary">Go to the magazine</router-link>
        <router-link to="/issues" class="ghost">Browse issues</router-link>
      </div>
    </section>
  </BossShell>
</template>

<style scoped>
.nf { max-width: 720px; margin: 0 auto; padding: var(--s-9) var(--s-7);
      min-height: 50vh; }
.code { margin: 0 0 var(--s-3); font-size: var(--t-xs); font-weight: 700;
        letter-spacing: var(--track-caps); color: var(--boss-gold); }
h1 { margin: 0 0 var(--s-5); font-family: var(--font-serif);
     font-size: var(--t-2xl); line-height: 1.1; color: var(--boss-text); }
.sub { margin: 0; font-size: var(--t-base); line-height: var(--lh-body);
       color: var(--boss-text-muted); max-width: 60ch; }
.sub code { word-break: break-all; color: var(--boss-text); }
.actions { display: flex; gap: var(--s-5); align-items: center;
           margin-top: var(--s-7); flex-wrap: wrap; }
.primary { background: var(--boss-gold); color: var(--boss-bg);
           padding: var(--s-4) var(--s-6); font-size: var(--t-xs);
           font-weight: 700; letter-spacing: var(--track-caps);
           text-transform: uppercase; }
.primary:hover { background: var(--boss-gold-bright); }
.ghost { font-size: var(--t-xs); letter-spacing: var(--track-caps);
         text-transform: uppercase; color: var(--boss-text-muted); }
.ghost:hover { color: var(--boss-gold); }
</style>
