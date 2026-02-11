import { useState } from 'react'
import { useReportStore } from '../../stores/reportStore'
import EditHistory from './EditHistory'
import type { GeneratedReport } from '../../types/report'

interface SectionEditorProps {
  reportId: string
  selectedPath: string | null
  report: GeneratedReport
}

export default function SectionEditor({
  reportId,
  selectedPath,
  report,
}: SectionEditorProps) {
  const { editSection, isEditing, error, editHistory } = useReportStore()
  const [instructions, setInstructions] = useState('')

  const selectedSectionInfo = selectedPath
    ? getSectionInfo(report, selectedPath)
    : null

  const handleApply = async () => {
    if (!instructions.trim()) return

    try {
      await editSection(instructions)
      setInstructions('')
    } catch {
      // Error handled by store
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
      handleApply()
    }
  }

  return (
    <div className="h-full flex flex-col">
      {/* Sidebar header */}
      <div className="px-4 py-3 border-b border-gray-100 flex-shrink-0">
        <div className="flex items-center gap-2">
          <div className={`w-2 h-2 rounded-full ${selectedPath ? 'bg-primary-500 animate-pulse-ring' : 'bg-gray-300'}`} />
          <h3 className="text-sm font-semibold text-gray-800">
            AI Assistant
          </h3>
        </div>
      </div>

      {/* Context Badge */}
      {selectedPath && selectedSectionInfo && (
        <div className="px-4 py-2.5 bg-primary-50/60 border-b border-primary-100/50 flex-shrink-0">
          <div className="flex items-center gap-2">
            <svg className="w-3.5 h-3.5 text-primary-500 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <span className="text-xs font-medium text-primary-700 truncate">
              Editing: {selectedSectionInfo.title}
            </span>
          </div>
        </div>
      )}

      {/* Chat content area */}
      <div className="flex-1 overflow-auto px-4 py-4 space-y-4">
        {selectedPath ? (
          <>
            {/* AI suggestion preview */}
            {isEditing && (
              <div className="flex gap-2.5">
                <div className="w-6 h-6 rounded-full bg-primary-100 flex items-center justify-center flex-shrink-0 mt-0.5">
                  <SparkleIcon className="w-3.5 h-3.5 text-primary-600" />
                </div>
                <div className="flex-1 bg-gray-50 rounded-xl px-3.5 py-3 text-sm text-gray-600">
                  <div className="flex items-center gap-2">
                    <Spinner className="w-3.5 h-3.5" />
                    <span>Working on your changes...</span>
                  </div>
                </div>
              </div>
            )}

            {/* Section preview */}
            <div className="bg-gray-50 rounded-xl p-3.5">
              <div className="font-medium text-gray-800 text-sm">
                {selectedSectionInfo?.title || selectedPath}
              </div>
              {selectedSectionInfo?.preview && (
                <p className="text-xs text-gray-500 mt-1.5 line-clamp-3 leading-relaxed">
                  {selectedSectionInfo.preview}
                </p>
              )}
            </div>

            {/* Error message */}
            {error && (
              <div className="bg-red-50 border border-red-100 text-red-600 px-3.5 py-2.5 rounded-xl text-sm">
                {error}
              </div>
            )}
          </>
        ) : (
          <div className="flex flex-col items-center justify-center py-12 text-center">
            <div className="w-14 h-14 rounded-2xl bg-gray-50 flex items-center justify-center mb-4">
              <ClickIcon className="w-7 h-7 text-gray-300" />
            </div>
            <p className="text-sm text-gray-400 max-w-[200px] leading-relaxed">
              Select a section or slide to start editing with AI
            </p>
          </div>
        )}

        {/* Edit History */}
        {editHistory.length > 0 && (
          <>
            <hr className="border-gray-100" />
            <EditHistory />
          </>
        )}
      </div>

      {/* Command Bar input */}
      {selectedPath && (
        <div className="px-4 py-3 border-t border-gray-100 bg-white flex-shrink-0">
          <div className="relative">
            <textarea
              value={instructions}
              onChange={(e) => setInstructions(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="How should I change this section?"
              rows={2}
              className="w-full px-3.5 py-2.5 pr-12 text-sm border border-gray-200 rounded-xl focus:ring-2 focus:ring-primary-500/20 focus:border-primary-400 resize-none bg-gray-50 placeholder-gray-400 transition-colors"
              disabled={isEditing}
            />
            <button
              onClick={handleApply}
              disabled={isEditing || !instructions.trim()}
              className="absolute bottom-2.5 right-2.5 p-1.5 rounded-lg bg-primary-600 text-white disabled:opacity-30 disabled:cursor-not-allowed hover:bg-primary-700 transition-colors"
              title="Apply changes (Ctrl+Enter)"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
              </svg>
            </button>
          </div>
          <p className="text-xs text-gray-400 mt-1.5 px-1">
            Press ⌘+Enter to apply
          </p>
        </div>
      )}
    </div>
  )
}

function getSectionInfo(
  report: GeneratedReport,
  path: string
): { title: string; preview: string } | null {
  const parts = path.split('.')

  if (parts[0] === 'executive_summary') {
    return {
      title: 'Executive Summary',
      preview: report.executive_summary.slice(0, 150),
    }
  }

  if (parts[0] === 'key_findings') {
    return {
      title: 'Key Findings',
      preview: report.key_findings.slice(0, 3).join(' • '),
    }
  }

  if (parts[0] === 'recommendations') {
    return {
      title: 'Recommendations',
      preview: report.recommendations.slice(0, 3).join(' • '),
    }
  }

  if (parts[0] === 'slides') {
    const slideIdx = parseInt(parts[1])
    return {
      title: `Slide ${slideIdx + 1}`,
      preview: '',
    }
  }

  if (parts[0] === 'sections') {
    try {
      let current = report.sections[parseInt(parts[1])]
      for (let i = 2; i < parts.length; i += 2) {
        if (parts[i] === 'subsections') {
          current = current.subsections[parseInt(parts[i + 1])]
        }
      }
      return {
        title: current.title,
        preview: current.content.slice(0, 150),
      }
    } catch {
      return null
    }
  }

  return null
}

function SparkleIcon({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M5 3v4M3 5h4M6 17v4m-2-2h4m5-16l2.286 6.857L21 12l-5.714 2.143L13 21l-2.286-6.857L5 12l5.714-2.143L13 3z"
      />
    </svg>
  )
}

function ClickIcon({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={1.5}
        d="M15 15l-2 5L9 9l11 4-5 2zm0 0l5 5M7.188 2.239l.777 2.897M5.136 7.965l-2.898-.777M13.95 4.05l-2.122 2.122m-5.657 5.656l-2.12 2.122"
      />
    </svg>
  )
}

function Spinner({ className }: { className?: string }) {
  return (
    <svg className={`animate-spin ${className}`} fill="none" viewBox="0 0 24 24">
      <circle
        className="opacity-25"
        cx="12"
        cy="12"
        r="10"
        stroke="currentColor"
        strokeWidth="4"
      />
      <path
        className="opacity-75"
        fill="currentColor"
        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
      />
    </svg>
  )
}
