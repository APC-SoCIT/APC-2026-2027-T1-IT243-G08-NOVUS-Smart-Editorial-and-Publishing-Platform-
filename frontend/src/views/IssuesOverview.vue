<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import api from '../services/api'
import { useAuthStore } from '../stores/auth'
import StaffLayout from '../components/StaffLayout.vue'
import UiEmpty from '../components/ui/UiEmpty.vue'
import UiSkeleton from '../components/ui/UiSkeleton.vue'
import UiBadge from '../components/ui/UiBadge.vue'

const router = useRouter()

// Each role opens an article in its own view. Designers read scheduled copy
// in the designer view; the review screen belongs to editors and the
// publisher, and the role check would send a designer straight back.
function openArticle(a) {
  const role = auth.user?.role ?? auth.role
  router.push(role === 'GRAPHIC_DESIGNER'
    ? `/designer/article/${a.id}`
    : `/editor/review/${a.id}`)
}
const auth = useAuthStore()

const issues = ref([])
const loading = ref(true)
const expanded = ref(null)
const detail = ref({})

const open = computed(() =>
  issues.value.filter(i => !['PUBLISHED', 'ARCHIVED'].includes(i.status)))
const shipped = computed(() =>
  issues.value.filter(i => ['PUBLISHED', 'ARCHIVED'].includes(i.status)))

async function load() {
  const { data } = await api.get('/publication/issues/')
  issues.value = data.results ?? data
  loading.value = false
}
onMounted(load)

/* Fetched on expand rather than up front: an editor opens one issue at a
   time, and loading every issue's articles to show a list nobody has asked
   for is wasted work. */
async function toggle(i) {
  if (expanded.value === i.id) { expanded.value = null; return }
  expanded.value = i.id
  if (!detail.value[i.id]) {
    const { data } = await api.get(`/publication/issues/${i.id}/`)
    detail.value = { ...detail.value, [i.id]: data }
  }
}

const pct = (i) => i.total_articles
  ? Math.round((i.approved_articles / i.total_articles) * 100) : 0

const shortfall = (i) =>
  i.minimum_articles && i.total_articles < i.minimum_articles
    ? i.minimum_articles - i.total_articles : 0

const fmt = (d) => d
  ? new Date(d).toLocaleDateString('en-PH',
      { year: 'numeric', month: 'long', day: 'numeric' })
  : null

const daysAway = (d) => {
  if (!d) return null
  const diff = Math.ceil((new Date(d) - new Date()) / 86400000)
  if (diff < 0) return `${Math.abs(diff)} days past target`
  if (diff === 0) return 'Target is today'
  return `${diff} days to target`
}
</script>

<template>
  <StaffLayout title="Issues"
               subtitle="What each issue holds and how close it is to shipping">

    <UiSkeleton v-if="loading" :rows="3" label="Loading issues" />

    <template v-else>
      <UiEmpty v-if="!issues.length" icon="□" title="No issues yet"
               body="The publisher creates issues; editors assign approved articles to them." />

      <template v-else>
        <h2 v-if="open.length" class="sect">In preparation</h2>

        <article v-for="i in open" :key="i.id" class="issue">
          <button class="head" :aria-expanded="expanded === i.id"
                  @click="toggle(i)">
            <div class="ident">
              <span class="num">Issue {{ i.number }}</span>
              <span class="title">{{ i.title }}</span>
            </div>

            <div class="state">
              <span v-if="i.target_release_date" class="target">
                {{ daysAway(i.target_release_date) }}
              </span>
              <UiBadge :tone="i.is_ready ? 'ok' : 'neutral'">
                {{ i.is_ready ? 'Ready' : 'In preparation' }}
              </UiBadge>
              <span class="chev" aria-hidden="true">
                {{ expanded === i.id ? '▲' : '▼' }}
              </span>
            </div>
          </button>

          <div class="bar">
            <div class="track">
              <i :style="{ width: pct(i) + '%' }" :class="{ full: i.is_ready }"></i>
            </div>
            <span class="cnt">
              {{ i.approved_articles }} of {{ i.total_articles }} approved
              <template v-if="shortfall(i)">
                · <b class="short">{{ shortfall(i) }} more needed</b>
              </template>
              <template v-if="!i.replica_available">
                · <span class="nolayout">no layout yet</span>
              </template>
            </span>
          </div>

          <div v-if="expanded === i.id" class="contents">
            <p v-if="!detail[i.id]" class="loading">Loading…</p>

            <template v-else>
              <p v-if="!detail[i.id].articles.length" class="none">
                Nothing assigned yet. Approve an article and set its issue from
                the review screen.
              </p>

              <ol v-else class="arts">
                <li v-for="a in detail[i.id].articles" :key="a.id"
                    tabindex="0" role="button"
                    @click="openArticle(a)"
                    @keyup.enter="openArticle(a)">
                  <span class="at">{{ a.title }}</span>
                  <span class="aw">{{ a.writer_name }}</span>
                  <UiBadge :status="a.status" dot />
                </li>
              </ol>

              <ul v-if="detail[i.id].blocking_reasons?.length" class="blockers">
                <li v-for="(r, n) in detail[i.id].blocking_reasons" :key="n">{{ r }}</li>
              </ul>
            </template>
          </div>
        </article>

        <h2 v-if="shipped.length" class="sect">Published</h2>

        <article v-for="i in shipped" :key="i.id" class="issue done">
          <div class="head static">
            <div class="ident">
              <span class="num">Issue {{ i.number }}</span>
              <span class="title">{{ i.title }}</span>
            </div>
            <div class="state">
              <span class="target">{{ fmt(i.published_at) }}</span>
              <UiBadge tone="ok">{{ i.total_articles }} articles</UiBadge>
            </div>
          </div>
        </article>
      </template>
    </template>
  </StaffLayout>
</template>

<style scoped>
.sect { font-size: 13px; letter-spacing: .06em; text-transform: uppercase;
        color: var(--nv-text-muted); font-weight: 600;
        margin: 0 0 var(--s-3); }
.sect:not(:first-of-type) { margin-top: var(--s-7); }

.issue { background: var(--nv-surface); border: 1px solid var(--nv-line);
         border-radius: var(--r-md); padding: var(--s-5);
         margin-bottom: var(--s-3); }
.issue.done { opacity: .75; }

.head { display: flex; justify-content: space-between; align-items: center;
        gap: var(--s-4); width: 100%; background: none; border: 0; padding: 0;
        cursor: pointer; font-family: inherit; text-align: left; }
.head.static { cursor: default; }
.ident { min-width: 0; }
.num { display: block; font-size: 13px; color: var(--nv-text-muted); }
.title { font-size: 17px; font-weight: 600; color: var(--nv-text); }

.state { display: flex; align-items: center; gap: var(--s-3); flex-shrink: 0; }
.target { font-size: 13px; color: var(--nv-text-muted); white-space: nowrap; }
.chev { font-size: 10px; color: var(--nv-text-faint); }

.bar { margin-top: var(--s-4); }
.track { height: 8px; background: var(--nv-line); border-radius: 4px;
         overflow: hidden; }
.track i { display: block; height: 100%; background: var(--nv-accent);
           transition: width var(--dur-base) var(--ease-out); }
.track i.full { background: var(--ok); }
.cnt { display: block; margin-top: 7px; font-size: 14px;
       color: var(--nv-text-muted); }
.short { color: var(--warn); font-weight: 600; }
.nolayout { color: var(--nv-text-faint); }

.contents { margin-top: var(--s-5); padding-top: var(--s-4);
            border-top: 1px solid var(--nv-line); }
.loading, .none { font-size: 14px; color: var(--nv-text-faint); margin: 0;
                  line-height: 1.6; }

.arts { list-style: none; margin: 0; padding: 0; counter-reset: art; }
.arts li { display: flex; align-items: center; gap: var(--s-3);
           padding: 10px 0; border-bottom: 1px solid var(--nv-line);
           cursor: pointer; counter-increment: art; }
.arts li:last-child { border-bottom: 0; }
.arts li::before { content: counter(art, decimal-leading-zero);
                   font-size: 12px; color: var(--nv-text-faint);
                   font-variant-numeric: tabular-nums; width: 22px; }
.arts li:hover .at { color: var(--nv-accent); }
.at { flex: 1; font-size: 14px; font-weight: 600; color: var(--nv-text);
      overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.aw { font-size: 13px; color: var(--nv-text-muted); white-space: nowrap; }

.blockers { margin: var(--s-4) 0 0; padding-left: var(--s-5); }
.blockers li { font-size: 13px; line-height: 1.6; color: var(--warn); }

@media (max-width: 700px) {
  .head { flex-wrap: wrap; }
  .aw { display: none; }
}
</style>
