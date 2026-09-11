<script setup>
const props = defineProps({
  evaluation: { type: Object, default: null },
  returnedByAi: { type: Boolean, default: false },
  threshold: { type: Number, default: 70 },
})

const typeLabel = {
  GRAMMAR: 'Grammar', TONE: 'Tone',
  STRUCTURE: 'Structure', FACTUAL: 'Factual',
}
</script>

<template>
  <div v-if="evaluation" class="panel" :class="returnedByAi ? 'failed' : 'passed'">
    <div class="head">
      <div class="ring" :class="returnedByAi ? 'r-fail' : 'r-pass'">
        <b>{{ evaluation.overall_score }}</b>
        <small>/ 100</small>
      </div>
      <div class="headline">
        <h4 v-if="returnedByAi">Returned for revision</h4>
        <h4 v-else>Passed pre-screening</h4>
        <p v-if="returnedByAi">
          This draft scored below the passing mark of {{ threshold }}.
          Address the points below and submit again.
        </p>
        <p v-else>Sent to your editor for review.</p>
      </div>
    </div>

    <div class="bars">
      <div class="bar">
        <span>Grammar</span>
        <div class="track"><i :style="{ width: evaluation.grammar_score + '%' }"></i></div>
        <b>{{ evaluation.grammar_score }}</b>
      </div>
      <div class="bar">
        <span>Readability</span>
        <div class="track"><i :style="{ width: evaluation.readability_score + '%' }"></i></div>
        <b>{{ evaluation.readability_score }}</b>
      </div>
    </div>

    <p v-if="evaluation.summary" class="summary">{{ evaluation.summary }}</p>

    <div v-if="evaluation.suggestions?.length" class="sugs">
      <h5>Suggested improvements</h5>
      <div v-for="(s, i) in evaluation.suggestions" :key="i" class="sug">
        <div class="tags">
          <span class="tag">{{ typeLabel[s.note_type] || s.note_type }}</span>
          <span class="tag pri" :class="'p-' + s.priority.toLowerCase()">{{ s.priority }}</span>
          <span v-if="s.section" class="sec">{{ s.section }}</span>
        </div>
        <p>{{ s.instruction }}</p>
      </div>
    </div>

    <p v-if="evaluation.ai_model === 'stub'" class="stub">
      Automated evaluation is not configured, so no score was produced.
    </p>
  </div>
</template>

<style scoped>
.panel { border: 1px solid #e0e0e0; border-radius: 10px; padding: 18px; margin-bottom: 22px; background: #fff; }
.panel.failed { border-color: #f0c9c9; background: #fffafa; }
.panel.passed { border-color: #c9e6d4; background: #fafffb; }
.head { display: flex; gap: 18px; align-items: center; }
.ring { width: 76px; height: 76px; border-radius: 50%; display: flex; flex-direction: column;
        align-items: center; justify-content: center; flex-shrink: 0; border: 4px solid; }
.r-pass { border-color: #2e9e63; color: #1c6b45; }
.r-fail { border-color: #c95757; color: #a33; }
.ring b { font-size: 24px; line-height: 1; }
.ring small { font-size: 10px; opacity: .7; }
.headline h4 { margin: 0 0 4px; font-size: 16px; }
.headline p { margin: 0; font-size: 13px; color: #666; line-height: 1.5; }
.bars { margin-top: 16px; display: flex; flex-direction: column; gap: 8px; }
.bar { display: flex; align-items: center; gap: 10px; font-size: 12px; }
.bar span { width: 82px; color: #666; }
.track { flex: 1; height: 6px; background: #eee; border-radius: 3px; overflow: hidden; }
.track i { display: block; height: 100%; background: #4a7fb5; }
.bar b { width: 28px; text-align: right; }
.summary { margin: 16px 0 0; font-size: 13px; line-height: 1.6; color: #444;
           border-left: 3px solid #ddd; padding-left: 12px; }
.sugs { margin-top: 18px; }
.sugs h5 { margin: 0 0 10px; font-size: 12px; letter-spacing: .5px; color: #555; text-transform: uppercase; }
.sug { border-top: 1px solid #eee; padding: 10px 0; }
.tags { display: flex; gap: 6px; align-items: center; margin-bottom: 5px; flex-wrap: wrap; }
.tag { font-size: 10px; padding: 2px 7px; border-radius: 10px; background: #eef2f7; color: #445; letter-spacing: .4px; }
.tag.pri.p-high { background: #fbe6e6; color: #a33; }
.tag.pri.p-medium { background: #fdf2e0; color: #96631a; }
.tag.pri.p-low { background: #eef2f7; color: #556; }
.sec { font-size: 11px; color: #888; }
.sug p { margin: 0; font-size: 13px; line-height: 1.55; }
.stub { margin: 14px 0 0; font-size: 12px; color: #888; font-style: italic; }
</style>
