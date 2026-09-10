<script setup>
import { onMounted } from 'vue'
import BossShell from '../components/BossShell.vue'
import { useIntro, useReveal } from '../composables/useReveal'

onMounted(() => { document.title = 'About — BOSS Magazine PH' })
useIntro('[data-intro]')
useReveal('[data-reveal]')
</script>

<template>
  <BossShell>
    <header class="intro">
      <h1 data-intro>
        <span class="plain">About</span>
        <span class="brand">Boss Magazine Ph</span>
      </h1>
    </header>

    <section class="body" aria-labelledby="about-heading">
      <h2 id="about-heading" class="sr-only">About BOSS Magazine PH</h2>

      <div class="cols">
        <div class="text">
          <blockquote data-reveal>
            BOSS Magazine PH is the Philippines’ premier lifestyle and business
            publication — dedicated to celebrating Filipino excellence across
            entrepreneurship, culture, and society.
          </blockquote>

          <p data-reveal>
            Founded with a vision to give Filipino achievers a platform they
            deserve, BOSS Magazine PH has grown into a trusted voice for those
            who lead, inspire, and innovate. Each issue is a carefully curated
            collection of stories that reflect the power and prestige of the
            Filipino spirit.
          </p>

          <p data-reveal>
            From cover stories featuring the country’s most influential names to
            deep-dive features on emerging industries, BOSS Magazine PH is where
            ambition meets artistry.
          </p>

          <div class="actions" data-reveal>
            <router-link to="/issues" class="primary">Browse issues</router-link>
            <router-link to="/read" class="ghost">Read articles →</router-link>
          </div>
        </div>

        <div class="mark" data-reveal>
          <img src="/boss-logo.png" alt="BOSS Magazine PH logo" />
        </div>
      </div>

      <div class="colophon" data-reveal>
        <h3>Colophon</h3>
        <p>
          BOSS Magazine PH is published by BOSS Media Philippines Inc. The
          editorial workflow behind every issue runs on NOVUS, a smart editorial
          and publishing platform built for the newsroom.
        </p>
        <router-link to="/staff/login" class="staff">Editorial team login →</router-link>
      </div>
    </section>
  </BossShell>
</template>

<style scoped>
.intro { max-width: 1200px; margin: 0 auto;
         padding: var(--s-9) var(--s-7) var(--s-7);
         border-bottom: 1px solid var(--boss-line); }
h1 { margin: 0; font-family: var(--font-serif); line-height: 1.05; }
.plain { display: block; font-size: var(--t-2xl); color: var(--boss-text);
         font-weight: 400; }
.brand { display: block; font-size: var(--t-3xl); color: var(--boss-gold);
         font-style: italic; font-weight: 500; }

.body { max-width: 1200px; margin: 0 auto; padding: var(--s-8) var(--s-7) 0; }
.cols { display: grid; grid-template-columns: 1.4fr 1fr; gap: var(--s-8);
        align-items: start; }

blockquote { margin: 0 0 var(--s-6); padding-left: var(--s-5);
             border-left: 2px solid var(--boss-gold);
             font-family: var(--font-serif); font-size: var(--t-md);
             line-height: var(--lh-body); color: var(--boss-text); }
.text p { font-size: var(--t-base); line-height: var(--lh-body);
          color: var(--boss-text-muted); margin: 0 0 var(--s-5); max-width: 60ch; }

.actions { display: flex; gap: var(--s-4); align-items: center;
           margin-top: var(--s-6); flex-wrap: wrap; }
.primary { background: var(--boss-gold); color: var(--boss-bg);
           padding: var(--s-4) var(--s-6); font-size: var(--t-xs);
           font-weight: 700; letter-spacing: var(--track-caps);
           text-transform: uppercase;
           transition: background var(--dur-base) var(--ease-out); }
.primary:hover { background: var(--boss-gold-bright); }
.ghost { font-size: var(--t-xs); letter-spacing: var(--track-caps);
         text-transform: uppercase; color: var(--boss-text-muted);
         transition: color var(--dur-fast) var(--ease-out); }
.ghost:hover { color: var(--boss-gold); }

.mark { border: 1px solid var(--boss-line); background: var(--boss-surface);
        padding: var(--s-8); display: flex; align-items: center;
        justify-content: center; }
.mark img { max-width: 260px; }

.colophon { margin-top: var(--s-9); padding-top: var(--s-6);
            border-top: 1px solid var(--boss-line); max-width: 60ch; }
.colophon h3 { font-size: var(--t-xs); letter-spacing: var(--track-caps);
               text-transform: uppercase; color: var(--boss-gold);
               margin: 0 0 var(--s-3); }
.colophon p { font-size: var(--t-sm); line-height: var(--lh-body);
              color: var(--boss-text-muted); margin: 0 0 var(--s-4); }
.staff { font-size: var(--t-xs); letter-spacing: var(--track-caps);
         text-transform: uppercase; color: var(--boss-text-faint); }
.staff:hover { color: var(--boss-gold); }

@media (max-width: 860px) {
  .cols { grid-template-columns: 1fr; }
  .intro, .body { padding-left: var(--s-4); padding-right: var(--s-4); }
  .brand { font-size: var(--t-2xl); }
}
</style>
