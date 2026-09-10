<script setup>
import { computed } from 'vue'
import VueApexCharts from 'vue3-apexcharts'

const props = defineProps({
  title: { type: String, required: true },
  caption: { type: String, default: '' },
  type: { type: String, default: 'bar' },
  series: { type: Array, required: true },
  options: { type: Object, default: () => ({}) },
  height: { type: Number, default: 260 },
  /* Plain-language description read by screen readers. A chart with no text
     alternative is invisible to some readers. */
  description: { type: String, default: '' },
})

const BASE = {
  chart: {
    fontFamily: 'system-ui, -apple-system, sans-serif',
    toolbar: { show: false },
    animations: { easing: 'easeout', speed: 500 },
    background: 'transparent',
  },
  colors: ['#4a7fb5', '#1c6b45', '#8a5a12', '#9e2f2f', '#24365e'],
  grid: { borderColor: '#eaecef', strokeDashArray: 3 },
  dataLabels: { enabled: false },
  legend: {
    position: 'bottom',
    fontSize: '12px',
    markers: { width: 9, height: 9, radius: 3 },
    itemMargin: { horizontal: 10, vertical: 4 },
  },
  tooltip: { theme: 'light', style: { fontSize: '12px' } },
  xaxis: {
    labels: { style: { colors: '#8a939e', fontSize: '11px' } },
    axisBorder: { color: '#eaecef' },
    axisTicks: { color: '#eaecef' },
  },
  yaxis: { labels: { style: { colors: '#8a939e', fontSize: '11px' } } },
}

function merge(a, b) {
  const out = { ...a }
  for (const k in b) {
    out[k] = b[k] && typeof b[k] === 'object' && !Array.isArray(b[k])
      ? merge(a[k] || {}, b[k])
      : b[k]
  }
  return out
}

const merged = computed(() => merge(BASE, props.options))
const hasData = computed(() =>
  props.series.some(s => (Array.isArray(s) ? s.length : (s.data || []).length)))
</script>

<template>
  <figure class="chart">
    <figcaption>
      <h3>{{ title }}</h3>
      <p v-if="caption">{{ caption }}</p>
    </figcaption>

    <p v-if="description" class="sr-only">{{ description }}</p>

    <div v-if="!hasData" class="empty">
      <p>Nothing to chart for this period.</p>
    </div>
    <VueApexCharts v-else :type="type" :height="height"
                   :options="merged" :series="series" aria-hidden="true" />
  </figure>
</template>

<style scoped>
.chart { background: var(--nv-surface); border: 1px solid var(--nv-line);
         border-radius: var(--r-md); padding: var(--s-5); margin: 0 0 var(--s-4); }
figcaption { margin-bottom: var(--s-4); }
h3 { font-size: var(--t-base); margin: 0 0 var(--s-1); color: var(--nv-text);
     font-weight: 600; }
figcaption p { font-size: var(--t-xs); color: var(--nv-text-faint);
               margin: 0; line-height: var(--lh-snug); }
.empty { display: flex; align-items: center; justify-content: center;
         height: 180px; border: 1px dashed var(--nv-line-strong);
         border-radius: var(--r-sm); }
.empty p { color: var(--nv-text-faint); font-size: var(--t-sm); margin: 0; }
</style>
