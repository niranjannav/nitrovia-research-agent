import { useState, useEffect } from 'react'
import { useReportStore } from '../stores/reportStore'
import { useAuthStore } from '../stores/authStore'
import FileUploader from '../components/files/FileUploader'
import FileList from '../components/files/FileList'
import ReportConfigForm from '../components/reports/ReportConfigForm'
import GenerationProgress from '../components/reports/GenerationProgress'
import ReportEditor from '../components/reports/ReportEditor'
import DocumentChat from '../components/chat/DocumentChat'

type Step = 'upload' | 'chat' | 'generating' | 'editing'

export default function NewReportPage() {
  const {
    selectedFiles,
    generateReport,
    currentReportId,
    currentReport,
    generationStatus,
    resetConfig,
    clearEditorState,
    error,
    clearError,
    isLoading,
  } = useReportStore()

  const { quota, fetchQuota } = useAuthStore()
  const [step, setStep] = useState<Step>('upload')
  const [showReportConfig, setShowReportConfig] = useState(false)

  useEffect(() => {
    fetchQuota()
  }, [fetchQuota])

  // Transition to editing when generation completes
  useEffect(() => {
    if (
      step === 'generating' &&
      generationStatus?.status === 'completed' &&
      currentReportId
    ) {
      setStep('editing')
      fetchQuota()
    }
  }, [step, generationStatus?.status, currentReportId, fetchQuota])

  const quotaExceeded = quota && !quota.is_admin && quota.exceeded

  const handleStartGeneration = async () => {
    try {
      clearError()
      await generateReport()
      setStep('generating')
      setShowReportConfig(false)
    } catch {
      // Error handled by store
    }
  }

  const handleComplete = () => {
    if (currentReportId) setStep('editing')
  }

  const handleNewReport = () => {
    resetConfig()
    clearEditorState()
    setStep('upload')
    setShowReportConfig(false)
  }

  const handleDownload = (format: 'pdf' | 'docx' | 'pptx') => {
    const file = currentReport?.output_files?.find((f) => f.format === format)
    if (file?.download_url) window.open(file.download_url, '_blank')
  }

  // Map store files to the shape DocumentChat expects
  const chatFiles = selectedFiles.map((f) => ({
    id: f.id,
    name: f.name,
    type: f.type,
  }))

  return (
    <div className={step === 'editing' ? 'max-w-7xl mx-auto' : step === 'chat' ? 'max-w-6xl mx-auto' : 'max-w-3xl mx-auto'}>
      {/* Header */}
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">
            {step === 'editing' ? 'Edit Report' : step === 'chat' ? 'Document Research' : 'Create New Report'}
          </h1>
          <p className="text-gray-600 mt-1">
            {step === 'editing'
              ? 'Click any section to select it, then enter your edit instructions'
              : step === 'chat'
              ? 'Ask questions about your documents or generate a research report'
              : 'Upload documents to analyze and research'}
          </p>
        </div>
        {(step === 'editing' || step === 'chat') && (
          <button
            onClick={handleNewReport}
            className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
          >
            New Report
          </button>
        )}
      </div>

      {/* Step progress indicator (upload only) */}
      {step === 'upload' && (
        <div className="mb-8">
          <div className="flex items-center">
            <StepIndicator stepNumber={1} label="Upload" isActive isCompleted={false} />
            <div className="flex-1 mx-4 h-px bg-gray-200" />
            <StepIndicator stepNumber={2} label="Research & Chat" isActive={false} isCompleted={false} />
            <div className="flex-1 mx-4 h-px bg-gray-200" />
            <StepIndicator stepNumber={3} label="Generate" isActive={false} isCompleted={false} />
          </div>
        </div>
      )}

      {step === 'generating' && (
        <div className="mb-8">
          <div className="flex items-center">
            <StepIndicator stepNumber={1} label="Upload" isActive={false} isCompleted />
            <div className="flex-1 mx-4 h-px bg-primary-200" />
            <StepIndicator stepNumber={2} label="Research & Chat" isActive={false} isCompleted />
            <div className="flex-1 mx-4 h-px bg-primary-200" />
            <StepIndicator stepNumber={3} label="Generate" isActive isCompleted={false} />
          </div>
        </div>
      )}

      {/* Error message */}
      {error && (
        <div className="mb-6 bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm">
          {error}
        </div>
      )}

      {/* Quota indicator */}
      {quota && !quota.is_admin && step !== 'editing' && (
        <div
          className={`mb-6 px-4 py-3 rounded-lg text-sm flex items-center justify-between ${
            quota.exceeded
              ? 'bg-red-50 border border-red-200 text-red-700'
              : quota.remaining <= 1
              ? 'bg-amber-50 border border-amber-200 text-amber-700'
              : 'bg-blue-50 border border-blue-200 text-blue-700'
          }`}
        >
          <div className="flex items-center gap-2">
            <svg className="w-4 h-4 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <span>
              {quota.exceeded
                ? `Monthly limit reached (${quota.used}/${quota.limit} reports). Resets ${new Date(quota.resets_at).toLocaleDateString()}.`
                : `${quota.used}/${quota.limit} reports used this month`}
            </span>
          </div>
          {!quota.exceeded && (
            <span className="font-medium">{quota.remaining} remaining</span>
          )}
        </div>
      )}

      {/* ── UPLOAD STEP ─────────────────────────────────────────── */}
      {step === 'upload' && (
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6 space-y-6">
          <FileUploader />
          <FileList />
          <div className="flex justify-end pt-4 border-t border-gray-100">
            <button
              onClick={() => setStep('chat')}
              disabled={selectedFiles.length === 0}
              className="px-6 py-2.5 bg-primary-600 text-white rounded-lg font-medium hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center gap-2"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
              </svg>
              Chat with Documents
            </button>
          </div>
        </div>
      )}

      {/* ── CHAT STEP ───────────────────────────────────────────── */}
      {step === 'chat' && (
        <div className="flex gap-4" style={{ height: 'calc(100vh - 220px)', minHeight: '560px' }}>
          {/* Left sidebar: file list */}
          <div className="w-56 flex-shrink-0 bg-white rounded-xl shadow-sm border border-gray-100 flex flex-col">
            <div className="px-3 py-3 border-b border-gray-100">
              <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wide">
                Documents ({selectedFiles.length})
              </h3>
            </div>
            <div className="flex-1 overflow-y-auto py-2">
              {selectedFiles.map((file) => (
                <div key={file.id} className="flex items-start gap-2 px-3 py-2 hover:bg-gray-50 rounded-lg mx-1">
                  <FileTypeBadge type={file.type} />
                  <div className="min-w-0">
                    <p className="text-xs font-medium text-gray-700 truncate" title={file.name}>
                      {file.name}
                    </p>
                    <p className="text-xs text-gray-400">{formatBytes(file.size)}</p>
                  </div>
                </div>
              ))}
            </div>
            <div className="p-3 border-t border-gray-100">
              <button
                onClick={() => setStep('upload')}
                className="w-full text-xs text-gray-500 hover:text-gray-700 py-1 flex items-center justify-center gap-1 transition-colors"
              >
                <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                </svg>
                Add more files
              </button>
            </div>
          </div>

          {/* Right panel: chat + optional report config */}
          <div className="flex-1 flex flex-col gap-4 min-w-0">
            {/* Chat window */}
            <div className={`bg-white rounded-xl shadow-sm border border-gray-100 flex flex-col ${showReportConfig ? 'flex-1' : 'flex-1'}`}
              style={{ minHeight: 0 }}>
              <DocumentChat
                selectedFiles={chatFiles}
                onGenerateReport={() => setShowReportConfig((v) => !v)}
                showReportConfig={showReportConfig}
              />
            </div>

            {/* Report config panel (shown when toggled) */}
            {showReportConfig && (
              <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-5 flex-shrink-0">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-sm font-semibold text-gray-900">Report Configuration</h3>
                  <button
                    onClick={() => setShowReportConfig(false)}
                    className="text-gray-400 hover:text-gray-600"
                  >
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                    </svg>
                  </button>
                </div>
                <ReportConfigForm />
                <div className="flex justify-end mt-4 pt-4 border-t border-gray-100">
                  <button
                    onClick={handleStartGeneration}
                    disabled={isLoading || selectedFiles.length === 0 || !!quotaExceeded}
                    className="px-6 py-2.5 bg-primary-600 text-white rounded-lg font-medium hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center gap-2"
                  >
                    {quotaExceeded ? (
                      'Limit Reached'
                    ) : isLoading ? (
                      <>
                        <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                        Starting…
                      </>
                    ) : (
                      <>
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                        </svg>
                        Generate Report
                      </>
                    )}
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* ── GENERATING STEP ─────────────────────────────────────── */}
      {step === 'generating' && currentReportId && (
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6 space-y-6">
          <GenerationProgress reportId={currentReportId} onComplete={handleComplete} />
          <div className="flex justify-center pt-4 border-t border-gray-100">
            <button
              onClick={handleNewReport}
              className="px-6 py-2.5 border border-gray-300 text-gray-700 rounded-lg font-medium hover:bg-gray-50 transition-colors"
            >
              Create Another Report
            </button>
          </div>
        </div>
      )}

      {/* ── EDITING STEP ────────────────────────────────────────── */}
      {step === 'editing' && currentReportId && (
        <ReportEditor
          reportId={currentReportId}
          onDownload={handleDownload}
          downloadUrls={
            currentReport?.output_files?.map((f) => ({
              format: f.format,
              download_url: f.download_url || '',
            })) || []
          }
        />
      )}
    </div>
  )
}

// ── Sub-components ────────────────────────────────────────────────────────────

interface StepIndicatorProps {
  stepNumber: number
  label: string
  isActive: boolean
  isCompleted: boolean
}

function StepIndicator({ stepNumber, label, isActive, isCompleted }: StepIndicatorProps) {
  return (
    <div className={`flex items-center ${isActive ? 'text-primary-600' : 'text-gray-400'}`}>
      <span
        className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium ${
          isActive || isCompleted ? 'bg-primary-600 text-white' : 'bg-gray-200 text-gray-600'
        }`}
      >
        {isCompleted && !isActive ? <CheckIcon /> : stepNumber}
      </span>
      <span className="ml-2 text-sm font-medium">{label}</span>
    </div>
  )
}

function CheckIcon() {
  return (
    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
    </svg>
  )
}

function FileTypeBadge({ type }: { type: string }) {
  const colors: Record<string, string> = {
    pdf: 'bg-red-100 text-red-700',
    docx: 'bg-blue-100 text-blue-700',
    doc: 'bg-blue-100 text-blue-700',
    xlsx: 'bg-green-100 text-green-700',
    xls: 'bg-green-100 text-green-700',
    pptx: 'bg-orange-100 text-orange-700',
    ppt: 'bg-orange-100 text-orange-700',
  }
  return (
    <span
      className={`flex-shrink-0 inline-block px-1.5 py-0.5 rounded text-[10px] font-bold uppercase ${
        colors[type] || 'bg-gray-100 text-gray-600'
      }`}
    >
      {type}
    </span>
  )
}

function formatBytes(bytes: number): string {
  if (!bytes) return ''
  if (bytes < 1024) return `${bytes}B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)}KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)}MB`
}
