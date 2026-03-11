import { create } from 'zustand'
import { configService } from '../services/configService'

interface ConfigState {
  productionMode: boolean
  devToggleAvailable: boolean
  modelTier: 'sonnet' | 'haiku'
  isLoading: boolean

  fetchMode: () => Promise<void>
  toggleMode: () => Promise<void>
}

export const useConfigStore = create<ConfigState>((set, get) => ({
  productionMode: true,
  devToggleAvailable: false,
  modelTier: 'sonnet',
  isLoading: true,

  fetchMode: async () => {
    try {
      const status = await configService.getMode()
      set({
        productionMode: status.production_mode,
        devToggleAvailable: status.dev_toggle_available,
        modelTier: status.model_tier,
        isLoading: false,
      })
    } catch {
      // If fetch fails (e.g. not logged in yet), default to production
      set({ isLoading: false })
    }
  },

  toggleMode: async () => {
    const current = get().productionMode
    try {
      const status = await configService.setMode(!current)
      set({
        productionMode: status.production_mode,
        modelTier: status.model_tier,
      })
    } catch (err) {
      console.error('Failed to toggle mode:', err)
    }
  },
}))
