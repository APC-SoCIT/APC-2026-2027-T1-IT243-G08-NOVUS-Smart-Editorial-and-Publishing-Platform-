<script setup>
/* A dropdown you can type in to filter (adviser meeting, Nov 24), with an
   optional "+ Create" row for lists that grow, such as categories.

   Keyboard: type to filter, ↑/↓ to move, Enter to choose, Esc to close.
   Follows the WAI-ARIA combobox pattern so screen readers announce the
   list and the highlighted option. */
import { ref, computed, watch, nextTick, useId } from 'vue'

const props = defineProps({
  modelValue: { type: [String, Number, null], default: '' },
  /* [{ value, label, hint? }] — hint is shown in grey and is searchable. */
  options: { type: Array, default: () => [] },
  placeholder: { type: String, default: 'Select…' },
  /* A first row that clears the choice, e.g. "Uncategorised". */
  emptyLabel: { type: String, default: '' },
  /* async (name) => option. Given, a "+ Create" row appears for new text. */
  create: { type: Function, default: null },
  disabled: { type: Boolean, default: false },
  ariaLabel: { type: String, default: '' },
  id: { type: String, default: '' },
})
const emit = defineEmits(['update:modelValue', 'change'])

const uid = props.id || `cb-${useId()}`
const listId = `${uid}-list`
const open = ref(false)
const query = ref('')
const typing = ref(false)
const active = ref(-1)
const creating = ref(false)
const error = ref('')
const input = ref(null)
const list = ref(null)

const selected = computed(() =>
  props.options.find((o) => String(o.value) === String(props.modelValue)) || null)
const shownText = computed(() => (typing.value ? query.value : selected.value?.label || ''))

const filtered = computed(() => {
  const q = query.value.trim().toLowerCase()
  const rows = q
    ? props.options.filter((o) =>
        o.label.toLowerCase().includes(q) || (o.hint || '').toLowerCase().includes(q))
    : props.options
  return props.emptyLabel && !q ? [{ value: '', label: props.emptyLabel, empty: true }, ...rows] : rows
})

const canCreate = computed(() => {
  const q = query.value.trim()
  return !!props.create && q.length >= 2 &&
    !props.options.some((o) => o.label.toLowerCase() === q.toLowerCase())
})
const rows = computed(() =>
  canCreate.value ? [...filtered.value, { create: true, label: query.value.trim() }] : filtered.value)

watch(rows, () => { active.value = rows.value.length ? 0 : -1 })

function openList() {
  if (props.disabled || open.value) return
  // Start from an empty box with the current choice as the placeholder, so
  // typing searches instead of editing the shown name.
  typing.value = true
  query.value = ''
  open.value = true
  error.value = ''
  const i = rows.value.findIndex((r) => !r.create && String(r.value) === String(props.modelValue))
  active.value = i >= 0 ? i : 0
  scrollToActive()
}
function close() {
  open.value = false
  typing.value = false
  query.value = ''
}
function onInput(e) {
  query.value = e.target.value
  typing.value = true
  open.value = true
}
async function choose(row) {
  if (!row) return
  if (row.create) return makeNew(row.label)
  emit('update:modelValue', row.value)
  emit('change', row.value)
  close()
}
async function makeNew(name) {
  creating.value = true
  error.value = ''
  try {
    const option = await props.create(name)
    if (option) {
      emit('update:modelValue', option.value)
      emit('change', option.value)
    }
    close()
  } catch (e) {
    const d = e?.response?.data
    error.value = d?.name?.[0] || d?.detail || e?.message || 'Could not create it.'
  } finally { creating.value = false }
}
function move(step) {
  if (!open.value) return openList()
  const n = rows.value.length
  if (!n) return
  active.value = (active.value + step + n) % n
  scrollToActive()
}
function scrollToActive() {
  nextTick(() => list.value?.querySelector('[data-active="true"]')?.scrollIntoView({ block: 'nearest' }))
}
function onKey(e) {
  if (e.key === 'ArrowDown') { e.preventDefault(); move(1) }
  else if (e.key === 'ArrowUp') { e.preventDefault(); move(-1) }
  else if (e.key === 'Enter') {
    if (open.value) { e.preventDefault(); choose(rows.value[active.value]) }
  } else if (e.key === 'Escape') {
    if (open.value) { e.preventDefault(); close() }
  }
}
const optId = (i) => `${uid}-opt-${i}`
</script>

<template>
  <div class="cb" :class="{ open, disabled }">
    <div class="field">
      <input ref="input" :id="uid" type="text" role="combobox" autocomplete="off"
             :value="shownText" :placeholder="open && selected ? selected.label : placeholder"
             :disabled="disabled || creating" :aria-label="ariaLabel || undefined"
             aria-autocomplete="list" :aria-expanded="open" :aria-controls="listId"
             :aria-activedescendant="open && active >= 0 ? optId(active) : undefined"
             @focus="openList" @click="openList" @input="onInput"
             @keydown="onKey" @blur="close" />
      <span class="chev" aria-hidden="true">▾</span>
    </div>

    <ul v-show="open" :id="listId" ref="list" role="listbox" class="list"
        :aria-label="ariaLabel || undefined">
      <li v-for="(r, i) in rows" :id="optId(i)" :key="r.create ? '__create' : String(r.value)"
          role="option" :aria-selected="!r.create && String(r.value) === String(modelValue)"
          :data-active="i === active" :class="{ on: i === active, empty: r.empty, create: r.create }"
          @mousedown.prevent="choose(r)" @mousemove="active = i">
        <template v-if="r.create">
          {{ creating ? 'Creating…' : '+ Create' }} “{{ r.label }}”
        </template>
        <template v-else>
          <span>{{ r.label }}</span>
          <small v-if="r.hint">{{ r.hint }}</small>
        </template>
      </li>
      <li v-if="!rows.length" class="none" role="presentation">No matches</li>
    </ul>
    <p v-if="error" class="err" role="alert">{{ error }}</p>
  </div>
</template>

<style scoped>
.cb { position: relative; margin-top: 5px; letter-spacing: normal; }
.field { position: relative; }
input { width: 100%; padding: 9px 30px 9px 9px; border: 1px solid var(--nv-line-strong);
        border-radius: 6px; font-size: 13px; font-family: inherit;
        background: var(--nv-surface); color: var(--nv-text); margin: 0; }
input:focus { outline: 2px solid var(--nv-accent); outline-offset: 1px; }
input:disabled { opacity: .6; }
.chev { position: absolute; right: 10px; top: 50%; transform: translateY(-50%);
        color: var(--nv-text-muted); pointer-events: none; font-size: 12px; }
.list { position: absolute; z-index: 50; left: 0; right: 0; top: calc(100% + 4px);
        min-width: 220px;
        max-height: 240px; overflow-y: auto; margin: 0; padding: 4px;
        list-style: none; background: var(--nv-surface);
        border: 1px solid var(--nv-line-strong); border-radius: 6px;
        box-shadow: 0 8px 24px rgba(0, 0, 0, .12); }
li { display: flex; justify-content: space-between; gap: 10px; align-items: baseline;
     padding: 8px 10px; border-radius: 4px; font-size: 13px; color: var(--nv-text);
     cursor: pointer; }
li.on { background: var(--nv-accent-soft); }
li[aria-selected="true"] { font-weight: 600; }
li.empty { color: var(--nv-text-muted); font-style: italic; }
li.create { color: var(--nv-accent); font-weight: 600;
            border-top: 1px solid var(--nv-line); margin-top: 2px; }
li small { color: var(--nv-text-faint); font-size: 12px; white-space: nowrap; }
li.none { color: var(--nv-text-muted); cursor: default; }
.err { color: var(--bad); font-size: 12px; margin: 6px 0 0; }
</style>
