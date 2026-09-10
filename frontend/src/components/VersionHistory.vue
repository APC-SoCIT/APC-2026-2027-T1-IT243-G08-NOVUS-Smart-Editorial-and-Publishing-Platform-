<script setup>
import { ref, computed } from 'vue'

const props = defineProps({
  versions: { type: Array, default: () => [] },
  currentTitle: { type: String, default: '' },
  currentBody: { type: String, default: '' },
})

const open = ref(false)
const selected = ref(null)
const compare = ref(false)

const plain = (html) => {
  const el = document.createElement('div')
  el.innerHTML = html || ''
  return el.innerText.trim()
}

// Sentence-level diff. Good enough to show an editor what moved between
// drafts without pulling in a diff library.
const diff = computed(() => {
  if (!selected.value) return []
  const split = (t) => plain(t).split(/(?<=[.!?])\s+/).filter(Boolean)
  const older = split(selected.value.body)
  const newer = split(props.currentBody)
  const olderSet = new Set(older)
  const newerSet = new Set(newer)

  return [
    ...older.filter(s => !newerSet.has(s)).map(s => ({ type: 'removed', text: s })),
    ...newer.filter(s => !olderSet.has(s)).map(s => ({ type: 'added', text: s })),
  ]
})

function select(v) {
  selected.value = selected.value?.id === v.id ? null : v
  compare.value = false
}

const when = (d) => new Date(d).toLocaleString('en-PH',
  { month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' })
</script>

<template>
  <div v-if="versions.length" class="vh">
    <button class="toggle" @click="open = !open">
      Version history
      <span class="count">{{ versions.length }}</span>
      <span class="chev">{{ open ? '▲' : '▼' }}</span>
    </button>

    <div v-if="open" class="body">
      <p class="hint">
        A snapshot is taken every time the writer submits. Select a version to
        see what has changed since.
      </p>

      <ul class="list">
        <li v-for="v in versions" :key="v.id"
            :class="{ on: selected?.id === v.id }" @click="select(v)">
          <div class="meta">
            <b>Version {{ v.number }}</b>
            <em>{{ v.submitted_by_name }} · {{ when(v.created_at) }}</em>
          </div>
          <span class="words">{{ v.word_count }} words</span>
        </li>
      </ul>

      <div v-if="selected" class="detail">
        <div class="dhead">
          <b>Version {{ selected.number }}</b>
          <div class="tabs">
            <button :class="{ on: !compare }" @click="compare = false">Content</button>
            <button :class="{ on: compare }" @click="compare = true">
              Changes since
            </button>
          </div>
        </div>

        <template v-if="!compare">
          <p v-if="selected.title !== currentTitle" class="tchange">
            Headline was: <b>{{ selected.title }}</b>
          </p>
          <div class="content" v-html="selected.body"></div>
        </template>

        <template v-else>
          <p v-if="!diff.length" class="muted">
            No sentence-level changes since this version.
          </p>
          <div v-else class="diff">
            <p v-for="(d, i) in diff" :key="i" :class="d.type">
              <span class="mark">{{ d.type === 'added' ? '+' : '−' }}</span>
              {{ d.text }}
            </p>
          </div>
        </template>
      </div>
    </div>
  </div>
</template>

<style scoped>
.vh { margin-top: 24px; }
.toggle { width: 100%; display: flex; align-items: center; gap: 8px;
          border: 1px solid #e6e6e6; background: #fafafa; border-radius: 8px;
          padding: 11px 14px; font-size: 13px; cursor: pointer; }
.count { background: #e4e9f0; color: #445; font-size: 11px;
         padding: 2px 8px; border-radius: 10px; }
.chev { margin-left: auto; font-size: 10px; color: #999; }
.body { border: 1px solid #e6e6e6; border-top: 0; border-radius: 0 0 8px 8px; padding: 14px; }
.hint { margin: 0 0 12px; font-size: 12px; color: #999; line-height: 1.5; }
.list { list-style: none; margin: 0; padding: 0; }
.list li { display: flex; justify-content: space-between; align-items: center;
           padding: 10px 12px; border: 1px solid #eee; border-radius: 6px;
           margin-bottom: 6px; cursor: pointer; }
.list li:hover { background: #fafafa; }
.list li.on { border-color: #b9c9e0; background: #f6f9fd; }
.meta b { display: block; font-size: 13px; }
.meta em { font-size: 11px; color: #999; font-style: normal; }
.words { font-size: 11px; color: #999; }
.detail { margin-top: 14px; border-top: 1px solid #eee; padding-top: 14px; }
.dhead { display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; }
.tabs { display: flex; gap: 4px; }
.tabs button { border: 1px solid #ddd; background: #fff; border-radius: 5px;
               padding: 5px 11px; font-size: 12px; cursor: pointer; }
.tabs button.on { background: #1a2744; color: #fff; border-color: #1a2744; }
.tchange { font-size: 12px; color: #96631a; background: #fdf6e8;
           padding: 8px 11px; border-radius: 6px; margin: 0 0 10px; }
.content { max-height: 320px; overflow-y: auto; font-size: 14px; line-height: 1.65;
           background: #fafafa; padding: 14px; border-radius: 6px; }
.content :deep(p) { margin: 0 0 12px; }
.diff p { margin: 0 0 7px; font-size: 13px; line-height: 1.55;
          padding: 7px 11px; border-radius: 5px; }
.diff p.added { background: #eef8f2; color: #1c6b45; }
.diff p.removed { background: #fdeeee; color: #a33; text-decoration: line-through; }
.mark { font-weight: 700; margin-right: 6px; }
.muted { color: #999; font-size: 13px; }
</style>
