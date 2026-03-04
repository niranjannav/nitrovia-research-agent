import { useEffect, useRef, useState } from 'react'
import AnalyticsReportConfig, { type ReportConfig } from './AnalyticsReportConfig'
import type { AnalyticsDomain } from '../../types/analytics'
import { useAnalyticsStore } from '../../stores/analyticsStore'

interface Props {
  open: boolean
  domain: AnalyticsDomain
  onClose: () => void
  onSubmit: (reportId: string) => void
}

function todayIso() {
  return new Date().toISOString().split('T')[0]
}

function defaultConfig(domain: AnalyticsDomain): ReportConfig {
  return {
    domain,
    report_period: 'monthly',
    as_of_date: todayIso(),
    primary_metric: domain === 'finance' ? 'revenue' : 'revenue',
    output_formats: ['pdf'],
    custom_instructions: '',
    title: '',
  }
}

export default function ReportConfigModal({ open, domain, onClose, onSubmit }: Props) {
  const { generateReport, isLoading, error } = useAnalyticsStore()
  const [config, setConfig] = useState<ReportConfig>(() => defaultConfig(domain))
  const overlayRef = useRef<HTMLDivElement>(null)

  // Reset config when domain changes or modal opens
  useEffect(() => {
    if (open) {
      setConfig(defaultConfig(domain))
    }
  }, [open, domain])

  // Close on Escape
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', handler)
    return () => document.removeEventListener('keydown', handler)
  }, [onClose])

  const handleOverlayClick = (e: React.MouseEvent) => {
    if (e.target === overlayRef.current) onClose()
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      const reportId = await generateReport({
        domain: config.domain,
        report_period: config.report_period,
        as_of_date: config.as_of_date,
        output_formats: config.output_formats,
        primary_metric: config.primary_metric,
        custom_instructions: config.custom_instructions || undefined,
        title: config.title || undefined,
      })
      onSubmit(reportId)
      onClose()
    } catch {
      // error displayed via store
    }
  }

  if (!open) return null

  return (
    <div
      ref={overlayRef}
      onClick={handleOverlayClick}
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm p-4"
    >
      <div className="w-full max-w-2xl bg-white rounded-2xl shadow-2xl flex flex-col max-h-[90vh]">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
          <h2 className="text-lg font-semibold text-gray-900">Generate Analytics Report</h2>
          <button
            onClick={onClose}
            className="w-8 h-8 flex items-center justify-center rounded-lg text-gray-400 hover:text-gray-600 hover:bg-gray-100 transition-colors"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Body */}
        <form onSubmit={handleSubmit} className="flex flex-col flex-1 overflow-hidden">
          <div className="flex-1 overflow-y-auto px-6 py-5">
            <AnalyticsReportConfig
              config={config}
              onChange={(updates) => setConfig((prev) => ({ ...prev, ...updates }))}
            />

            {error && (
              <div className="mt-4 rounded-lg bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-700">
                {error}
              </div>
            )}
          </div>

          {/* Footer */}
          <div className="flex items-center justify-end gap-3 px-6 py-4 border-t border-gray-200 bg-gray-50 rounded-b-2xl">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isLoading}
              className="px-5 py-2 text-sm font-medium text-white bg-primary-600 rounded-lg hover:bg-primary-700 disabled:opacity-50 transition-colors"
            >
              {isLoading ? 'Generating…' : 'Generate Report'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
