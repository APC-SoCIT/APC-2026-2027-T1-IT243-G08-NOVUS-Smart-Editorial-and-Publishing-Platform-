import { defineStore } from 'pinia'

const KEY = 'novus.theme'

/**
 * Staff interface theme.
 *
 * Three states, not two: "system" follows the operating system, which is what
 * most people actually want. An explicit light or dark choice overrides it.
 * Only the NOVUS workspace is affected — BOSS is dark by design.
 */
export const useThemeStore = defineStore('theme', {
  state: () => ({
    preference: localStorage.getItem(KEY) || 'system',
  }),

  getters: {
    /** What is actually on screen right now. */
    resolved: (s) => {
      if (s.preference !== 'system') return s.preference
      return window.matchMedia('(prefers-color-scheme: dark)').matches
        ? 'dark' : 'light'
    },
  },

  actions: {
    apply() {
      const dark = this.resolved === 'dark'
      document.documentElement.toggleAttribute('data-theme', dark)
      if (dark) document.documentElement.setAttribute('data-theme', 'dark')
      else document.documentElement.removeAttribute('data-theme')
    },

    set(pref) {
      this.preference = pref
      localStorage.setItem(KEY, pref)
      this.apply()
    },

    /** Called once at start-up; also keeps "system" honest if the OS changes. */
    init() {
      this.apply()
      window.matchMedia('(prefers-color-scheme: dark)')
        .addEventListener('change', () => {
          if (this.preference === 'system') this.apply()
        })
    },
  },
})
