<script setup>
import { ref, onMounted } from 'vue'
import api from '../services/api'

const props = defineProps({
  articleId: { type: [Number, String], required: true },
})

const events = ref([])
const loading = ref(true)

onMounted(async () => {
  try {
    const { data } = await api.get(`/editorial/articles/${props.articleId}/timeline/`)
    events.value = data
  } finally { loading.value = false }
})

const when = (d) => new Date(d).toLocaleString('en-PH',
  { month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' })

const ICON = {
  created: '·', submitted: '↑', evaluated: '✓', returned: '↩',
  override: '!', revision: '✎', approved: '✓', published: '★', withdrawn: '×',
}
</script>

<template>
  <div class="tl">
    <h5>History</h5>
    <p v-if="loading" class="muted">Loading…</p>
    <p v-else-if="!events.length" class="muted">Nothing recorded yet.</p>

    <ol v-else>
      <li v-for="(e, i) in events" :key="i" :class="e.kind">
        <span class="node">{{ ICON[e.kind] || '·' }}</span>
        <div class="body">
          <div class="top">
            <b>{{ e.title }}</b>
            <small>{{ when(e.at) }}</small>
          </div>
          <p>{{ e.detail }}</p>
        </div>
      </li>
    </ol>
  </div>
</template>

<style scoped>
.tl { border: 1px solid #e6e6e6; border-radius: 8px; padding: 16px 18px; margin-top: 24px; }
h5 { margin: 0 0 14px; font-size: 12px; letter-spacing: .5px;
     text-transform: uppercase; color: #555; }
.muted { color: #999; font-size: 13px; margin: 0; }
ol { list-style: none; margin: 0; padding: 0; position: relative; }
ol::before { content: ''; position: absolute; left: 10px; top: 8px; bottom: 8px;
             width: 1px; background: #e8ebef; }
li { display: flex; gap: 14px; position: relative; padding-bottom: 16px; }
li:last-child { padding-bottom: 0; }
.node { width: 21px; height: 21px; border-radius: 50%; background: #fff;
        border: 1.5px solid #d5dae0; color: #99a; display: flex;
        align-items: center; justify-content: center; font-size: 11px;
        flex-shrink: 0; z-index: 1; }
li.evaluated .node, li.approved .node { border-color: #2e9e63; color: #2e9e63; }
li.published .node { border-color: #1a2744; background: #1a2744; color: #fff; }
li.returned .node, li.withdrawn .node { border-color: #c95757; color: #c95757; }
li.override .node { border-color: #b5651d; color: #b5651d; }
li.revision .node { border-color: #d9963c; color: #d9963c; }
li.submitted .node { border-color: #4a7fb5; color: #4a7fb5; }
.body { flex: 1; min-width: 0; padding-top: 1px; }
.top { display: flex; justify-content: space-between; align-items: baseline; gap: 12px; }
.top b { font-size: 13px; }
.top small { font-size: 11px; color: #aab; white-space: nowrap; }
.body p { margin: 3px 0 0; font-size: 12px; color: #778; line-height: 1.55; }
</style>
