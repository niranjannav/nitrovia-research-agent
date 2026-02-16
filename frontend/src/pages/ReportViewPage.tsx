import { useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useReportStore } from '../stores/reportStore'
import ReportEditor from '../components/reports/ReportEditor'

export default function ReportViewPage() {
  const { reportId } = useParams<{ reportId: string }>()
  const navigate = useNavigate()
  const {
    currentReport,
    fetchReport,
    loadGeneratedContent,
    clearEditorState,
    isLoading,
    error,
  } = useReportStore()

  useEffect(() => {
    if (reportId) {
      fetchReport(reportId)
      loadGeneratedContent(reportId)
    }

    return () => {
      clearEditorState()
    }
  }, [reportId, fetchReport, loadGeneratedContent, clearEditorState])

  const handleDownload = (format: 'pdf' | 'docx' | 'pptx') => {
    const file = currentReport?.output_files?.find((f) => f.format === format)
    if (file?.download_url) {
      window.open(file.download_url, '_blank')
    }
  }

  const handleNewReport = () => {
    navigate('/reports/new')
  }

  if (isLoading && !currentReport) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
      </div>
    )
  }

  if (error && !currentReport) {
    return (
      <div className="max-w-3xl mx-auto">
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg">
          {error}
        </div>
      </div>
    )
  }

  if (!reportId) {
    return (
      <div className="max-w-3xl mx-auto">
        <div className="text-gray-500">Report not found</div>
      </div>
    )
  }

  return (
    <div className="max-w-7xl mx-auto">
      {/* Header */}
      <div className="mb-8 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">
            {currentReport?.title || 'View Report'}
          </h1>
          <p className="text-gray-600 mt-1">
            Click any section to select it, then enter your edit instructions
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={() => navigate('/')}
            className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
          >
            Back to Dashboard
          </button>
          <button
            onClick={handleNewReport}
            className="px-4 py-2 text-sm font-medium text-white bg-primary-600 rounded-lg hover:bg-primary-700 transition-colors"
          >
            New Report
          </button>
        </div>
      </div>

      {/* Report Editor */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-100">
        <ReportEditor
          reportId={reportId}
          onDownload={handleDownload}
          downloadUrls={
            currentReport?.output_files?.map((f) => ({
              format: f.format,
              download_url: f.download_url || '',
            })) || []
          }
        />
      </div>
    </div>
  )
}
