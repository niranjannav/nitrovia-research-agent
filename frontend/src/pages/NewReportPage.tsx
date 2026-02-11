import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useReportStore } from '../stores/reportStore'
import FileUploader from '../components/files/FileUploader'
import FileList from '../components/files/FileList'
import ReportConfigForm from '../components/reports/ReportConfigForm'
import GenerationProgress from '../components/reports/GenerationProgress'
import ReportEditor from '../components/reports/ReportEditor'

type Step = 'upload' | 'configure' | 'generating' | 'editing'

export default function NewReportPage() {
  const navigate = useNavigate()
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

  const [step, setStep] = useState<Step>('upload')

  // Transition to editing when generation completes
  useEffect(() => {
    if (
      step === 'generating' &&
      generationStatus?.status === 'completed' &&
      currentReportId
    ) {
      setStep('editing')
    }
  }, [step, generationStatus?.status, currentReportId])

  const handleStartGeneration = async () => {
    try {
      clearError()
      await generateReport()
      setStep('generating')
    } catch {
      // Error handled by store
    }
  }

  const handleComplete = () => {
    if (currentReportId) {
      setStep('editing')
    }
  }

  const handleNewReport = () => {
    resetConfig()
    clearEditorState()
    setStep('upload')
  }

  const handleDownload = (format: 'pdf' | 'docx' | 'pptx') => {
    const file = currentReport?.output_files?.find((f) => f.format === format)
    if (file?.download_url) {
      window.open(file.download_url, '_blank')
    }
  }

  if (step === 'editing' && currentReportId) {
    return (
      <div className="max-w-7xl mx-auto">
        <div className="mb-8 flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Edit Report</h1>
            <p className="text-gray-400 mt-1">
              Click any section to select it, then enter your edit instructions
            </p>
          </div>
          <button
            onClick={handleNewReport}
            className="px-4 py-2 text-sm font-medium text-gray-600 bg-white border border-gray-200 rounded-xl hover:bg-gray-50 transition-colors"
          >
            New Report
          </button>
        </div>
        <div className="bg-white rounded-2xl shadow-soft border border-gray-100 overflow-hidden" style={{ height: 'calc(100vh - 200px)' }}>
          <ReportEditor
            reportId={currentReportId}
            onDownload={handleDownload}
            downloadUrls={currentReport?.output_files?.map((f) => ({
              format: f.format,
              download_url: f.download_url || '',
            })) || []}
          />
        </div>
      </div>
    )
  }

  return (
    <div className="max-w-3xl mx-auto">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">Create New Report</h1>
        <p className="text-gray-400 mt-1">
          Upload documents and configure your report settings
        </p>
      </div>

      {/* Progress indicator */}
      <div className="mb-8">
        <div className="flex items-center">
          <StepIndicator
            stepNumber={1}
            label="Upload"
            isActive={step === 'upload'}
            isCompleted={step !== 'upload'}
          />
          <div className={`flex-1 mx-4 h-px ${step !== 'upload' ? 'bg-primary-300' : 'bg-gray-200'}`} />
          <StepIndicator
            stepNumber={2}
            label="Configure"
            isActive={step === 'configure'}
            isCompleted={step === 'generating'}
          />
          <div className={`flex-1 mx-4 h-px ${step === 'generating' ? 'bg-primary-300' : 'bg-gray-200'}`} />
          <StepIndicator
            stepNumber={3}
            label="Generate"
            isActive={step === 'generating'}
            isCompleted={false}
          />
        </div>
      </div>

      {/* Error message */}
      {error && (
        <div className="mb-6 bg-red-50 border border-red-100 text-red-600 px-4 py-3 rounded-xl text-sm">
          {error}
        </div>
      )}

      {/* Step content */}
      <div className="bg-white rounded-2xl shadow-soft border border-gray-100 p-6">
        {step === 'upload' && (
          <div className="space-y-6">
            <FileUploader />
            <FileList />

            <div className="flex justify-end pt-4 border-t border-gray-100">
              <button
                onClick={() => setStep('configure')}
                disabled={selectedFiles.length === 0}
                className="px-6 py-2.5 bg-primary-600 text-white rounded-xl font-medium hover:bg-primary-700 disabled:opacity-30 disabled:cursor-not-allowed transition-colors shadow-soft"
              >
                Continue
              </button>
            </div>
          </div>
        )}

        {step === 'configure' && (
          <div className="space-y-6">
            <ReportConfigForm />

            <div className="flex justify-between pt-4 border-t border-gray-100">
              <button
                onClick={() => setStep('upload')}
                className="px-6 py-2.5 border border-gray-200 text-gray-600 rounded-xl font-medium hover:bg-gray-50 transition-colors"
              >
                Back
              </button>
              <button
                onClick={handleStartGeneration}
                disabled={isLoading || selectedFiles.length === 0}
                className="px-6 py-2.5 bg-primary-600 text-white rounded-xl font-medium hover:bg-primary-700 disabled:opacity-30 disabled:cursor-not-allowed transition-colors shadow-soft"
              >
                {isLoading ? 'Starting...' : 'Generate Report'}
              </button>
            </div>
          </div>
        )}

        {step === 'generating' && currentReportId && (
          <div className="space-y-6">
            <GenerationProgress
              reportId={currentReportId}
              onComplete={handleComplete}
            />

            <div className="flex justify-center pt-4 border-t border-gray-100">
              <button
                onClick={handleNewReport}
                className="px-6 py-2.5 border border-gray-200 text-gray-600 rounded-xl font-medium hover:bg-gray-50 transition-colors"
              >
                Create Another Report
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

interface StepIndicatorProps {
  stepNumber: number
  label: string
  isActive: boolean
  isCompleted: boolean
}

function StepIndicator({ stepNumber, label, isActive, isCompleted }: StepIndicatorProps) {
  return (
    <div
      className={`flex items-center ${
        isActive ? 'text-primary-600' : isCompleted ? 'text-primary-500' : 'text-gray-400'
      }`}
    >
      <span
        className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium transition-colors ${
          isActive
            ? 'bg-primary-600 text-white shadow-soft'
            : isCompleted
            ? 'bg-primary-500 text-white'
            : 'bg-gray-100 text-gray-500'
        }`}
      >
        {isCompleted && !isActive ? (
          <CheckIcon />
        ) : (
          stepNumber
        )}
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
