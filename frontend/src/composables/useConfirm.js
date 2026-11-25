/* "Double take": one confirmation step before any decision.

     if (!(await confirm({ title: 'Approve this layout?', confirmLabel: 'Approve' }))) return

   One dialog for the whole app (ConfirmHost in App.vue), so a page asks
   with a single line instead of its own dialog, flag and handlers. */
import { reactive } from 'vue'

const state = reactive({
  open: false, title: '', message: '', points: [],
  confirmLabel: 'Confirm', tone: 'primary', requireText: '',
})
let settle = null

export function confirm(options = {}) {
  settle?.(false)               // a newer question replaces an unanswered one
  Object.assign(state, {
    title: 'Are you sure?', message: '', points: [],
    confirmLabel: 'Confirm', tone: 'primary', requireText: '',
    ...options, open: true,
  })
  return new Promise((resolve) => { settle = resolve })
}

export function answer(ok) {
  state.open = false
  const done = settle
  settle = null
  done?.(ok)
}

export const confirmState = state
