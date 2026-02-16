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
  reportId: _reportId,
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
      {/* Header */}
      <div className="px-4 py-3 border-b border-gray-200">
        <h3 className="font-semibold text-gray-900 flex items-center gap-2">
          <EditIcon />
          Edit Section
        </h3>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-auto p-4 space-y-4">
        {selectedPath ? (
          <>
            {/* Selected section info */}
            <div className="bg-gray-50 rounded-lg p-3">
              <div className="text-xs font-medium text-gray-500 mb-1">
                Selected
              </div>
              <div className="font-medium text-gray-900">
                {selectedSectionInfo?.title || selectedPath}
              </div>
              {selectedSectionInfo?.preview && (
                <p className="text-sm text-gray-600 mt-1 line-clamp-3">
                  {selectedSectionInfo.preview}
                </p>
              )}
            </div>

            {/* Instructions input */}
            <div className="space-y-2">
              <label className="block text-sm font-medium text-gray-700">
                How should this section change?
              </label>
              <textarea
                value={instructions}
                onChange={(e) => setInstructions(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="e.g., Make this more concise, add statistics, change the tone to be more formal..."
                rows={4}
                className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 resize-none"
                disabled={isEditing}
              />
              <p className="text-xs text-gray-500">
                Press Ctrl+Enter to apply
              </p>
            </div>

            {/* Error message */}
            {error && (
              <div className="bg-red-50 border border-red-200 text-red-700 px-3 py-2 rounded-lg text-sm">
                {error}
              </div>
            )}

            {/* Apply button */}
            <button
              onClick={handleApply}
              disabled={isEditing || !instructions.trim()}
              className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-primary-600 text-white rounded-lg font-medium hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {isEditing ? (
                <>
                  <Spinner />
                  Applying...
                </>
              ) : (
                <>
                  <SparkleIcon />
                  Apply Changes
                </>
              )}
            </button>
          </>
        ) : (
          <div className="text-center py-8 text-gray-500">
            <ClickIcon className="w-12 h-12 mx-auto mb-3 text-gray-300" />
            <p className="text-sm">
              Click a section on the left to select it for editing
            </p>
          </div>
        )}

        {/* Divider */}
        {editHistory.length > 0 && <hr className="border-gray-200" />}

        {/* Edit History */}
        {editHistory.length > 0 && <EditHistory />}
      </div>
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

function EditIcon() {
  return (
    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"
      />
    </svg>
  )
}

function SparkleIcon() {
  return (
    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
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

function Spinner() {
  return (
    <svg className="animate-spin w-5 h-5" fill="none" viewBox="0 0 24 24">
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
