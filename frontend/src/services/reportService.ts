import api from './api'
import type {
  Report,
  ReportConfig,
  GenerateReportResponse,
  ReportListResponse,
} from '../types/report'

interface ReportStatusResponse {
  status: string
  progress: number
  current_step: string
  error_message: string | null
}

export const reportService = {
  async generateReport(config: ReportConfig): Promise<GenerateReportResponse> {
    const response = await api.post<GenerateReportResponse>('/reports/generate', {
      title: config.title,
      custom_instructions: config.customInstructions,
      detail_level: config.detailLevel,
      output_formats: config.outputFormats,
      slide_count: config.slideCount,
      source_file_ids: config.sourceFileIds,
    })

    return response.data
  },

  async getReport(reportId: string): Promise<Report> {
    const response = await api.get<Report>(`/reports/${reportId}`)
    return response.data
  },

  async getReportStatus(reportId: string): Promise<ReportStatusResponse> {
    const response = await api.get<ReportStatusResponse>(`/reports/${reportId}/status`)
    return response.data
  },

  async listReports(page = 1, limit = 20, status?: string): Promise<ReportListResponse> {
    const params: Record<string, unknown> = { page, limit }
    if (status) params.status = status

    const response = await api.get<ReportListResponse>('/reports', { params })
    return response.data
  },

  async deleteReport(reportId: string): Promise<void> {
    await api.delete(`/reports/${reportId}`)
  },
}
