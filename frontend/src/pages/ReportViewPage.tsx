import { useEffect } from 'react'
import { useParams } from 'react-router-dom'
import { useReportStore } from '../stores/reportStore'
import ReportEditor from '../components/reports/ReportEditor'

export default function ReportViewPage() {
  const { reportId } = useParams<{ reportId: string }>()
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

  if (isLoading && !currentReport) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
      </div>
    )
  }

  if (error && !currentReport) {
    return (
      <div className="flex items-center justify-center h-full px-8">
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-xl max-w-md">
          {error}
        </div>
      </div>
    )
  }

  if (!reportId) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-gray-400">Report not found</div>
      </div>
    )
  }

  return (
    <div className="h-full">
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
  )
}
