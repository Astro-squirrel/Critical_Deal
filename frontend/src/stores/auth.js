import { defineStore } from 'pinia'
import { accountsApi } from '../api/accounts'

export const useAuthStore = defineStore('auth', {
  state: () => ({ user: null, loading: false, error: '' }),
  actions: {
    async login(payload) {
      this.loading = true
      this.error = ''
      try {
        this.user = await accountsApi.login(payload)
      } catch (error) {
        this.error = error.message
        throw error
      } finally {
        this.loading = false
      }
    },
    async signup(payload) {
      this.user = await accountsApi.signup(payload)
    },
    async fetchMe() {
      try {
        this.user = await accountsApi.me()
      } catch {
        this.user = null
      }
    },
    async logout() {
      try {
        await accountsApi.logout()
      } catch {
        // Treat logout as complete locally even if the session was already gone.
      } finally {
        this.user = null
      }
    },
  },
})

