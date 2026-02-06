import { useEffect } from 'react'
import { useReportStore } from '../../stores/reportStore'

interface GenerationProgressProps {
  reportId: string
  onComplete?: () => void
}

export default function GenerationProgress({ reportId, onComplete }: GenerationProgressProps) {
  const { generationStatus, currentReport, pollReportStatus, stopPolling } = useReportStore()

  useEffect(() => {
    pollReportStatus(reportId)

    return () => {
      stopPolling()
    }
  }, [reportId, pollReportStatus, stopPolling])

  useEffect(() => {
    if (generationStatus?.status === 'completed' && onComplete) {
      onComplete()
    }
  }, [generationStatus?.status, onComplete])

  if (!generationStatus) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
      </div>
    )
  }

  const { status, progress, currentStep, errorMessage } = generationStatus

  return (
    <div className="space-y-6">
      {/* Status Header */}
      <div className="text-center">
        {status === 'completed' ? (
          <div className="inline-flex items-center justify-center w-16 h-16 bg-green-100 rounded-full mb-4">
            <svg
              className="w-8 h-8 text-green-500"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M5 13l4 4L19 7"
              />
            </svg>
          </div>
        ) : status === 'failed' ? (
          <div className="inline-flex items-center justify-center w-16 h-16 bg-red-100 rounded-full mb-4">
            <svg
              className="w-8 h-8 text-red-500"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M6 18L18 6M6 6l12 12"
              />
            </svg>
          </div>
        ) : (
          <div className="inline-flex items-center justify-center w-16 h-16 bg-primary-100 rounded-full mb-4">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
          </div>
        )}

        <h3 className="text-lg font-medium text-gray-900">
          {status === 'completed'
            ? 'Report Ready!'
            : status === 'failed'
            ? 'Generation Failed'
            : 'Generating Report...'}
        </h3>

        <p className="text-sm text-gray-500 mt-1">{currentStep}</p>
      </div>

      {/* Progress Bar */}
      {status !== 'failed' && (
        <div className="space-y-2">
          <div className="flex justify-between text-sm text-gray-600">
            <span>Progress</span>
            <span>{progress}%</span>
          </div>
          <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
            <div
              className={`h-full transition-all duration-500 rounded-full ${
                status === 'completed' ? 'bg-green-500' : 'bg-primary-500'
              }`}
              style={{ width: `${progress}%` }}
            />
          </div>
        </div>
      )}

      {/* Error Message */}
      {status === 'failed' && errorMessage && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm">
          {errorMessage}
        </div>
      )}

      {/* Download Buttons */}
      {status === 'completed' && currentReport?.output_files && (
        <div className="space-y-3">
          <h4 className="text-sm font-medium text-gray-700">Download your report:</h4>
          <div className="flex flex-wrap gap-3">
            {currentReport.output_files.map((file) => (
              <a
                key={file.format}
                href={file.download_url || '#'}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors"
              >
                <svg
                  className="w-5 h-5 mr-2"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"
                  />
                </svg>
                Download {file.format.toUpperCase()}
              </a>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
