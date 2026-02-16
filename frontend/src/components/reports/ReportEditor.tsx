import { useEffect } from 'react'
import { Panel, PanelGroup, PanelResizeHandle } from 'react-resizable-panels'
import { useReportStore } from '../../stores/reportStore'
import ReportPreview from './ReportPreview'
import SectionEditor from './SectionEditor'

interface ReportEditorProps {
  reportId: string
  onDownload?: (format: 'pdf' | 'docx' | 'pptx') => void
  downloadUrls?: { format: string; download_url: string }[]
}

export default function ReportEditor({
  reportId,
  onDownload,
  downloadUrls = [],
}: ReportEditorProps) {
  const {
    generatedContent,
    selectedSectionPath,
    loadGeneratedContent,
    selectSection,
    isLoading,
    error,
  } = useReportStore()

  useEffect(() => {
    if (reportId) {
      loadGeneratedContent(reportId)
    }
  }, [reportId, loadGeneratedContent])

  if (isLoading && !generatedContent) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="text-gray-500">Loading report content...</div>
      </div>
    )
  }

  if (error && !generatedContent) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="text-red-500">{error}</div>
      </div>
    )
  }

  if (!generatedContent?.report) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="text-gray-500">No report content available</div>
      </div>
    )
  }

  const report = generatedContent.report

  return (
    <div className="h-[calc(100vh-200px)] flex flex-col">
      {/* Header with title and download buttons */}
      <div className="flex items-center justify-between px-4 py-3 bg-white border-b border-gray-200">
        <h2 className="text-xl font-semibold text-gray-900 truncate">
          {report.title}
        </h2>
        <div className="flex items-center gap-2">
          {downloadUrls.map((file) => (
            <button
              key={file.format}
              onClick={() => onDownload?.(file.format as 'pdf' | 'docx' | 'pptx')}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 transition-colors"
            >
              <DownloadIcon />
              {file.format.toUpperCase()}
            </button>
          ))}
        </div>
      </div>

      {/* Split pane layout */}
      <PanelGroup direction="horizontal" className="flex-1">
        <Panel defaultSize={60} minSize={40}>
          <div className="h-full overflow-auto bg-gray-50 p-4">
            <ReportPreview
              report={report}
              selectedPath={selectedSectionPath}
              onSelectSection={selectSection}
            />
          </div>
        </Panel>

        <PanelResizeHandle className="w-1.5 bg-gray-200 hover:bg-primary-300 transition-colors cursor-col-resize" />

        <Panel defaultSize={40} minSize={30}>
          <div className="h-full overflow-auto bg-white border-l border-gray-200">
            <SectionEditor
              reportId={reportId}
              selectedPath={selectedSectionPath}
              report={report}
            />
          </div>
        </Panel>
      </PanelGroup>
    </div>
  )
}

function DownloadIcon() {
  return (
    <svg
      className="w-4 h-4"
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
  )
}
