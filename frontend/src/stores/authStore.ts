import { create } from 'zustand'
import { authService } from '../services/authService'
import api from '../services/api'
import type { User, SignupRequest, LoginRequest, QuotaStatus } from '../types/auth'

interface AuthState {
  user: User | null
  quota: QuotaStatus | null
  isLoading: boolean
  error: string | null

  // Actions
  signUp: (data: SignupRequest) => Promise<void>
  signIn: (data: LoginRequest) => Promise<void>
  signOut: () => Promise<void>
  checkAuth: () => Promise<void>
  fetchQuota: () => Promise<void>
  clearError: () => void
}

export const useAuthStore = create<AuthState>((set, get) => ({
  user: null,
  quota: null,
  isLoading: true,
  error: null,

  signUp: async (data) => {
    set({ isLoading: true, error: null })
    try {
      const user = await authService.signUp(data)
      set({ user, isLoading: false })
      get().fetchQuota()
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Signup failed',
        isLoading: false,
      })
      throw error
    }
  },

  signIn: async (data) => {
    set({ isLoading: true, error: null })
    try {
      const user = await authService.signIn(data)
      set({ user, isLoading: false })
      get().fetchQuota()
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Login failed',
        isLoading: false,
      })
      throw error
    }
  },

  signOut: async () => {
    try {
      await authService.signOut()
      set({ user: null, quota: null })
    } catch (error) {
      console.error('Sign out error:', error)
    }
  },

  checkAuth: async () => {
    set({ isLoading: true })
    try {
      const user = await authService.getCurrentUser()
      set({ user, isLoading: false })
      if (user) get().fetchQuota()
    } catch {
      set({ user: null, isLoading: false })
    }
  },

  fetchQuota: async () => {
    try {
      const response = await api.get<QuotaStatus>('/auth/quota')
      set({ quota: response.data })
    } catch (error) {
      console.error('Failed to fetch quota:', error)
    }
  },

  clearError: () => set({ error: null }),
}))
