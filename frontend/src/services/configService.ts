import api from './api'

export interface ModeStatus {
  production_mode: boolean
  dev_toggle_available: boolean
  model_tier: 'sonnet' | 'haiku'
}

export const configService = {
  async getMode(): Promise<ModeStatus> {
    const { data } = await api.get<ModeStatus>('/config/mode')
    return data
  },

  async setMode(productionMode: boolean): Promise<ModeStatus> {
    const { data } = await api.put<ModeStatus>('/config/mode', {
      production_mode: productionMode,
    })
    return data
  },
}
