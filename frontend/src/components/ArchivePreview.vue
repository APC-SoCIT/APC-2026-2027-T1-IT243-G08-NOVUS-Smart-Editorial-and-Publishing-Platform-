<script setup>
/*
 * Read-only preview of a published article, opened from the archive by any
 * staff role.
 *
 * Loaded through the public endpoint rather than the editorial one: the
 * editorial endpoint limits a writer to their own work, so a writer opening
 * a colleague's piece would be refused. Every staff role reads past the
 * paywall, so all of them see the full text here.
 */
import { ref, watch } from 'vue'
import api from '../services/api'
import SlideOver from './SlideOver.vue'

const props = defineProps({
  article: { type: Object, default: null },    // the archive row that was opened
  issueLabel: { type: String, default: '' },
})
const emit = defineEmits(['close'])

const full = ref(null)
const loading = ref(false)
const failed = ref(false)
let request = 0

watch(() => props.article?.id, async (id) => {
  full.value = null
  failed.value = false
  if (!id) return
  const mine = ++request            // a later click supersedes this one
  loading.value = true
  try {
    const { data } = await api.get(`/content/articles/${id}/`)
    if (mine === request) full.value = data
  } catch {
    if (mine === request) failed.value = true
  } finally {
    if (mine === request) loading.value = false
  }
}, { immediate: true })

const fmt = (d) => d ? new Date(d).toLocaleDateString('en-PH',
  { year: 'numeric', month: 'long', day: 'numeric' }) : ''
</script>

<template>
  <SlideOver :open="!!article"
             :title="article?.title || 'Article'"
             :subtitle="article ? `${article.writer_name} · ${article.reading_time} min read` : ''"
             @close="emit('close')">
    <p v-if="loading" class="state" role="status">Loading…</p>
    <p v-else-if="failed" class="state" role="alert">
      This article could not be loaded. It may have been withdrawn since it was published.
    </p>

    <template v-else-if="full">
      <a class="public" :href="`/read/${article.id}`" target="_blank" rel="noopener">
        View on BOSS Magazine <span aria-hidden="true">↗</span>
        <span class="sr">(opens in a new tab)</span>
      </a>

      <figure v-if="full.hero_image" class="hero">
        <img :src="full.hero_image" :alt="full.hero_caption || `Photograph for ${full.title}`" />
        <figcaption v-if="full.hero_caption">{{ full.hero_caption }}</figcaption>
      </figure>

      <p v-if="full.excerpt" class="stand">{{ full.excerpt }}</p>

      <p v-if="full.is_locked" class="state">
        Only the opening is available to this account.
      </p>
      <article class="body" v-html="full.body"></article>

      <dl class="meta">
        <div><dt>Writer</dt><dd>{{ article.writer_name }}</dd></div>
        <div><dt>Category</dt><dd>{{ article.category || 'Uncategorised' }}</dd></div>
        <div><dt>Issue</dt><dd>{{ issueLabel || 'Standalone' }}</dd></div>
        <div><dt>Published</dt><dd>{{ fmt(article.published_at) }}</dd></div>
        <div><dt>Access</dt><dd>{{ article.is_premium ? 'Subscribers' : 'Free to read' }}</dd></div>
      </dl>
    </template>
  </SlideOver>
</template>

<style scoped>
.state { color: var(--nv-text-faint); font-size: 14px; }

.public { display: inline-flex; align-items: center; gap: 6px; margin: 0 0 var(--s-5);
          padding: 7px 12px; border-radius: var(--r-sm); font-size: 13px; font-weight: 600;
          border: 1px solid var(--nv-line-strong); color: var(--nv-text);
          text-decoration: none; }
.public:hover { background: var(--nv-bg); }
.public:focus-visible { outline: 2px solid var(--nv-accent); outline-offset: 2px; }
.sr { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0); }

.hero { margin: 0 0 var(--s-5); }
.hero img { width: 100%; border-radius: var(--r-sm); }
.hero figcaption { font-size: 12px; color: var(--nv-text-faint); margin-top: 7px; }

.stand { font-size: 17px; line-height: 1.55; color: var(--nv-text-muted);
         font-style: italic; margin: 0 0 var(--s-5);
         padding-bottom: var(--s-4); border-bottom: 1px solid var(--nv-line); }

.body { font-size: 16px; line-height: 1.75; color: var(--nv-text); }
.body :deep(p) { margin: 0 0 16px; }
.body :deep(h2) { font-size: 21px; margin: 26px 0 10px; }
.body :deep(h3) { font-size: 18px; margin: 20px 0 8px; }
.body :deep(img) { width: 100%; border-radius: var(--r-sm); margin: 18px 0; }
.body :deep(blockquote) { border-left: 3px solid var(--nv-line-strong);
                          padding-left: 16px; margin: 0 0 16px; color: var(--nv-text-muted); }

.meta { margin: var(--s-6) 0 0; padding-top: var(--s-4); border-top: 1px solid var(--nv-line); }
.meta > div { display: flex; justify-content: space-between; gap: 16px; padding: 7px 0; }
dt { font-size: 13px; color: var(--nv-text-muted); }
dd { margin: 0; font-size: 13px; color: var(--nv-text); text-align: right; }
</style>
