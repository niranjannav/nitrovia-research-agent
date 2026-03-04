import { useCallback, useEffect, useState } from 'react'
import { useDropzone } from 'react-dropzone'
import { useNavigate } from 'react-router-dom'
import { useAnalyticsStore } from '../stores/analyticsStore'
import AnalyticsChat from '../components/analytics/AnalyticsChat'
import ReportConfigModal from '../components/analytics/ReportConfigModal'
import GenerationProgress from '../components/reports/GenerationProgress'
import type { AnalyticsDomain, AnalyticsUpload } from '../types/analytics'

const DOMAINS: { value: AnalyticsDomain; label: string; available: boolean }[] = [
  { value: 'sales', label: 'Sales', available: true },
  { value: 'finance', label: 'Finance', available: true },
  { value: 'production', label: 'Production', available: false },
  { value: 'qa', label: 'QA', available: false },
]

function todayIso() {
  return new Date().toISOString().split('T')[0]
}

function oneYearAgoIso() {
  const d = new Date()
  d.setFullYear(d.getFullYear() - 1)
  return d.toISOString().split('T')[0]
}

export default function AnalyticsPage() {
  const {
    selectedDomain,
    setSelectedDomain,
    uploads,
    isUploading,
    currentUpload,
    fetchUploads,
    uploadFile,
    pollUploadStatus,
    stopUploadPolling,
    deleteUpload,
    error,
    clearError,
  } = useAnalyticsStore()

  const navigate = useNavigate()
  const [reportModalOpen, setReportModalOpen] = useState(false)
  const [activeReportId, setActiveReportId] = useState<string | null>(null)

  // On mount: fetch uploads for current domain
  useEffect(() => {
    fetchUploads(selectedDomain)
  }, [selectedDomain, fetchUploads])

  // Poll current upload if uploading
  useEffect(() => {
    if (currentUpload?.id && currentUpload.status === 'processing') {
      pollUploadStatus(currentUpload.id)
    }
    return () => stopUploadPolling()
  }, [currentUpload?.id, currentUpload?.status, pollUploadStatus, stopUploadPolling])

  const domainUploads = uploads.filter((u) => u.domain === selectedDomain)
  const hasCompletedUpload = domainUploads.some((u) => u.status === 'completed')

  const onDrop = useCallback(
    async (acceptedFiles: File[]) => {
      const file = acceptedFiles[0]
      if (!file) return
      clearError()
      try {
        const uploadId = await uploadFile(
          file,
          selectedDomain,
          oneYearAgoIso(),
          todayIso(),
        )
        pollUploadStatus(uploadId)
      } catch {
        // error shown via store
      }
    },
    [selectedDomain, uploadFile, pollUploadStatus, clearError],
  )

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'],
      'application/vnd.ms-excel': ['.xls'],
    },
    maxFiles: 1,
    disabled: isUploading,
  })

  const handleReportSubmit = (reportId: string) => {
    setActiveReportId(reportId)
  }

  const handleReportComplete = () => {
    if (activeReportId) {
      navigate(`/reports/${activeReportId}`)
    }
  }

  return (
    <div className="flex h-[calc(100vh-64px)] overflow-hidden bg-gray-50">
      {/* Left Panel */}
      <div className="w-72 flex-shrink-0 border-r border-gray-200 bg-white flex flex-col overflow-hidden">
        <div className="flex-1 overflow-y-auto p-4 space-y-5">
          {/* Domain selector */}
          <div>
            <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">
              Domain
            </p>
            <div className="grid grid-cols-2 gap-1.5">
              {DOMAINS.map((d) => (
                <button
                  key={d.value}
                  onClick={() => d.available && setSelectedDomain(d.value)}
                  disabled={!d.available}
                  title={d.available ? undefined : 'Coming soon'}
                  className={`py-1.5 px-2 rounded-lg text-sm font-medium transition-colors text-center ${
                    d.value === selectedDomain
                      ? 'bg-primary-600 text-white'
                      : d.available
                      ? 'text-gray-700 hover:bg-gray-100'
                      : 'text-gray-300 cursor-not-allowed'
                  }`}
                >
                  {d.label}
                  {!d.available && (
                    <span className="block text-[10px] font-normal opacity-70">soon</span>
                  )}
                </button>
              ))}
            </div>
          </div>

          {/* Drop zone */}
          <div>
            <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">
              Upload Data
            </p>
            <div
              {...getRootProps()}
              className={`border-2 border-dashed rounded-xl p-4 text-center cursor-pointer transition-colors ${
                isDragActive
                  ? 'border-primary-400 bg-primary-50'
                  : isUploading
                  ? 'border-gray-200 bg-gray-50 cursor-not-allowed'
                  : 'border-gray-300 hover:border-primary-400 hover:bg-primary-50/30'
              }`}
            >
              <input {...getInputProps()} />
              {isUploading ? (
                <div className="flex flex-col items-center gap-2 py-1">
                  <div className="w-5 h-5 border-2 border-primary-500 border-t-transparent rounded-full animate-spin" />
                  <p className="text-xs text-gray-500">Uploading…</p>
                </div>
              ) : (
                <div className="flex flex-col items-center gap-1.5 py-1">
                  <svg
                    className="w-7 h-7 text-gray-400"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={1.5}
                      d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12"
                    />
                  </svg>
                  <p className="text-xs font-medium text-gray-600">
                    {isDragActive ? 'Drop here' : 'Drop .xlsx / .xls'}
                  </p>
                  <p className="text-[11px] text-gray-400">or click to browse</p>
                </div>
              )}
            </div>

            {error && (
              <p className="mt-2 text-xs text-red-600 bg-red-50 rounded-lg px-3 py-2">
                {error}
              </p>
            )}
          </div>

          {/* Uploads list */}
          <div>
            <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">
              Uploads ({domainUploads.length})
            </p>
            {domainUploads.length === 0 ? (
              <p className="text-xs text-gray-400 text-center py-4">No uploads yet</p>
            ) : (
              <ul className="space-y-1.5">
                {domainUploads.map((upload) => (
                  <UploadItem
                    key={upload.id}
                    upload={upload}
                    onDelete={() => deleteUpload(upload.id)}
                  />
                ))}
              </ul>
            )}
          </div>
        </div>
      </div>

      {/* Right Panel — Chat */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {activeReportId ? (
          <div className="flex-1 overflow-y-auto p-6">
            <div className="max-w-2xl mx-auto">
              <div className="flex items-center gap-3 mb-4">
                <button
                  onClick={() => setActiveReportId(null)}
                  className="text-sm text-gray-500 hover:text-gray-700 flex items-center gap-1"
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
                  </svg>
                  Back to chat
                </button>
              </div>
              <GenerationProgress
                reportId={activeReportId}
                onComplete={handleReportComplete}
              />
            </div>
          </div>
        ) : (
          <AnalyticsChat
            domain={selectedDomain}
            hasData={hasCompletedUpload}
            onGenerateReport={() => setReportModalOpen(true)}
          />
        )}
      </div>

      {/* Report Config Modal */}
      <ReportConfigModal
        open={reportModalOpen}
        domain={selectedDomain}
        onClose={() => setReportModalOpen(false)}
        onSubmit={handleReportSubmit}
      />
    </div>
  )
}

function UploadItem({
  upload,
  onDelete,
}: {
  upload: AnalyticsUpload
  onDelete: () => void
}) {
  const statusIcon: Record<string, React.ReactNode> = {
    completed: (
      <svg className="w-3.5 h-3.5 text-green-500 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
        <path
          fillRule="evenodd"
          d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
          clipRule="evenodd"
        />
      </svg>
    ),
    processing: (
      <div className="w-3.5 h-3.5 border-2 border-primary-400 border-t-transparent rounded-full animate-spin flex-shrink-0" />
    ),
    pending: (
      <div className="w-3.5 h-3.5 border-2 border-gray-300 border-t-transparent rounded-full animate-spin flex-shrink-0" />
    ),
    failed: (
      <svg className="w-3.5 h-3.5 text-red-500 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
        <path
          fillRule="evenodd"
          d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"
          clipRule="evenodd"
        />
      </svg>
    ),
  }

  const timeAgo = (isoStr: string) => {
    const diff = Date.now() - new Date(isoStr).getTime()
    const mins = Math.floor(diff / 60000)
    if (mins < 60) return `${mins}m ago`
    const hrs = Math.floor(mins / 60)
    if (hrs < 24) return `${hrs}h ago`
    return `${Math.floor(hrs / 24)}d ago`
  }

  return (
    <li className="flex items-start gap-2 px-2.5 py-2 rounded-lg hover:bg-gray-50 group">
      <div className="mt-0.5">{statusIcon[upload.status] ?? null}</div>
      <div className="flex-1 min-w-0">
        <p className="text-xs font-medium text-gray-800 truncate" title={upload.file_name}>
          {upload.file_name}
        </p>
        <p className="text-[11px] text-gray-400">
          {timeAgo(upload.created_at)}
          {upload.row_count ? ` · ${upload.row_count.toLocaleString()} rows` : ''}
        </p>
      </div>
      <button
        onClick={onDelete}
        className="opacity-0 group-hover:opacity-100 text-gray-300 hover:text-red-400 transition-opacity"
        title="Delete upload"
      >
        <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
        </svg>
      </button>
    </li>
  )
}
