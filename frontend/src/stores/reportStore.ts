import { create } from 'zustand'
import { reportService } from '../services/reportService'
import type {
  Report,
  ReportConfig,
  OutputFormat,
  DetailLevel,
  GeneratedContent,
  EditHistoryEntry,
} from '../types/report'
import type { SourceFile } from '../types/file'

interface ReportState {
  // Current report being generated
  currentReportId: string | null
  currentReport: Report | null
  generationStatus: {
    status: string
    progress: number
    currentStep: string
    errorMessage: string | null
  } | null

  // Report configuration form state
  selectedFiles: SourceFile[]
  config: {
    title: string
    customInstructions: string
    detailLevel: DetailLevel
    outputFormats: OutputFormat[]
    slideCountMin: number
    slideCountMax: number
  }

  // Report history
  reports: Report[]
  totalReports: number
  currentPage: number
  isLoading: boolean
  error: string | null

  // Editor state
  generatedContent: GeneratedContent | null
  selectedSectionPath: string | null
  editHistory: EditHistoryEntry[]
  isEditing: boolean

  // Actions
  addFile: (file: SourceFile) => void
  removeFile: (fileId: string) => void
  clearFiles: () => void
  updateConfig: (updates: Partial<ReportState['config']>) => void
  resetConfig: () => void

  generateReport: () => Promise<string>
  pollReportStatus: (reportId: string) => Promise<void>
  stopPolling: () => void
  fetchReport: (reportId: string) => Promise<void>
  fetchReports: (page?: number) => Promise<void>
  deleteReport: (reportId: string) => Promise<void>
  clearError: () => void

  // Editor actions
  loadGeneratedContent: (reportId: string) => Promise<void>
  selectSection: (sectionPath: string | null) => void
  editSection: (instructions: string) => Promise<void>
  undoEdit: (historyIndex: number) => void
  clearEditorState: () => void
}

const defaultConfig = {
  title: '',
  customInstructions: '',
  detailLevel: 'standard' as DetailLevel,
  outputFormats: ['pdf'] as OutputFormat[],
  slideCountMin: 10,
  slideCountMax: 15,
}

let pollingInterval: ReturnType<typeof setInterval> | null = null

export const useReportStore = create<ReportState>((set, get) => ({
  currentReportId: null,
  currentReport: null,
  generationStatus: null,
  selectedFiles: [],
  config: { ...defaultConfig },
  reports: [],
  totalReports: 0,
  currentPage: 1,
  isLoading: false,
  error: null,

  // Editor state
  generatedContent: null,
  selectedSectionPath: null,
  editHistory: [],
  isEditing: false,

  addFile: (file) => {
    set((state) => ({
      selectedFiles: [...state.selectedFiles, file],
    }))
  },

  removeFile: (fileId) => {
    set((state) => ({
      selectedFiles: state.selectedFiles.filter((f) => f.id !== fileId),
    }))
  },

  clearFiles: () => set({ selectedFiles: [] }),

  updateConfig: (updates) => {
    set((state) => ({
      config: { ...state.config, ...updates },
    }))
  },

  resetConfig: () => {
    set({
      selectedFiles: [],
      config: { ...defaultConfig },
      currentReportId: null,
      currentReport: null,
      generationStatus: null,
    })
  },

  generateReport: async () => {
    const { selectedFiles, config } = get()

    if (selectedFiles.length === 0) {
      throw new Error('Please select at least one file')
    }

    set({ isLoading: true, error: null })

    try {
      const reportConfig: ReportConfig = {
        title: config.title || undefined,
        customInstructions: config.customInstructions || undefined,
        detailLevel: config.detailLevel,
        outputFormats: config.outputFormats,
        slideCount: config.outputFormats.includes('pptx')
          ? { min: config.slideCountMin, max: config.slideCountMax }
          : undefined,
        sourceFileIds: selectedFiles.map((f) => f.id),
      }

      const response = await reportService.generateReport(reportConfig)

      set({
        currentReportId: response.report_id,
        generationStatus: {
          status: response.status,
          progress: 0,
          currentStep: 'Starting...',
          errorMessage: null,
        },
        isLoading: false,
      })

      return response.report_id
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Failed to start generation',
        isLoading: false,
      })
      throw error
    }
  },

  pollReportStatus: async (reportId) => {
    // Clear any existing polling
    if (pollingInterval) {
      clearInterval(pollingInterval)
    }

    const poll = async () => {
      try {
        const status = await reportService.getReportStatus(reportId)

        set({
          generationStatus: {
            status: status.status,
            progress: status.progress,
            currentStep: status.current_step,
            errorMessage: status.error_message,
          },
        })

        // Stop polling if completed or failed
        if (status.status === 'completed' || status.status === 'failed') {
          if (pollingInterval) {
            clearInterval(pollingInterval)
            pollingInterval = null
          }

          // Fetch full report on completion
          if (status.status === 'completed') {
            const report = await reportService.getReport(reportId)
            set({ currentReport: report })
          }
        }
      } catch (error) {
        console.error('Polling error:', error)
      }
    }

    // Initial poll
    await poll()

    // Start polling interval
    pollingInterval = setInterval(poll, 2000)
  },

  stopPolling: () => {
    if (pollingInterval) {
      clearInterval(pollingInterval)
      pollingInterval = null
    }
  },

  fetchReport: async (reportId) => {
    set({ isLoading: true, error: null })
    try {
      const report = await reportService.getReport(reportId)
      set({ currentReport: report, isLoading: false })
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Failed to fetch report',
        isLoading: false,
      })
    }
  },

  fetchReports: async (page = 1) => {
    set({ isLoading: true, error: null })
    try {
      const response = await reportService.listReports(page)
      set({
        reports: response.reports,
        totalReports: response.total,
        currentPage: page,
        isLoading: false,
      })
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Failed to fetch reports',
        isLoading: false,
      })
    }
  },

  deleteReport: async (reportId) => {
    try {
      await reportService.deleteReport(reportId)
      set((state) => ({
        reports: state.reports.filter((r) => r.id !== reportId),
        totalReports: state.totalReports - 1,
      }))
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Failed to delete report',
      })
    }
  },

  clearError: () => set({ error: null }),

  // Editor actions
  loadGeneratedContent: async (reportId: string) => {
    set({ isLoading: true, error: null })
    try {
      const content = await reportService.getGeneratedContent(reportId)
      set({
        generatedContent: content,
        currentReportId: reportId,
        isLoading: false,
      })
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Failed to load content',
        isLoading: false,
      })
    }
  },

  selectSection: (sectionPath: string | null) => {
    set({ selectedSectionPath: sectionPath })
  },

  editSection: async (instructions: string) => {
    const { currentReportId, selectedSectionPath, generatedContent } = get()

    if (!currentReportId || !selectedSectionPath || !generatedContent) {
      throw new Error('No section selected')
    }

    set({ isEditing: true, error: null })

    try {
      const response = await reportService.editSection(
        currentReportId,
        selectedSectionPath,
        instructions
      )

      // Add to history
      const historyEntry: EditHistoryEntry = {
        sectionPath: response.section_path,
        sectionTitle: selectedSectionPath,
        oldContent: response.old_content,
        newContent: response.new_content,
        appliedAt: response.applied_at,
      }

      // Reload the generated content to get the updated version
      const updatedContent = await reportService.getGeneratedContent(currentReportId)

      set((state) => ({
        generatedContent: updatedContent,
        editHistory: [historyEntry, ...state.editHistory],
        isEditing: false,
      }))
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Failed to edit section',
        isEditing: false,
      })
      throw error
    }
  },

  undoEdit: (historyIndex: number) => {
    // Note: Full undo would require backend support
    // For now, just remove from history display
    set((state) => ({
      editHistory: state.editHistory.filter((_, i) => i !== historyIndex),
    }))
  },

  clearEditorState: () => {
    set({
      generatedContent: null,
      selectedSectionPath: null,
      editHistory: [],
      isEditing: false,
    })
  },
}))
