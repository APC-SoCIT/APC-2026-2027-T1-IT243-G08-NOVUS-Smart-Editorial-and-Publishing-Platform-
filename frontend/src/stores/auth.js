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
    async login(email, password) {
      const { data } = await api.post('/auth/token/', { email, password })
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
