import type { AnalyticsDomain, ReportPeriod } from '../../types/analytics'

const DOMAINS: { value: AnalyticsDomain; label: string; metrics: string[] }[] = [
  {
    value: 'sales',
    label: 'Sales',
    metrics: ['revenue', 'quantity_units', 'quantity_litres'],
  },
  {
    value: 'production',
    label: 'Production',
    metrics: ['quantity_produced', 'yield_rate', 'efficiency_rate', 'waste_rate'],
  },
  {
    value: 'qa',
    label: 'Quality Assurance',
    metrics: ['pass_rate', 'defect_rate', 'test_count', 'compliance_rate'],
  },
  {
    value: 'finance',
    label: 'Finance',
    metrics: ['revenue', 'gross_profit', 'net_profit', 'operating_costs'],
  },
]

const PERIODS: { value: ReportPeriod; label: string; description: string }[] = [
  { value: 'weekly', label: 'Weekly', description: 'WoW + daily trends' },
  { value: 'monthly', label: 'Monthly', description: 'MoM, YTD, SMLY' },
  { value: 'quarterly', label: 'Quarterly', description: 'QoQ + SQLY' },
  { value: 'annual', label: 'Annual', description: 'Year-over-year' },
]

export interface ReportConfig {
  domain: AnalyticsDomain
  report_period: ReportPeriod
  as_of_date: string
  primary_metric: string
  output_formats: string[]
  custom_instructions: string
  title: string
}

interface Props {
  config: ReportConfig
  onChange: (updates: Partial<ReportConfig>) => void
}

const OUTPUT_FORMATS = [
  { value: 'pdf', label: 'PDF' },
  { value: 'docx', label: 'Word (DOCX)' },
  { value: 'pptx', label: 'PowerPoint (PPTX)' },
]

export default function AnalyticsReportConfig({ config, onChange }: Props) {
  const selectedDomain = DOMAINS.find((d) => d.value === config.domain)

  const toggleFormat = (fmt: string) => {
    const current = config.output_formats
    if (current.includes(fmt)) {
      if (current.length > 1) {
        onChange({ output_formats: current.filter((f) => f !== fmt) })
      }
    } else {
      onChange({ output_formats: [...current, fmt] })
    }
  }

  const handleDomainChange = (domain: AnalyticsDomain) => {
    const d = DOMAINS.find((x) => x.value === domain)
    onChange({ domain, primary_metric: d?.metrics[0] ?? 'revenue' })
  }

  return (
    <div className="space-y-6">
      {/* Report Title */}
      <div>
        <label htmlFor="report_title" className="block text-sm font-medium text-gray-700 mb-1">
          Report Title (optional)
        </label>
        <input
          id="report_title"
          type="text"
          value={config.title}
          onChange={(e) => onChange({ title: e.target.value })}
          className="block w-full px-3 py-2 border border-gray-300 rounded-lg shadow-sm focus:ring-primary-500 focus:border-primary-500"
          placeholder="Auto-generated if left blank"
        />
      </div>

      {/* Domain */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">Domain</label>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          {DOMAINS.map((d) => (
            <button
              key={d.value}
              type="button"
              onClick={() => handleDomainChange(d.value)}
              className={`p-3 border rounded-lg text-sm font-medium text-left transition-colors ${
                config.domain === d.value
                  ? 'border-primary-500 bg-primary-50 text-primary-700 ring-1 ring-primary-500'
                  : 'border-gray-300 text-gray-700 hover:border-gray-400'
              }`}
            >
              {d.label}
            </button>
          ))}
        </div>
      </div>

      {/* Report Period */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">Report Period</label>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          {PERIODS.map((p) => (
            <button
              key={p.value}
              type="button"
              onClick={() => onChange({ report_period: p.value })}
              className={`p-3 border rounded-lg text-left transition-colors ${
                config.report_period === p.value
                  ? 'border-primary-500 bg-primary-50 ring-1 ring-primary-500'
                  : 'border-gray-300 hover:border-gray-400'
              }`}
            >
              <p className="font-medium text-sm text-gray-900">{p.label}</p>
              <p className="text-xs text-gray-500 mt-0.5">{p.description}</p>
            </button>
          ))}
        </div>
      </div>

      {/* As-of Date */}
      <div>
        <label htmlFor="as_of_date" className="block text-sm font-medium text-gray-700 mb-1">
          As-of Date
        </label>
        <input
          id="as_of_date"
          type="date"
          value={config.as_of_date}
          onChange={(e) => onChange({ as_of_date: e.target.value })}
          className="block w-full sm:w-48 px-3 py-2 border border-gray-300 rounded-lg shadow-sm focus:ring-primary-500 focus:border-primary-500"
        />
        <p className="text-xs text-gray-500 mt-1">
          Report covers all data up to and including this date.
        </p>
      </div>

      {/* Primary Metric */}
      <div>
        <label htmlFor="primary_metric" className="block text-sm font-medium text-gray-700 mb-1">
          Primary Metric
        </label>
        <select
          id="primary_metric"
          value={config.primary_metric}
          onChange={(e) => onChange({ primary_metric: e.target.value })}
          className="block w-full sm:w-64 px-3 py-2 border border-gray-300 rounded-lg shadow-sm focus:ring-primary-500 focus:border-primary-500"
        >
          {(selectedDomain?.metrics ?? []).map((m) => (
            <option key={m} value={m}>
              {m.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())}
            </option>
          ))}
        </select>
      </div>

      {/* Output Formats */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">Output Formats</label>
        <div className="flex flex-wrap gap-2">
          {OUTPUT_FORMATS.map((fmt) => (
            <button
              key={fmt.value}
              type="button"
              onClick={() => toggleFormat(fmt.value)}
              className={`px-4 py-2 border rounded-lg text-sm font-medium transition-colors ${
                config.output_formats.includes(fmt.value)
                  ? 'border-primary-500 bg-primary-50 text-primary-700'
                  : 'border-gray-300 text-gray-700 hover:border-gray-400'
              }`}
            >
              {fmt.label}
            </button>
          ))}
        </div>
      </div>

      {/* Custom Instructions */}
      <div>
        <label
          htmlFor="custom_instructions"
          className="block text-sm font-medium text-gray-700 mb-1"
        >
          Custom Instructions (optional)
        </label>
        <textarea
          id="custom_instructions"
          rows={3}
          value={config.custom_instructions}
          onChange={(e) => onChange({ custom_instructions: e.target.value })}
          className="block w-full px-3 py-2 border border-gray-300 rounded-lg shadow-sm focus:ring-primary-500 focus:border-primary-500"
          placeholder="Any specific focus areas, tone, or requirements for this report…"
        />
      </div>
    </div>
  )
}
