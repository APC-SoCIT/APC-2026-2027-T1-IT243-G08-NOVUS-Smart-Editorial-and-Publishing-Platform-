import { defineStore } from 'pinia'
import api from '../services/api'

export const useAuthStore = defineStore('auth', {
  state: () => ({
    user: null,
    access: localStorage.getItem('access') || null,
  }),
  getters: {
    isAuthenticated: (s) => !!s.access,
    role: (s) => s.user?.role || null,
  },
  actions: {
    /* Step one, the password. Returns { codeRequired: true, challenge,
       sentTo, staff } when an emailed code must follow (always for staff),
       or signs in at once and returns { codeRequired: false }. */
    async login(email, password) {
      const { data } = await api.post('/auth/token/', { email, password })
      if (data.code_required) {
        return { codeRequired: true, challenge: data.challenge,
                 sentTo: data.sent_to, staff: data.staff }
      }
      await this.setTokens(data)
      return { codeRequired: false }
    },
    /* Step two, the code from the email. */
    async verifyCode(challenge, code) {
      const { data } = await api.post('/auth/token/code/', { challenge, code })
      await this.setTokens(data)
    },
    async resendCode(challenge) {
      const { data } = await api.post('/auth/token/resend/', { challenge })
      return data
    },
    async setTokens(data) {
      this.access = data.access
      localStorage.setItem('access', data.access)
      localStorage.setItem('refresh', data.refresh)
      await this.fetchUser()
    },
    async fetchUser() {
      const { data } = await api.get('/auth/me/')
      this.user = data
    },
    logout() {
      this.user = null
      this.access = null
      localStorage.removeItem('access')
      localStorage.removeItem('refresh')
    },
  },
})
