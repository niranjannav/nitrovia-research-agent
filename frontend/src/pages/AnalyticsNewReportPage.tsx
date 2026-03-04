import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import AnalyticsReportConfig from '../components/analytics/AnalyticsReportConfig'
import GenerationProgress from '../components/reports/GenerationProgress'
import { useAnalyticsStore } from '../stores/analyticsStore'
import type { ReportConfig } from '../components/analytics/AnalyticsReportConfig'

const today = new Date().toISOString().split('T')[0]

const defaultConfig: ReportConfig = {
  domain: 'sales',
  report_period: 'monthly',
  as_of_date: today,
  primary_metric: 'revenue',
  output_formats: ['pdf'],
  custom_instructions: '',
  title: '',
}

export default function AnalyticsNewReportPage() {
  const navigate = useNavigate()
  const [config, setConfig] = useState<ReportConfig>(defaultConfig)
  const [reportId, setReportId] = useState<string | null>(null)

  const { generateReport, isLoading, error, clearError } = useAnalyticsStore()

  const handleChange = (updates: Partial<ReportConfig>) => {
    setConfig((prev) => ({ ...prev, ...updates }))
  }

  const handleGenerate = async () => {
    clearError()
    try {
      const id = await generateReport({
        domain: config.domain,
        report_period: config.report_period,
        as_of_date: config.as_of_date,
        output_formats: config.output_formats,
        primary_metric: config.primary_metric,
        custom_instructions: config.custom_instructions || undefined,
        title: config.title || undefined,
      })
      setReportId(id)
    } catch {
      // error shown from store
    }
  }

  const handleComplete = () => {
    if (reportId) {
      navigate(`/reports/${reportId}`)
    }
  }

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      {/* Header */}
      <div>
        <nav className="text-sm text-gray-500 mb-2">
          <Link to="/analytics" className="hover:text-gray-700">
            Analytics
          </Link>{' '}
          / New Report
        </nav>
        <h1 className="text-2xl font-bold text-gray-900">Generate Analytics Report</h1>
        <p className="text-gray-600 mt-1">
          Configure the report parameters and Claude will generate an in-depth analytics narrative
          with charts.
        </p>
      </div>

      {/* Generation progress */}
      {reportId ? (
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
          <GenerationProgress reportId={reportId} onComplete={handleComplete} />
        </div>
      ) : (
        <>
          {/* Error */}
          {error && (
            <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm">
              {error}
            </div>
          )}

          {/* Config form */}
          <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
            <AnalyticsReportConfig config={config} onChange={handleChange} />
          </div>

          {/* No-data notice */}
          <div className="bg-amber-50 border border-amber-200 rounded-lg px-4 py-3">
            <p className="text-sm text-amber-800">
              Make sure you have uploaded data for the selected domain and period before generating.{' '}
              <Link to="/analytics/upload" className="font-medium underline hover:text-amber-900">
                Upload data
              </Link>
            </p>
          </div>

          {/* Generate button */}
          <div className="flex justify-end">
            <button
              onClick={handleGenerate}
              disabled={isLoading || !config.as_of_date}
              className="px-6 py-2.5 bg-primary-600 text-white rounded-lg font-medium text-sm hover:bg-primary-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
            >
              {isLoading ? (
                <>
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white" />
                  Starting…
                </>
              ) : (
                'Generate Report'
              )}
            </button>
          </div>
        </>
      )}
    </div>
  )
}
