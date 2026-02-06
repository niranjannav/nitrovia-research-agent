import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useReportStore } from '../stores/reportStore'
import FileUploader from '../components/files/FileUploader'
import FileList from '../components/files/FileList'
import ReportConfigForm from '../components/reports/ReportConfigForm'
import GenerationProgress from '../components/reports/GenerationProgress'

type Step = 'upload' | 'configure' | 'generating'

export default function NewReportPage() {
  const navigate = useNavigate()
  const {
    selectedFiles,
    generateReport,
    currentReportId,
    resetConfig,
    error,
    clearError,
    isLoading,
  } = useReportStore()

  const [step, setStep] = useState<Step>('upload')

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
    // Optionally navigate to history or stay on page
  }

  const handleNewReport = () => {
    resetConfig()
    setStep('upload')
  }

  return (
    <div className="max-w-3xl mx-auto">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">Create New Report</h1>
        <p className="text-gray-600 mt-1">
          Upload documents and configure your report settings
        </p>
      </div>

      {/* Progress indicator */}
      <div className="mb-8">
        <div className="flex items-center">
          <div
            className={`flex items-center ${
              step === 'upload' ? 'text-primary-600' : 'text-gray-400'
            }`}
          >
            <span
              className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium ${
                step === 'upload'
                  ? 'bg-primary-600 text-white'
                  : step !== 'upload'
                  ? 'bg-primary-600 text-white'
                  : 'bg-gray-200 text-gray-600'
              }`}
            >
              1
            </span>
            <span className="ml-2 text-sm font-medium">Upload</span>
          </div>

          <div className="flex-1 mx-4 h-px bg-gray-200" />

          <div
            className={`flex items-center ${
              step === 'configure' ? 'text-primary-600' : 'text-gray-400'
            }`}
          >
            <span
              className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium ${
                step === 'configure'
                  ? 'bg-primary-600 text-white'
                  : step === 'generating'
                  ? 'bg-primary-600 text-white'
                  : 'bg-gray-200 text-gray-600'
              }`}
            >
              2
            </span>
            <span className="ml-2 text-sm font-medium">Configure</span>
          </div>

          <div className="flex-1 mx-4 h-px bg-gray-200" />

          <div
            className={`flex items-center ${
              step === 'generating' ? 'text-primary-600' : 'text-gray-400'
            }`}
          >
            <span
              className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium ${
                step === 'generating'
                  ? 'bg-primary-600 text-white'
                  : 'bg-gray-200 text-gray-600'
              }`}
            >
              3
            </span>
            <span className="ml-2 text-sm font-medium">Generate</span>
          </div>
        </div>
      </div>

      {/* Error message */}
      {error && (
        <div className="mb-6 bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm">
          {error}
        </div>
      )}

      {/* Step content */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
        {step === 'upload' && (
          <div className="space-y-6">
            <FileUploader />
            <FileList />

            <div className="flex justify-end pt-4 border-t border-gray-100">
              <button
                onClick={() => setStep('configure')}
                disabled={selectedFiles.length === 0}
                className="px-6 py-2.5 bg-primary-600 text-white rounded-lg font-medium hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
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
                className="px-6 py-2.5 border border-gray-300 text-gray-700 rounded-lg font-medium hover:bg-gray-50 transition-colors"
              >
                Back
              </button>
              <button
                onClick={handleStartGeneration}
                disabled={isLoading || selectedFiles.length === 0}
                className="px-6 py-2.5 bg-primary-600 text-white rounded-lg font-medium hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
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
                className="px-6 py-2.5 border border-gray-300 text-gray-700 rounded-lg font-medium hover:bg-gray-50 transition-colors"
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
