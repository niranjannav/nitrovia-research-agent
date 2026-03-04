import { create } from 'zustand'
import { analyticsService } from '../services/analyticsService'
import type {
  AnalyticsDomain,
  SchemaMapping,
  SavedMapping,
  InferSchemaResponse,
  AnalyticsUpload,
  AnalyticsReportRequest,
  ChatMessage,
} from '../types/analytics'

interface AnalyticsState {
  // Domain selection
  selectedDomain: AnalyticsDomain
  setSelectedDomain: (domain: AnalyticsDomain) => void

  // Schema inference
  inferredSchema: InferSchemaResponse | null
  savedMapping: SavedMapping | null
  mappingId: string | null
  isInferring: boolean

  // Upload
  uploads: AnalyticsUpload[]
  currentUploadId: string | null
  currentUpload: AnalyticsUpload | null
  isUploading: boolean

  // Report generation
  generatingReportId: string | null

  // Chat
  chatMessages: Record<string, ChatMessage[]>
  isChatLoading: boolean
  sendChatMessage: (domain: AnalyticsDomain, message: string) => Promise<void>
  clearChat: (domain: AnalyticsDomain) => void

  // UI
  isLoading: boolean
  error: string | null

  // Actions
  inferSchema: (file: File, domain: AnalyticsDomain) => Promise<void>
  fetchSavedMapping: (domain: AnalyticsDomain) => Promise<void>
  confirmMapping: (domain: AnalyticsDomain, mapping: SchemaMapping, name: string) => Promise<void>
  uploadFile: (
    file: File,
    domain: AnalyticsDomain,
    periodStart: string,
    periodEnd: string,
  ) => Promise<string>
  pollUploadStatus: (uploadId: string) => void
  stopUploadPolling: () => void
  fetchUploads: (domain?: AnalyticsDomain) => Promise<void>
  deleteUpload: (uploadId: string) => Promise<void>
  generateReport: (config: AnalyticsReportRequest) => Promise<string>
  clearInferred: () => void
  resetUpload: () => void
  clearError: () => void
}

let uploadPollingInterval: ReturnType<typeof setInterval> | null = null

function makeMessage(
  role: ChatMessage['role'],
  content: string,
): ChatMessage {
  return { id: crypto.randomUUID(), role, content, timestamp: new Date() }
}

export const useAnalyticsStore = create<AnalyticsState>((set, get) => ({
  selectedDomain: 'sales',
  setSelectedDomain: (domain) => {
    set({ selectedDomain: domain })
  },

  inferredSchema: null,
  savedMapping: null,
  mappingId: null,
  isInferring: false,

  uploads: [],
  currentUploadId: null,
  currentUpload: null,
  isUploading: false,

  generatingReportId: null,
  isLoading: false,
  error: null,

  chatMessages: {},
  isChatLoading: false,

  sendChatMessage: async (domain, message) => {
    const userMsg = makeMessage('user', message)
    set((state) => ({
      chatMessages: {
        ...state.chatMessages,
        [domain]: [...(state.chatMessages[domain] || []), userMsg],
      },
      isChatLoading: true,
    }))

    try {
      const history = (get().chatMessages[domain] || []).map((m) => ({
        role: m.role as 'user' | 'assistant',
        content: m.content,
      }))
      const { answer } = await analyticsService.chatWithData(domain, message, history)
      const assistantMsg = makeMessage('assistant', answer)
      set((state) => ({
        chatMessages: {
          ...state.chatMessages,
          [domain]: [...(state.chatMessages[domain] || []), assistantMsg],
        },
        isChatLoading: false,
      }))
    } catch (err) {
      const errMsg = makeMessage(
        'system',
        'Failed to get a response. Please try again.',
      )
      set((state) => ({
        chatMessages: {
          ...state.chatMessages,
          [domain]: [...(state.chatMessages[domain] || []), errMsg],
        },
        isChatLoading: false,
      }))
    }
  },

  clearChat: (domain) => {
    set((state) => ({
      chatMessages: { ...state.chatMessages, [domain]: [] },
    }))
  },

  inferSchema: async (file, domain) => {
    set({ isInferring: true, error: null, inferredSchema: null })
    try {
      const result = await analyticsService.inferSchema(file, domain)
      set({ inferredSchema: result, isInferring: false })
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Schema inference failed',
        isInferring: false,
      })
      throw error
    }
  },

  fetchSavedMapping: async (domain) => {
    set({ isLoading: true, error: null })
    try {
      const saved = await analyticsService.getSavedMapping(domain)
      set({ savedMapping: saved, mappingId: saved?.id ?? null, isLoading: false })
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Failed to fetch mapping',
        isLoading: false,
      })
    }
  },

  confirmMapping: async (domain, mapping, name) => {
    set({ isLoading: true, error: null })
    try {
      const { mappingId } = get()
      const result = await analyticsService.confirmMapping(
        domain,
        mapping,
        name,
        mappingId ?? undefined,
      )
      set({ mappingId: result.mapping_id, isLoading: false })
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Failed to save mapping',
        isLoading: false,
      })
      throw error
    }
  },

  uploadFile: async (file, domain, periodStart, periodEnd) => {
    set({ isUploading: true, error: null, currentUpload: null })
    try {
      // No mappingId required — backend auto-infers if needed
      const result = await analyticsService.uploadFile(
        file,
        domain,
        periodStart,
        periodEnd,
      )
      set({ currentUploadId: result.upload_id, isUploading: false })
      return result.upload_id
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Upload failed',
        isUploading: false,
      })
      throw error
    }
  },

  pollUploadStatus: (uploadId) => {
    if (uploadPollingInterval) clearInterval(uploadPollingInterval)

    const poll = async () => {
      try {
        const upload = await analyticsService.getUploadStatus(uploadId)
        set({ currentUpload: upload })
        if (upload.status === 'completed' || upload.status === 'failed') {
          if (uploadPollingInterval) {
            clearInterval(uploadPollingInterval)
            uploadPollingInterval = null
          }
          get().fetchUploads()
        }
      } catch (err) {
        console.error('Upload polling error:', err)
      }
    }

    poll()
    uploadPollingInterval = setInterval(poll, 2000)
  },

  stopUploadPolling: () => {
    if (uploadPollingInterval) {
      clearInterval(uploadPollingInterval)
      uploadPollingInterval = null
    }
  },

  fetchUploads: async (domain) => {
    set({ isLoading: true, error: null })
    try {
      const uploads = await analyticsService.listUploads(domain)
      set({ uploads, isLoading: false })
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Failed to fetch uploads',
        isLoading: false,
      })
    }
  },

  deleteUpload: async (uploadId) => {
    try {
      await analyticsService.deleteUpload(uploadId)
      set((state) => ({
        uploads: state.uploads.filter((u) => u.id !== uploadId),
      }))
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Failed to delete upload',
      })
    }
  },

  generateReport: async (config) => {
    set({ isLoading: true, error: null })
    try {
      const result = await analyticsService.generateReport(config)
      set({ generatingReportId: result.report_id, isLoading: false })
      return result.report_id
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Failed to generate report',
        isLoading: false,
      })
      throw error
    }
  },

  clearInferred: () => set({ inferredSchema: null }),

  resetUpload: () =>
    set({
      currentUploadId: null,
      currentUpload: null,
      inferredSchema: null,
      isUploading: false,
    }),

  clearError: () => set({ error: null }),
}))
