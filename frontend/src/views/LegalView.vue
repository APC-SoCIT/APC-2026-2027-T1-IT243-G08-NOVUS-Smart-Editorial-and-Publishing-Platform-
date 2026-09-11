<script setup>
import { computed, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import BossShell from '../components/BossShell.vue'
import { DOCS, ORG } from '../content/legal'
import { useIntro } from '../composables/useReveal'

const route = useRoute()
const doc = computed(() => DOCS[route.params.doc] || null)

const NAV = [
  { key: 'privacy', label: 'Privacy Policy' },
  { key: 'terms', label: 'Terms of Service' },
  { key: 'cookies', label: 'Cookie Policy' },
  { key: 'refunds', label: 'Refund Policy' },
]

function setTitle() {
  document.title = doc.value
    ? `${doc.value.title} — BOSS Magazine PH`
    : 'Legal — BOSS Magazine PH'
}
onMounted(setTitle)
watch(() => route.params.doc, () => { setTitle(); window.scrollTo(0, 0) })

useIntro('[data-intro]')

// Anchor id for each heading, so sections can be linked to directly.
const slug = (s) => s.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '')
</script>

<template>
  <BossShell>
    <div class="page">
      <nav class="side" aria-label="Legal documents">
        <h2>Legal</h2>
        <router-link v-for="n in NAV" :key="n.key" :to="`/legal/${n.key}`"
                     :class="{ on: route.params.doc === n.key }"
                     :aria-current="route.params.doc === n.key ? 'page' : undefined">
          {{ n.label }}
        </router-link>
      </nav>

      <main class="doc">
        <p v-if="!doc" class="state">That document isn’t available.</p>

        <template v-else>
          <header>
            <h1 data-intro>{{ doc.title }}</h1>
            <p class="summary" data-intro>{{ doc.summary }}</p>
            <p class="eff" data-intro>
              Effective {{ ORG.effective }} · {{ ORG.company }}
            </p>
          </header>

          <!-- Jump list: long documents need a way in. -->
          <nav class="toc" aria-label="On this page">
            <h2>On this page</h2>
            <ol>
              <li v-for="s in doc.sections.filter(x => x.heading)" :key="s.heading">
                <a :href="`#${slug(s.heading)}`">{{ s.heading }}</a>
              </li>
            </ol>
          </nav>

          <section v-for="(s, i) in doc.sections" :key="i" class="sec">
            <div v-if="s.type === 'notice'" class="notice" role="note">
              <span class="ntag">Please note</span>
              <p>{{ s.body }}</p>
            </div>

            <template v-else>
              <h2 :id="slug(s.heading)">{{ s.heading }}</h2>
              <p v-if="s.body">{{ s.body }}</p>
              <ul v-if="s.list">
                <li v-for="(item, j) in s.list" :key="j">{{ item }}</li>
              </ul>
            </template>
          </section>

          <footer class="end">
            <p>
              Questions about this document? Write to
              <a :href="`mailto:${ORG.email}`">{{ ORG.email }}</a>.
            </p>
          </footer>
        </template>
      </main>
    </div>
  </BossShell>
</template>

<style scoped>
.page { max-width: 1100px; margin: 0 auto; padding: var(--s-8) var(--s-7) 0;
        display: grid; grid-template-columns: 200px 1fr; gap: var(--s-8); }

.side { position: sticky; top: 100px; align-self: start;
        display: flex; flex-direction: column; gap: var(--s-2); }
.side h2 { font-size: var(--t-xs); letter-spacing: var(--track-caps);
           text-transform: uppercase; color: var(--boss-gold);
           margin: 0 0 var(--s-3); }
.side a { font-size: var(--t-sm); color: var(--boss-text-muted);
          padding: var(--s-2) 0; border-left: 2px solid transparent;
          padding-left: var(--s-3);
          transition: color var(--dur-fast) var(--ease-out),
                      border-color var(--dur-fast) var(--ease-out); }
.side a:hover { color: var(--boss-text); }
.side a.on { color: var(--boss-gold); border-left-color: var(--boss-gold); }

.doc { min-width: 0; padding-bottom: var(--s-9); }
.state { color: var(--boss-text-muted); }

header { border-bottom: 1px solid var(--boss-line); padding-bottom: var(--s-6);
         margin-bottom: var(--s-6); }
h1 { font-family: var(--font-serif); font-size: var(--t-2xl); font-weight: 500;
     margin: 0 0 var(--s-3); color: var(--boss-text);
     line-height: var(--lh-tight); }
.summary { font-size: var(--t-base); line-height: var(--lh-body);
           color: var(--boss-text-muted); margin: 0 0 var(--s-3); max-width: 62ch; }
.eff { font-size: var(--t-xs); letter-spacing: .04em; text-transform: uppercase;
       color: var(--boss-text-faint); margin: 0; }

.toc { background: var(--boss-surface); border: 1px solid var(--boss-line);
       padding: var(--s-5); margin-bottom: var(--s-7); border-radius: var(--r-md); }
.toc h2 { font-size: var(--t-xs); letter-spacing: var(--track-caps);
          text-transform: uppercase; color: var(--boss-text-faint);
          margin: 0 0 var(--s-3); }
.toc ol { margin: 0; padding-left: var(--s-5); columns: 2; column-gap: var(--s-6); }
.toc li { font-size: var(--t-sm); padding: var(--s-1) 0;
          break-inside: avoid; color: var(--boss-text-muted); }
.toc a { color: var(--boss-text-muted); }
.toc a:hover { color: var(--boss-gold); }

.sec { margin-bottom: var(--s-6); }
.sec h2 { font-family: var(--font-serif); font-size: var(--t-lg);
          font-weight: 600; color: var(--boss-text);
          margin: 0 0 var(--s-3); scroll-margin-top: 100px; }
.sec p { font-size: var(--t-base); line-height: var(--lh-body);
         color: var(--boss-text-muted); margin: 0 0 var(--s-3); max-width: 68ch; }
.sec ul { margin: 0; padding-left: var(--s-5); max-width: 68ch; }
.sec li { font-size: var(--t-base); line-height: var(--lh-body);
          color: var(--boss-text-muted); margin-bottom: var(--s-2); }

.notice { border: 1px solid var(--boss-gold-deep);
          background: rgba(212,164,55,.07); border-radius: var(--r-md);
          padding: var(--s-5); }
.ntag { display: inline-block; font-size: var(--t-xs);
        letter-spacing: var(--track-caps); text-transform: uppercase;
        color: var(--boss-gold); margin-bottom: var(--s-2); }
.notice p { margin: 0; color: var(--boss-text); font-size: var(--t-sm);
            line-height: var(--lh-body); }

.end { border-top: 1px solid var(--boss-line); padding-top: var(--s-5);
       margin-top: var(--s-7); }
.end p { font-size: var(--t-sm); color: var(--boss-text-muted); margin: 0; }
.end a { color: var(--boss-gold); border-bottom: 1px solid var(--boss-gold-deep); }

@media (max-width: 820px) {
  .page { grid-template-columns: 1fr; padding-left: var(--s-4);
          padding-right: var(--s-4); gap: var(--s-6); }
  .side { position: static; flex-direction: row; flex-wrap: wrap;
          border-bottom: 1px solid var(--boss-line); padding-bottom: var(--s-4); }
  .side h2 { width: 100%; margin: 0; }
  .side a { border-left: 0; padding-left: 0; margin-right: var(--s-4); }
  .side a.on { border-bottom: 2px solid var(--boss-gold); }
  .toc ol { columns: 1; }
}
</style>
