<script setup>
import { computed } from 'vue'

const props = defineProps({
  evaluation: { type: Object, default: null },
  returnedByAi: { type: Boolean, default: false },
  threshold: { type: Number, default: 70 },
})

const typeLabel = {
  GRAMMAR: 'Grammar', TONE: 'Tone',
  STRUCTURE: 'Structure', FACTUAL: 'Factual',
}

const rewrite = computed(() => props.evaluation?.verdict === 'REWRITE')
// An editor deserves to know which words came from the machine.
const accepted = computed(() =>
  (props.evaluation?.fixes || []).filter(f => f.state === 'accepted'))
</script>

<template>
  <section v-if="evaluation" class="panel"
           :class="evaluation.is_overridden ? 'overridden' : (returnedByAi ? 'failed' : 'passed')">

    <!-- Verdict on one side, the two measurements on the other. The grid
         reflows by the space it is given, so the same component sits side by
         side on the review screen and stacks in the composer's narrow rail. -->
    <div class="top">
      <div class="verdict">
        <div class="ring"
             :class="evaluation.is_overridden ? 'r-over' : (returnedByAi ? 'r-fail' : 'r-pass')">
          <b>{{ evaluation.overall_score }}</b>
          <small>/ 100</small>
        </div>
        <div class="headline">
          <h4 v-if="evaluation.is_overridden">Overridden by an editor</h4>
          <h4 v-else-if="rewrite">Needs rework</h4>
          <h4 v-else-if="returnedByAi">Returned for revision</h4>
          <h4 v-else>Passed pre-screening</h4>
          <p v-if="evaluation.is_overridden">
            Scored below the passing mark of {{ threshold }}. An editor approved
            it anyway and recorded why.
          </p>
          <p v-else-if="rewrite">
            Well below the passing mark of {{ threshold }}. Line edits won't
            carry this over; the notes describe what to rethink.
          </p>
          <p v-else-if="returnedByAi">
            Below the passing mark of {{ threshold }}. Address the points below
            and submit again.
          </p>
          <p v-else>Cleared the passing mark of {{ threshold }}.</p>
        </div>
      </div>

      <dl class="bars">
        <div class="bar">
          <dt>Grammar</dt>
          <dd><span class="track"><i :style="{ width: evaluation.grammar_score + '%' }"></i></span>
              <b>{{ evaluation.grammar_score }}</b></dd>
        </div>
        <div class="bar">
          <dt>Readability</dt>
          <dd><span class="track"><i :style="{ width: evaluation.readability_score + '%' }"></i></span>
              <b>{{ evaluation.readability_score }}</b></dd>
        </div>
      </dl>
    </div>

    <blockquote v-if="evaluation.summary" class="summary">{{ evaluation.summary }}</blockquote>

    <div v-if="evaluation.suggestions?.length" class="sugs">
      <h5>Suggested improvements <span>{{ evaluation.suggestions.length }}</span></h5>
      <ul>
        <li v-for="(s, i) in evaluation.suggestions" :key="i" class="sug">
          <div class="tags">
            <span class="tag">{{ typeLabel[s.note_type] || s.note_type }}</span>
            <span class="tag pri" :class="'p-' + (s.priority || '').toLowerCase()">{{ s.priority }}</span>
            <span v-if="s.section" class="sec">{{ s.section }}</span>
          </div>
          <p>{{ s.instruction }}</p>
        </li>
      </ul>
    </div>

    <details v-if="accepted.length" class="aifix">
      <summary>{{ accepted.length }} AI-suggested
        {{ accepted.length === 1 ? 'fix' : 'fixes' }} accepted by the writer</summary>
      <ul>
        <li v-for="f in accepted" :key="f.id">
          <del>{{ f.original }}</del> → <ins>{{ f.replacement }}</ins>
        </li>
      </ul>
    </details>

    <p v-if="evaluation.ai_model === 'stub'" class="stub">
      Automated evaluation is not configured, so no score was produced.
    </p>
  </section>
</template>

<style scoped>
.panel { background: var(--nv-surface); border: 1px solid var(--nv-line);
         border-left: 4px solid var(--ok); border-radius: var(--r-md);
         padding: var(--s-5); }
.panel.failed { border-left-color: var(--bad); }
.panel.overridden { border-left-color: var(--warn); }

.top { display: grid; gap: var(--s-4) var(--s-6); align-items: center;
       grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); }

.verdict { display: flex; gap: var(--s-4); align-items: center; }
.ring { flex: 0 0 auto; width: 76px; height: 76px; border-radius: 50%;
        border: 4px solid var(--ok); display: flex; flex-direction: column;
        align-items: center; justify-content: center; line-height: 1; }
.ring b { font-size: 24px; font-variant-numeric: tabular-nums; }
.ring small { font-size: 10px; color: var(--nv-text-faint); margin-top: 3px; }
.r-pass { border-color: var(--ok); } .r-pass b { color: var(--ok); }
.r-fail { border-color: var(--bad); } .r-fail b { color: var(--bad); }
.r-over { border-color: var(--warn); } .r-over b { color: var(--warn); }
.headline h4 { margin: 0 0 4px; font-size: 16px; color: var(--nv-text); }
.headline p { margin: 0; font-size: 13.5px; line-height: 1.55;
              color: var(--nv-text-muted); max-width: 46ch; }

/* Capped width: two numbers do not need the whole screen to be read. */
.bars { margin: 0; display: grid; gap: 10px; max-width: 380px;
        justify-self: end; width: 100%; }
.bar { display: grid; grid-template-columns: 88px 1fr; align-items: center; gap: 10px; }
.bar dt { font-size: 13px; color: var(--nv-text-muted); }
.bar dd { margin: 0; display: flex; align-items: center; gap: 10px; }
.track { flex: 1; height: 6px; border-radius: 3px; background: var(--nv-line);
         overflow: hidden; }
.track i { display: block; height: 100%; background: var(--nv-accent);
           border-radius: 3px; }
.bar b { font-size: 13px; min-width: 24px; text-align: right;
         font-variant-numeric: tabular-nums; color: var(--nv-text); }

.summary { margin: var(--s-4) 0 0; padding: 2px 0 2px var(--s-3);
           border-left: 3px solid var(--nv-line-strong); font-size: 14px;
           line-height: 1.6; color: var(--nv-text); }

.sugs { margin-top: var(--s-5); padding-top: var(--s-4);
        border-top: 1px solid var(--nv-line); }
.sugs h5 { margin: 0 0 var(--s-3); font-size: 11.5px; letter-spacing: .08em;
           text-transform: uppercase; color: var(--nv-text-muted); }
.sugs h5 span { margin-left: 6px; padding: 1px 7px; border-radius: 999px;
                background: var(--nv-bg); color: var(--nv-text-faint);
                letter-spacing: 0; }
.sugs ul { list-style: none; margin: 0; padding: 0; display: grid; gap: var(--s-3);
           grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); }
.sug { padding: var(--s-3); border: 1px solid var(--nv-line);
       border-radius: var(--r-sm); background: var(--nv-bg); }
.sug p { margin: 8px 0 0; font-size: 13.5px; line-height: 1.55; color: var(--nv-text); }
.tags { display: flex; flex-wrap: wrap; gap: 6px; align-items: center; }
.tag { font-size: 11px; padding: 2px 8px; border-radius: 999px;
       background: var(--nv-accent-soft); color: var(--nv-text); }
.pri { font-weight: 600; }
.p-high { background: var(--bad-bg); color: var(--bad); }
.p-medium { background: var(--warn-bg); color: var(--warn); }
.p-low { background: var(--nv-bg); color: var(--nv-text-muted);
         border: 1px solid var(--nv-line); }
.sec { font-size: 12px; color: var(--nv-text-faint); }

.aifix { margin-top: var(--s-4); font-size: 13px; color: var(--nv-text-muted); }
.aifix summary { cursor: pointer; font-weight: 600; color: var(--nv-text); }
.aifix ul { margin: 8px 0 0; padding-left: 18px; display: grid; gap: 4px; }
.aifix del { color: var(--bad); }
.aifix ins { color: var(--ok); text-decoration: none; }
.stub { margin: var(--s-4) 0 0; font-size: 13px; color: var(--nv-text-faint); }
</style>
