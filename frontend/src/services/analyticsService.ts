import api from './api'
import type {
  AnalyticsDomain,
  InferSchemaResponse,
  SchemaMapping,
  SavedMapping,
  AnalyticsUpload,
  AnalyticsReportRequest,
  ChatMessage,
} from '../types/analytics'

export const analyticsService = {
  async inferSchema(file: File, domain: AnalyticsDomain): Promise<InferSchemaResponse> {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('domain', domain)
    const response = await api.post('/analytics/schema/infer', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    return response.data
  },

  async getSavedMapping(domain: AnalyticsDomain): Promise<SavedMapping | null> {
    try {
      const response = await api.get(`/analytics/schema/${domain}`)
      return response.data
    } catch (error: unknown) {
      if ((error as { response?: { status?: number } }).response?.status === 404) return null
      throw error
    }
  },

  async confirmMapping(
    domain: AnalyticsDomain,
    mapping: SchemaMapping,
    mappingName: string,
    mappingId?: string,
  ): Promise<{ mapping_id: string }> {
    const response = await api.post('/analytics/schema/confirm', {
      domain,
      mapping,
      mapping_name: mappingName,
      mapping_id: mappingId,
    })
    return response.data
  },

  async uploadFile(
    file: File,
    domain: AnalyticsDomain,
    periodStart: string,
    periodEnd: string,
    mappingId?: string,
  ): Promise<{ upload_id: string; status: string }> {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('domain', domain)
    formData.append('period_start', periodStart)
    formData.append('period_end', periodEnd)
    if (mappingId) formData.append('mapping_id', mappingId)
    const response = await api.post('/analytics/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    return response.data
  },

  async getUploadStatus(uploadId: string): Promise<AnalyticsUpload> {
    const response = await api.get(`/analytics/uploads/${uploadId}`)
    return response.data
  },

  async listUploads(domain?: AnalyticsDomain): Promise<AnalyticsUpload[]> {
    const params = domain ? { domain } : {}
    const response = await api.get('/analytics/uploads', { params })
    return response.data.uploads
  },

  async deleteUpload(uploadId: string): Promise<void> {
    await api.delete(`/analytics/uploads/${uploadId}`)
  },

  async generateReport(
    config: AnalyticsReportRequest,
  ): Promise<{ report_id: string; status: string }> {
    const response = await api.post('/analytics/reports/generate', config)
    return response.data
  },

  async chatWithData(
    domain: AnalyticsDomain,
    message: string,
    history: Pick<ChatMessage, 'role' | 'content'>[],
  ): Promise<{ answer: string }> {
    const response = await api.post('/analytics/chat', {
      domain,
      message,
      conversation_history: history.filter((m) => m.role !== 'system'),
    })
    return response.data
  },
}
