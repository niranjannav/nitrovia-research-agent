export type AnalyticsDomain = 'sales' | 'production' | 'qa' | 'finance'
export type ReportPeriod = 'weekly' | 'monthly' | 'quarterly' | 'annual'
export type UploadStatus = 'pending' | 'processing' | 'completed' | 'failed'

export interface MetricBlock {
  label: string
  start_col: number
  end_col: number
  maps_to?: string
}

export interface TimeStructure {
  type:
    | 'wide_monthly'
    | 'wide_weekly'
    | 'long_date_col'
    | 'quarterly_pivot'
    | 'annual_only'
    | 'dual_metric_wide_monthly'
    | 'transposed_financial'
  columns?: string[]
  year_source?: string
  date_column?: string
  date_format?: string
  quarter_columns?: string[]
  metric_column?: string
  group_column?: string
  // dual_metric_wide_monthly
  metric_blocks?: MetricBlock[]
  // transposed_financial
  label_column?: string
  row_label_map?: Record<string, string>
  date_header_row?: number
}

export interface ChatMessage {
  id: string
  role: 'user' | 'assistant' | 'system'
  content: string
  timestamp: Date
}

export interface DerivedField {
  source?: string
  method?: 'prefix_2chars' | 'prefix_lookup' | 'regex' | 'constant' | 'companion_sheet_join' | 'lookup_table'
  mappings?: Record<string, string>
  sheet_pattern?: string
  pattern?: string
  value?: string
  lookup_col?: string
  result_col?: string
}

export interface SchemaMapping {
  domain: string
  source_sheets: string[]
  primary_metric: string
  header_row: number
  column_roles: Record<string, string>
  time_structure: TimeStructure
  derived_fields?: Record<string, DerivedField>
  revenue_sheet_pattern?: string
  exclude_sheets?: string[]
  warnings?: string[]
}

export interface SheetDescription {
  name: string
  has_formulas: boolean
  row_count: number
  columns: string[]
  sample_rows: unknown[][]
}

export interface SheetSummary {
  file_name: string
  total_sheets: number
  sheets: SheetDescription[]
}

export interface InferSchemaResponse {
  mapping: SchemaMapping
  sheet_summary: SheetSummary
  suggested_name?: string
}

export interface SavedMapping {
  id: string
  domain: AnalyticsDomain
  mapping_name: string | null
  mapping: SchemaMapping
  confirmed_by_user: boolean
  created_at: string
}

export interface AnalyticsUpload {
  id: string
  domain: AnalyticsDomain
  mapping_id: string | null
  period_start: string
  period_end: string
  file_name: string
  status: UploadStatus
  row_count: number | null
  created_at: string
  error_message?: string
}

export interface AnalyticsReportRequest {
  domain: AnalyticsDomain
  report_period: ReportPeriod
  as_of_date: string
  output_formats: string[]
  primary_metric: string
  custom_instructions?: string
  title?: string
}
