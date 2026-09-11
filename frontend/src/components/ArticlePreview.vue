<script setup>
import { ref, watch } from 'vue'
import api from '../services/api'
import SlideOver from './SlideOver.vue'

const props = defineProps({
  articleId: { type: [Number, String], default: null },
})
const emit = defineEmits(['close'])

const article = ref(null)
const loading = ref(false)

watch(() => props.articleId, async (id) => {
  if (!id) { article.value = null; return }
  loading.value = true
  try {
    const { data } = await api.get(`/editorial/articles/${id}/`)
    article.value = data
  } finally { loading.value = false }
}, { immediate: true })

const fmt = (d) => d ? new Date(d).toLocaleDateString('en-PH',
  { year: 'numeric', month: 'long', day: 'numeric' }) : ''
</script>

<template>
  <SlideOver :open="!!articleId"
             :title="article?.title || 'Article'"
             :subtitle="article
               ? `${article.writer_name} · ${article.reading_time} min read`
               : ''"
             @close="emit('close')">
    <p v-if="loading" class="state" role="status">Loading…</p>

    <template v-else-if="article">
      <div v-if="article.latest_evaluation" class="score"
           :class="article.latest_evaluation.overall_score >= 70 ? 'good' : 'bad'">
        <b>{{ article.latest_evaluation.overall_score }}</b>
        <span>
          Pre-screening · grammar {{ article.latest_evaluation.grammar_score }}
          · readability {{ article.latest_evaluation.readability_score }}
        </span>
      </div>

      <p v-if="article.latest_evaluation?.summary" class="summary">
        {{ article.latest_evaluation.summary }}
      </p>

      <figure v-if="article.hero_image" class="hero">
        <img :src="article.hero_image"
             :alt="article.hero_caption || `Photograph for ${article.title}`" />
        <figcaption v-if="article.hero_caption">{{ article.hero_caption }}</figcaption>
      </figure>

      <p v-if="article.excerpt" class="stand">{{ article.excerpt }}</p>

      <article class="body" v-html="article.body"></article>

      <dl class="meta">
        <div><dt>Category</dt><dd>{{ article.category || 'Uncategorised' }}</dd></div>
        <div><dt>Status</dt>
             <dd>{{ article.status.replace(/_/g, ' ').toLowerCase() }}</dd></div>
        <div v-if="article.published_at">
          <dt>Published</dt><dd>{{ fmt(article.published_at) }}</dd>
        </div>
      </dl>
    </template>
  </SlideOver>
</template>

<style scoped>
.state { color: var(--nv-text-faint); }

.score { display: flex; align-items: center; gap: var(--s-4);
         border: 1px solid; border-radius: var(--r-sm);
         padding: 12px 16px; margin-bottom: var(--s-4); }
.score b { font-size: 26px; font-variant-numeric: tabular-nums; }
.score span { font-size: 13px; line-height: 1.45; }
.score.good { border-color: var(--ok-line); background: var(--ok-bg); color: var(--ok); }
.score.bad { border-color: var(--bad-line); background: var(--bad-bg); color: var(--bad); }

.summary { font-size: 14px; line-height: 1.6; color: var(--nv-text-muted);
           border-left: 3px solid var(--nv-line-strong); padding-left: 14px;
           margin: 0 0 var(--s-5); }

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
                          padding-left: 16px; margin: 0 0 16px;
                          color: var(--nv-text-muted); }

.meta { margin: var(--s-6) 0 0; padding-top: var(--s-4);
        border-top: 1px solid var(--nv-line); }
.meta > div { display: flex; justify-content: space-between; padding: 7px 0; }
dt { font-size: 13px; color: var(--nv-text-muted); }
dd { margin: 0; font-size: 13px; color: var(--nv-text); text-transform: capitalize; }
</style>
