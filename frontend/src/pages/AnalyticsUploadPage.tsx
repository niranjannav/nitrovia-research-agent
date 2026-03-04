import { useCallback, useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useDropzone } from 'react-dropzone'
import SchemaMappingReview from '../components/analytics/SchemaMappingReview'
import { useAnalyticsStore } from '../stores/analyticsStore'
import type { AnalyticsDomain, SchemaMapping } from '../types/analytics'

type Step = 'configure' | 'schema_review' | 'uploading' | 'done'

const DOMAINS: { value: AnalyticsDomain; label: string; description: string }[] = [
  { value: 'sales', label: 'Sales', description: 'Revenue, quantity, channel breakdown' },
  { value: 'production', label: 'Production', description: 'Output, yield, efficiency' },
  { value: 'qa', label: 'Quality Assurance', description: 'Pass rates, defects, compliance' },
  { value: 'finance', label: 'Finance', description: 'P&L, costs, margins' },
]

export default function AnalyticsUploadPage() {
  const navigate = useNavigate()

  // Wizard state
  const [step, setStep] = useState<Step>('configure')
  const [domain, setDomain] = useState<AnalyticsDomain>('sales')
  const [periodStart, setPeriodStart] = useState('')
  const [periodEnd, setPeriodEnd] = useState('')
  const [file, setFile] = useState<File | null>(null)
  const [configError, setConfigError] = useState('')

  const {
    inferredSchema,
    savedMapping,
    mappingId,
    isInferring,
    currentUpload,
    isUploading,
    isLoading,
    error,
    inferSchema,
    fetchSavedMapping,
    confirmMapping,
    uploadFile,
    pollUploadStatus,
    stopUploadPolling,
    clearInferred,
    resetUpload,
    clearError,
  } = useAnalyticsStore()

  // Fetch saved mapping when domain changes
  useEffect(() => {
    fetchSavedMapping(domain)
  }, [domain, fetchSavedMapping])

  // Stop polling on unmount
  useEffect(() => {
    return () => stopUploadPolling()
  }, [stopUploadPolling])

  // Watch upload completion
  useEffect(() => {
    if (step === 'uploading' && currentUpload) {
      if (currentUpload.status === 'completed' || currentUpload.status === 'failed') {
        setStep('done')
      }
    }
  }, [currentUpload?.status, step])

  const onDrop = useCallback((acceptedFiles: File[]) => {
    if (acceptedFiles.length > 0) setFile(acceptedFiles[0])
  }, [])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'],
      'application/vnd.ms-excel': ['.xls'],
    },
    maxFiles: 1,
    multiple: false,
  })

  const handleProceed = async () => {
    clearError()
    if (!periodStart || !periodEnd) {
      setConfigError('Please select both a start and end date.')
      return
    }
    if (new Date(periodEnd) < new Date(periodStart)) {
      setConfigError('End date must be after start date.')
      return
    }
    if (!file) {
      setConfigError('Please drop an Excel file.')
      return
    }
    setConfigError('')

    if (savedMapping) {
      // Has saved mapping — go straight to upload
      await doUpload()
    } else {
      // No saved mapping — infer schema first
      try {
        await inferSchema(file, domain)
        setStep('schema_review')
      } catch {
        // error shown from store
      }
    }
  }

  const handleSchemaConfirm = async (mapping: SchemaMapping, name: string) => {
    try {
      await confirmMapping(domain, mapping, name)
      await doUpload()
    } catch {
      // error shown from store
    }
  }

  const handleSchemaCancel = () => {
    clearInferred()
    setStep('configure')
  }

  const doUpload = async () => {
    if (!file) return
    try {
      setStep('uploading')
      const uploadId = await uploadFile(file, domain, periodStart, periodEnd)
      pollUploadStatus(uploadId)
    } catch {
      setStep('configure')
    }
  }

  const handleUploadAnother = () => {
    resetUpload()
    setFile(null)
    setPeriodStart('')
    setPeriodEnd('')
    setStep('configure')
  }

  const handleReInfer = () => {
    if (!file) return
    clearInferred()
    inferSchema(file, domain).then(() => setStep('schema_review'))
  }

  // ── Render ─────────────────────────────────────────────────────────────────

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      {/* Header */}
      <div>
        <nav className="text-sm text-gray-500 mb-2">
          <Link to="/analytics" className="hover:text-gray-700">
            Analytics
          </Link>{' '}
          / Upload Data
        </nav>
        <h1 className="text-2xl font-bold text-gray-900">Upload Analytics Data</h1>
        <p className="text-gray-600 mt-1">
          Upload an Excel file to ingest structured data for analytics reporting.
        </p>
      </div>

      {/* Error from store */}
      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm">
          {error}
        </div>
      )}

      {/* ── Step: Schema Review ─────────────────────────────────────────────── */}
      {step === 'schema_review' && inferredSchema && (
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
          <div className="mb-5">
            <h2 className="text-lg font-semibold text-gray-900">Review Inferred Schema</h2>
            <p className="text-sm text-gray-500 mt-1">
              The AI analysed your Excel file and inferred the structure below. Confirm it's correct
              before uploading.
            </p>
          </div>
          <SchemaMappingReview
            mapping={inferredSchema.mapping}
            suggestedName={inferredSchema.suggested_name}
            onConfirm={handleSchemaConfirm}
            onCancel={handleSchemaCancel}
            isLoading={isLoading || isUploading}
          />
        </div>
      )}

      {/* ── Step: Uploading / Done ──────────────────────────────────────────── */}
      {(step === 'uploading' || step === 'done') && (
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-8 text-center space-y-4">
          {step === 'uploading' && !currentUpload && (
            <>
              <div className="inline-flex items-center justify-center w-16 h-16 bg-primary-100 rounded-full mx-auto">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600" />
              </div>
              <p className="text-gray-700 font-medium">Uploading file…</p>
            </>
          )}

          {currentUpload && (
            <>
              {currentUpload.status === 'completed' ? (
                <div className="inline-flex items-center justify-center w-16 h-16 bg-green-100 rounded-full mx-auto">
                  <svg className="w-8 h-8 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                </div>
              ) : currentUpload.status === 'failed' ? (
                <div className="inline-flex items-center justify-center w-16 h-16 bg-red-100 rounded-full mx-auto">
                  <svg className="w-8 h-8 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </div>
              ) : (
                <div className="inline-flex items-center justify-center w-16 h-16 bg-primary-100 rounded-full mx-auto">
                  <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600" />
                </div>
              )}

              <div>
                <p className="text-lg font-medium text-gray-900">
                  {currentUpload.status === 'completed'
                    ? 'Data ingested successfully!'
                    : currentUpload.status === 'failed'
                    ? 'Ingestion failed'
                    : 'Processing data…'}
                </p>
                {currentUpload.status === 'completed' && currentUpload.row_count != null && (
                  <p className="text-sm text-gray-500 mt-1">
                    {currentUpload.row_count.toLocaleString()} records ingested from{' '}
                    {currentUpload.file_name}
                  </p>
                )}
                {currentUpload.status === 'failed' && currentUpload.error_message && (
                  <p className="text-sm text-red-600 mt-1">{currentUpload.error_message}</p>
                )}
              </div>

              {step === 'done' && (
                <div className="flex justify-center gap-3 pt-2">
                  <button
                    onClick={handleUploadAnother}
                    className="px-4 py-2 border border-gray-300 rounded-lg text-sm font-medium text-gray-700 hover:bg-gray-50 transition-colors"
                  >
                    Upload another file
                  </button>
                  {currentUpload.status === 'completed' && (
                    <Link
                      to="/analytics/reports/new"
                      className="px-4 py-2 bg-primary-600 text-white rounded-lg text-sm font-medium hover:bg-primary-700 transition-colors"
                    >
                      Generate report
                    </Link>
                  )}
                </div>
              )}
            </>
          )}
        </div>
      )}

      {/* ── Step: Configure ─────────────────────────────────────────────────── */}
      {step === 'configure' && (
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6 space-y-6">
          {/* Domain */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Domain</label>
            <div className="grid grid-cols-2 gap-3">
              {DOMAINS.map((d) => (
                <button
                  key={d.value}
                  type="button"
                  onClick={() => setDomain(d.value)}
                  className={`p-3 border rounded-lg text-left transition-colors ${
                    domain === d.value
                      ? 'border-primary-500 bg-primary-50 ring-1 ring-primary-500'
                      : 'border-gray-300 hover:border-gray-400'
                  }`}
                >
                  <p className="font-medium text-sm text-gray-900">{d.label}</p>
                  <p className="text-xs text-gray-500 mt-0.5">{d.description}</p>
                </button>
              ))}
            </div>
          </div>

          {/* Date Range */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Data Period
            </label>
            <div className="flex items-center gap-3 flex-wrap">
              <div>
                <label className="block text-xs text-gray-500 mb-1">From</label>
                <input
                  type="date"
                  value={periodStart}
                  onChange={(e) => setPeriodStart(e.target.value)}
                  className="px-3 py-2 border border-gray-300 rounded-lg shadow-sm focus:ring-primary-500 focus:border-primary-500 text-sm"
                />
              </div>
              <span className="text-gray-400 mt-4">—</span>
              <div>
                <label className="block text-xs text-gray-500 mb-1">To</label>
                <input
                  type="date"
                  value={periodEnd}
                  onChange={(e) => setPeriodEnd(e.target.value)}
                  className="px-3 py-2 border border-gray-300 rounded-lg shadow-sm focus:ring-primary-500 focus:border-primary-500 text-sm"
                />
              </div>
            </div>
            <p className="text-xs text-gray-500 mt-1">
              The date range the Excel file covers. Historical uploads accumulate in the database.
            </p>
          </div>

          {/* Saved mapping indicator */}
          {savedMapping && (
            <div className="flex items-start justify-between bg-green-50 border border-green-200 rounded-lg px-4 py-3">
              <div>
                <p className="text-sm font-medium text-green-800">
                  Saved mapping: {savedMapping.mapping_name || `${domain} format`}
                </p>
                <p className="text-xs text-green-600 mt-0.5">
                  Schema will be applied automatically. No review step needed.
                </p>
              </div>
              {file && (
                <button
                  onClick={handleReInfer}
                  disabled={isInferring}
                  className="text-xs text-green-700 underline hover:text-green-900 ml-4 flex-shrink-0"
                >
                  Re-infer
                </button>
              )}
            </div>
          )}

          {!savedMapping && (
            <div className="flex items-center gap-2 text-sm text-gray-500">
              <svg className="w-4 h-4 text-amber-400" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
              </svg>
              No saved mapping for {domain}. The AI will infer the schema from your file.
            </div>
          )}

          {/* File Drop Zone */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Excel File
            </label>
            <div
              {...getRootProps()}
              className={`border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors ${
                isDragActive
                  ? 'border-primary-400 bg-primary-50'
                  : file
                  ? 'border-green-400 bg-green-50'
                  : 'border-gray-300 hover:border-gray-400 hover:bg-gray-50'
              }`}
            >
              <input {...getInputProps()} />
              {file ? (
                <div className="space-y-1">
                  <svg className="mx-auto w-10 h-10 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                  <p className="font-medium text-gray-900 text-sm">{file.name}</p>
                  <p className="text-xs text-gray-500">
                    {(file.size / 1024 / 1024).toFixed(1)} MB — click to replace
                  </p>
                </div>
              ) : isDragActive ? (
                <p className="text-primary-600 font-medium">Drop the file here…</p>
              ) : (
                <div className="space-y-2">
                  <svg className="mx-auto w-10 h-10 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                  </svg>
                  <p className="text-sm text-gray-600">
                    <span className="font-medium text-primary-600">Click to upload</span> or drag and drop
                  </p>
                  <p className="text-xs text-gray-400">Excel files only (.xlsx, .xls)</p>
                </div>
              )}
            </div>
          </div>

          {/* Config Error */}
          {configError && <p className="text-sm text-red-600">{configError}</p>}

          {/* Action Button */}
          <div className="flex justify-end">
            <button
              onClick={handleProceed}
              disabled={isInferring || isUploading || isLoading}
              className="px-6 py-2.5 bg-primary-600 text-white rounded-lg font-medium text-sm hover:bg-primary-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
            >
              {isInferring ? (
                <>
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white" />
                  Analysing file…
                </>
              ) : savedMapping ? (
                'Upload & Process'
              ) : (
                'Infer Schema & Continue'
              )}
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
