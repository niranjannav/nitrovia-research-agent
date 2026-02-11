import { useEffect, useState } from 'react'
import { Panel, PanelGroup, PanelResizeHandle } from 'react-resizable-panels'
import { useReportStore } from '../../stores/reportStore'
import ReportPreview from './ReportPreview'
import SlideDeckPreview from './SlideDeckPreview'
import SectionEditor from './SectionEditor'

type ViewMode = 'report' | 'slides'

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
    currentReport,
  } = useReportStore()

  const [viewMode, setViewMode] = useState<ViewMode>('report')
  const [drawerOpen, setDrawerOpen] = useState(false)

  useEffect(() => {
    if (reportId) {
      loadGeneratedContent(reportId)
    }
  }, [reportId, loadGeneratedContent])

  if (isLoading && !generatedContent) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-gray-400">Loading report content...</div>
      </div>
    )
  }

  if (error && !generatedContent) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-red-500">{error}</div>
      </div>
    )
  }

  if (!generatedContent?.report) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-gray-400">No report content available</div>
      </div>
    )
  }

  const report = generatedContent.report
  const presentation = generatedContent.presentation
  const sourceFiles = currentReport?.source_files || []

  return (
    <div className="h-full flex flex-col bg-gray-50">
      {/* Global Action Header */}
      <div className="flex items-center justify-between px-4 py-2 bg-white border-b border-gray-100 shadow-soft flex-shrink-0">
        <div className="flex items-center gap-3">
          {/* Reference drawer toggle */}
          <button
            onClick={() => setDrawerOpen(!drawerOpen)}
            className={`flex items-center gap-1.5 px-2.5 py-1.5 text-sm font-medium rounded-lg transition-colors ${
              drawerOpen
                ? 'bg-primary-50 text-primary-700'
                : 'text-gray-500 hover:text-gray-700 hover:bg-gray-50'
            }`}
            title="Source files"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" />
            </svg>
            Sources
            {sourceFiles.length > 0 && (
              <span className="ml-1 px-1.5 py-0.5 bg-gray-100 text-gray-500 text-xs rounded-full">
                {sourceFiles.length}
              </span>
            )}
          </button>

          <div className="h-5 w-px bg-gray-200" />

          {/* View toggle */}
          <div className="flex items-center bg-gray-100 rounded-lg p-0.5">
            <button
              onClick={() => setViewMode('report')}
              className={`px-3 py-1 text-sm font-medium rounded-md transition-colors ${
                viewMode === 'report'
                  ? 'bg-white text-primary-700 shadow-sm'
                  : 'text-gray-500 hover:text-gray-700'
              }`}
            >
              Report
            </button>
            <button
              onClick={() => setViewMode('slides')}
              disabled={!presentation}
              className={`px-3 py-1 text-sm font-medium rounded-md transition-colors ${
                viewMode === 'slides'
                  ? 'bg-white text-primary-700 shadow-sm'
                  : 'text-gray-500 hover:text-gray-700'
              } ${!presentation ? 'opacity-40 cursor-not-allowed' : ''}`}
            >
              Slide Deck
            </button>
          </div>

          <div className="h-5 w-px bg-gray-200" />

          <h2 className="text-sm font-medium text-gray-700 truncate max-w-xs">
            {report.title}
          </h2>
        </div>

        <div className="flex items-center gap-2">
          {downloadUrls.map((file) => (
            <button
              key={file.format}
              onClick={() => onDownload?.(file.format as 'pdf' | 'docx' | 'pptx')}
              className={`inline-flex items-center gap-1.5 px-3.5 py-1.5 text-sm font-medium rounded-lg transition-colors ${
                file.format === 'pdf'
                  ? 'bg-primary-600 text-white hover:bg-primary-700 shadow-soft'
                  : 'text-gray-600 bg-white border border-gray-200 hover:bg-gray-50'
              }`}
            >
              <DownloadIcon />
              {file.format.toUpperCase()}
            </button>
          ))}
        </div>
      </div>

      {/* Split-pane layout */}
      <div className="flex-1 overflow-hidden">
        <PanelGroup direction="horizontal">
          {/* Reference Drawer (Left) */}
          {drawerOpen && (
            <>
              <Panel defaultSize={14} minSize={12} maxSize={22}>
                <div className="h-full bg-white border-r border-gray-100 overflow-auto">
                  <div className="px-3 py-3">
                    <div className="flex items-center justify-between mb-3">
                      <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider">Sources</h3>
                      <button
                        onClick={() => setDrawerOpen(false)}
                        className="p-0.5 text-gray-400 hover:text-gray-600 rounded"
                      >
                        <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                        </svg>
                      </button>
                    </div>
                    <div className="space-y-1.5">
                      {sourceFiles.length > 0 ? (
                        sourceFiles.map((file, idx) => (
                          <div
                            key={file.id || idx}
                            className="flex items-center gap-2 px-2 py-2 rounded-lg bg-gray-50 hover:bg-gray-100 transition-colors"
                          >
                            <FileTypeIcon type="pdf" />
                            <span className="text-xs text-gray-600 truncate">
                              Source file {idx + 1}
                            </span>
                          </div>
                        ))
                      ) : (
                        <div className="text-xs text-gray-400 py-4 text-center">
                          No source files
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              </Panel>
              <PanelResizeHandle className="w-px bg-gray-100 hover:bg-primary-300 transition-colors" />
            </>
          )}

          {/* Main Document Canvas (Center) */}
          <Panel defaultSize={drawerOpen ? 54 : 64} minSize={40}>
            <div className="h-full overflow-auto bg-gray-50 p-6">
              {viewMode === 'report' ? (
                <div className="max-w-3xl mx-auto">
                  <ReportPreview
                    report={report}
                    selectedPath={selectedSectionPath}
                    onSelectSection={selectSection}
                  />
                </div>
              ) : (
                presentation && (
                  <SlideDeckPreview
                    presentation={presentation}
                    selectedPath={selectedSectionPath}
                    onSelectSlide={(path) => selectSection(path)}
                  />
                )
              )}
            </div>
          </Panel>

          <PanelResizeHandle className="w-px bg-gray-100 hover:bg-primary-300 transition-colors" />

          {/* Agentic Chat Sidebar (Right) */}
          <Panel defaultSize={drawerOpen ? 32 : 36} minSize={28}>
            <div className="h-full overflow-hidden bg-white border-l border-gray-100">
              <SectionEditor
                reportId={reportId}
                selectedPath={selectedSectionPath}
                report={report}
              />
            </div>
          </Panel>
        </PanelGroup>
      </div>
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

function FileTypeIcon({ type }: { type: string }) {
  const colors: Record<string, string> = {
    pdf: 'text-red-400',
    docx: 'text-blue-400',
    xlsx: 'text-green-400',
    pptx: 'text-orange-400',
  }
  return (
    <svg
      className={`w-4 h-4 flex-shrink-0 ${colors[type] || 'text-gray-400'}`}
      fill="none"
      stroke="currentColor"
      viewBox="0 0 24 24"
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={1.5}
        d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z"
      />
    </svg>
  )
}
