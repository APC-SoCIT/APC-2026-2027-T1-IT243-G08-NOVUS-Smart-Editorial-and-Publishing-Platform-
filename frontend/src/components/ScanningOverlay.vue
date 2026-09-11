<script setup>
import { ref, watch, onUnmounted } from 'vue'

const props = defineProps({
  active: { type: Boolean, default: false },
  result: { type: Object, default: null },   // set when the API returns
  threshold: { type: Number, default: 70 },
})
const emit = defineEmits(['done'])

const STAGES = [
  { key: 'read',  label: 'Reading your draft' },
  { key: 'gram',  label: 'Checking grammar and mechanics' },
  { key: 'read2', label: 'Assessing readability and structure' },
  { key: 'score', label: 'Scoring against editorial standards' },
]

const stage = ref(-1)
const showResult = ref(false)
const shownScore = ref(0)
let stageTimer = null
let countTimer = null

function reset() {
  stage.value = -1
  showResult.value = false
  shownScore.value = 0
  clearInterval(stageTimer)
  clearInterval(countTimer)
}

// Stages advance on a timer, but the last one holds until the API answers —
// so the overlay never claims to be finished before the work actually is.
watch(() => props.active, (on) => {
  if (!on) return reset()
  reset()
  stage.value = 0
  stageTimer = setInterval(() => {
    if (stage.value < STAGES.length - 1) stage.value++
    else clearInterval(stageTimer)
  }, 900)
})

watch(() => props.result, (r) => {
  if (!r) return
  clearInterval(stageTimer)
  stage.value = STAGES.length
  setTimeout(() => {
    showResult.value = true
    const target = r.overall_score ?? 0
    if (!target) return
    const step = Math.max(1, Math.round(target / 28))
    countTimer = setInterval(() => {
      shownScore.value = Math.min(target, shownScore.value + step)
      if (shownScore.value >= target) clearInterval(countTimer)
    }, 26)
  }, 450)
})

onUnmounted(reset)

const passed = () => (props.result?.overall_score ?? 0) >= props.threshold
const unavailable = () => props.result?.overall_score === null
             || props.result?.gate === 'BYPASSED'
</script>

<template>
  <transition name="fade">
    <div v-if="active" class="scrim">
      <div class="panel">

        <!-- scanning -->
        <template v-if="!showResult">
          <div class="scanner">
            <div class="doc">
              <span v-for="n in 7" :key="n" class="line"
                    :style="{ width: (55 + ((n * 13) % 40)) + '%' }"></span>
            </div>
            <div class="beam"></div>
          </div>

          <h3>Pre-screening your submission</h3>

          <ul class="stages">
            <li v-for="(s, i) in STAGES" :key="s.key"
                :class="{ done: i < stage, now: i === stage }">
              <span class="dot">
                <template v-if="i < stage">✓</template>
                <template v-else-if="i === stage"><i class="spin"></i></template>
              </span>
              {{ s.label }}
            </li>
          </ul>

          <p class="note">This usually takes a few seconds.</p>
        </template>

        <!-- result -->
        <template v-else>
          <div v-if="unavailable()" class="verdict neutral">
            <div class="ring none"><b>—</b></div>
            <h3>Sent for manual review</h3>
            <p>
              Automated evaluation was unavailable, so your editor will review
              this without a score.
            </p>
          </div>

          <div v-else class="verdict" :class="passed() ? 'pass' : 'fail'">
            <div class="ring" :class="passed() ? 'ok' : 'no'">
              <b>{{ shownScore }}</b><small>/ 100</small>
            </div>
            <h3>{{ passed() ? 'Passed pre-screening' : 'Returned for revision' }}</h3>
            <p v-if="passed()">
              Your article is now with the editor for review.
            </p>
            <p v-else>
              This scored below the passing mark of {{ threshold }}. Your
              editor's queue is unaffected — address the notes and submit again.
            </p>

            <div v-if="result?.summary" class="summary">{{ result.summary }}</div>
          </div>

          <button class="continue" @click="emit('done')">
            {{ passed() ? 'Back to dashboard' : 'View the notes' }}
          </button>
        </template>

      </div>
    </div>
  </transition>
</template>

<style scoped>
.scrim { position: fixed; inset: 0; background: rgba(13, 21, 38, .72);
         backdrop-filter: blur(3px); display: flex; align-items: center;
         justify-content: center; z-index: 100; font-family: system-ui; }
.panel { background: var(--nv-surface); border-radius: 14px; padding: 34px 36px;
         width: 420px; max-width: calc(100vw - 40px); text-align: center;
         box-shadow: 0 20px 60px rgba(0,0,0,.28); }

/* scanner graphic */
.scanner { position: relative; height: 118px; margin: 0 auto 22px;
           width: 150px; overflow: hidden; }
.doc { border: 1px solid #dfe4ea; border-radius: 6px; height: 100%;
       padding: 15px 13px; display: flex; flex-direction: column;
       gap: 9px; background: #fbfcfd; }
.line { height: 6px; background: #e4e9ef; border-radius: 3px; display: block; }
.beam { position: absolute; left: 0; right: 0; height: 34px;
        background: linear-gradient(180deg, rgba(74,127,181,0) 0%,
                    rgba(74,127,181,.28) 50%, rgba(74,127,181,0) 100%);
        border-top: 1px solid rgba(74,127,181,.55);
        border-bottom: 1px solid rgba(74,127,181,.55);
        animation: sweep 1.7s ease-in-out infinite; }
@keyframes sweep {
  0%   { transform: translateY(-34px); }
  50%  { transform: translateY(118px); }
  100% { transform: translateY(-34px); }
}

h3 { margin: 0 0 16px; font-size: 17px; }

.stages { list-style: none; margin: 0 0 18px; padding: 0; text-align: left; }
.stages li { display: flex; align-items: center; gap: 11px; padding: 6px 0;
             font-size: 13px; color: #b4bcc6; transition: color .25s; }
.stages li.done { color: #4a5a6a; }
.stages li.now { color: #1a2744; font-weight: 600; }
.dot { width: 18px; height: 18px; border-radius: 50%; border: 1.5px solid #dde2e8;
       display: inline-flex; align-items: center; justify-content: center;
       font-size: 10px; flex-shrink: 0; }
.stages li.done .dot { background: #2e9e63; border-color: var(--ok); color: #fff; }
.stages li.now .dot { border-color: var(--nv-accent); }
.spin { width: 8px; height: 8px; border: 1.5px solid #4a7fb5; border-top-color: transparent;
        border-radius: 50%; animation: rot .7s linear infinite; }
@keyframes rot { to { transform: rotate(360deg); } }

.note { margin: 0; font-size: 12px; color: var(--nv-text-faint)2bc; }

/* verdict */
.ring { width: 104px; height: 104px; border-radius: 50%; border: 5px solid;
        margin: 0 auto 18px; display: flex; flex-direction: column;
        align-items: center; justify-content: center; }
.ring.ok { border-color: var(--ok); color: var(--ok); }
.ring.no { border-color: var(--bad); color: var(--bad); }
.ring.none { border-color: #dde2e8; color: var(--nv-text-faint); }
.ring b { font-size: 34px; line-height: 1; }
.ring small { font-size: 11px; opacity: .65; margin-top: 2px; }
.verdict p { margin: 0; font-size: 13px; color: var(--nv-text-muted); line-height: 1.6; }
.summary { margin-top: 16px; background: #f6f8fa; border-radius: 8px;
           padding: 12px 14px; font-size: 13px; line-height: 1.6;
           color: #4a5a6a; text-align: left; }

.continue { width: 100%; margin-top: 24px; padding: 12px; border: 0;
            background: var(--nv-navy-2); color: #fff; border-radius: 8px;
            font-weight: 600; font-size: 14px; cursor: pointer; }

.fade-enter-active, .fade-leave-active { transition: opacity .25s; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
</style>
