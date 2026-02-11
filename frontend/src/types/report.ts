export type DetailLevel = 'executive' | 'standard' | 'comprehensive'
export type OutputFormat = 'pdf' | 'docx' | 'pptx'
export type ReportStatus = 'pending' | 'processing' | 'completed' | 'failed'

export interface SlideCountConfig {
  min: number
  max: number
}

export interface ReportConfig {
  title?: string
  customInstructions?: string
  detailLevel: DetailLevel
  outputFormats: OutputFormat[]
  slideCount?: SlideCountConfig
  sourceFileIds: string[]
}

export interface OutputFile {
  format: OutputFormat
  storage_path?: string
  download_url?: string
  expires_at?: string
}

export interface Report {
  id: string
  title: string | null
  status: ReportStatus
  progress: number
  detail_level: DetailLevel
  output_formats: OutputFormat[]
  custom_instructions: string | null
  source_files: { id: string }[] | null
  output_files: OutputFile[] | null
  error_message: string | null
  total_input_tokens: number | null
  total_output_tokens: number | null
  generation_time_seconds: number | null
  created_at: string | null
  completed_at: string | null
}

export interface ReportStatus {
  status: string
  progress: number
  current_step: string
  error_message: string | null
}

export interface GenerateReportResponse {
  report_id: string
  status: string
  estimated_time_seconds: number
}

export interface ReportListResponse {
  reports: Report[]
  total: number
  page: number
  pages: number
}

// Generated content types
export interface ReportSection {
  title: string
  content: string
  subsections: ReportSection[]
}

export interface GeneratedReport {
  title: string
  executive_summary: string
  sections: ReportSection[]
  key_findings: string[]
  recommendations: string[]
  sources: string[]
}

export interface GeneratedPresentation {
  title: string
  slides: {
    type: string
    title: string
    subtitle?: string
    bullets?: string[]
    findings?: string[]
    items?: string[]
  }[]
}

export interface GeneratedContent {
  report: GeneratedReport
  presentation?: GeneratedPresentation
}

// Section editing types
export interface EditHistoryEntry {
  sectionPath: string
  sectionTitle: string
  oldContent: string
  newContent: string
  appliedAt: string
}

export interface EditSectionRequest {
  instructions: string
}

export interface EditSectionResponse {
  section_path: string
  old_content: string
  new_content: string
  applied_at: string
}
