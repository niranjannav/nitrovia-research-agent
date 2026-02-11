import { useState } from 'react'
import type { GeneratedReport, ReportSection } from '../../types/report'

interface ReportPreviewProps {
  report: GeneratedReport
  selectedPath: string | null
  onSelectSection: (path: string | null) => void
}

export default function ReportPreview({
  report,
  selectedPath,
  onSelectSection,
}: ReportPreviewProps) {
  return (
    <div className="space-y-4">
      {/* Executive Summary */}
      <SectionCard
        title="Executive Summary"
        content={report.executive_summary}
        path="executive_summary"
        isSelected={selectedPath === 'executive_summary'}
        onSelect={onSelectSection}
      />

      {/* Main Sections */}
      {report.sections.map((section, idx) => (
        <SectionWithSubsections
          key={idx}
          section={section}
          basePath={`sections.${idx}`}
          selectedPath={selectedPath}
          onSelectSection={onSelectSection}
        />
      ))}

      {/* Key Findings */}
      <ListSectionCard
        title="Key Findings"
        items={report.key_findings}
        path="key_findings"
        isSelected={selectedPath === 'key_findings'}
        onSelect={onSelectSection}
      />

      {/* Recommendations */}
      <ListSectionCard
        title="Recommendations"
        items={report.recommendations}
        path="recommendations"
        isSelected={selectedPath === 'recommendations'}
        onSelect={onSelectSection}
      />

      {/* Sources */}
      {report.sources.length > 0 && (
        <div className="bg-white rounded-xl border border-gray-100 p-5 shadow-soft">
          <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-3">Sources</h3>
          <ul className="text-sm text-gray-500 space-y-1">
            {report.sources.map((source, idx) => (
              <li key={idx}>{source}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}

interface SectionCardProps {
  title: string
  content: string
  path: string
  isSelected: boolean
  onSelect: (path: string | null) => void
}

function SectionCard({
  title,
  content,
  path,
  isSelected,
  onSelect,
}: SectionCardProps) {
  const [showToolbar, setShowToolbar] = useState(false)

  return (
    <div
      onClick={() => onSelect(isSelected ? null : path)}
      onMouseEnter={() => setShowToolbar(true)}
      onMouseLeave={() => setShowToolbar(false)}
      className={`
        relative bg-white rounded-xl p-5 cursor-pointer transition-all
        ${isSelected
          ? 'ring-2 ring-primary-500 ring-offset-1 shadow-soft-md'
          : 'border border-gray-100 hover:border-gray-200 hover:shadow-soft shadow-soft'
        }
      `}
    >
      {/* Floating toolbar - Highlight-to-Action pattern */}
      {showToolbar && !isSelected && (
        <div className="floating-toolbar-enter absolute -top-3 right-3 flex items-center gap-1 bg-white/90 backdrop-blur-sm border border-gray-200 rounded-lg px-2 py-1 shadow-soft-md z-10">
          <span className="text-xs text-gray-400">Click to edit</span>
        </div>
      )}

      <div className="flex items-center justify-between mb-2">
        <h3 className="font-semibold text-gray-800 text-sm">{title}</h3>
        {isSelected && (
          <span className="text-xs font-medium text-primary-600 bg-primary-50 px-2 py-0.5 rounded-md">
            Editing
          </span>
        )}
      </div>
      <p className="text-sm text-gray-600 whitespace-pre-wrap line-clamp-6 leading-relaxed">
        {content}
      </p>
    </div>
  )
}

interface ListSectionCardProps {
  title: string
  items: string[]
  path: string
  isSelected: boolean
  onSelect: (path: string | null) => void
}

function ListSectionCard({
  title,
  items,
  path,
  isSelected,
  onSelect,
}: ListSectionCardProps) {
  const [showToolbar, setShowToolbar] = useState(false)

  return (
    <div
      onClick={() => onSelect(isSelected ? null : path)}
      onMouseEnter={() => setShowToolbar(true)}
      onMouseLeave={() => setShowToolbar(false)}
      className={`
        relative bg-white rounded-xl p-5 cursor-pointer transition-all
        ${isSelected
          ? 'ring-2 ring-primary-500 ring-offset-1 shadow-soft-md'
          : 'border border-gray-100 hover:border-gray-200 hover:shadow-soft shadow-soft'
        }
      `}
    >
      {showToolbar && !isSelected && (
        <div className="floating-toolbar-enter absolute -top-3 right-3 flex items-center gap-1 bg-white/90 backdrop-blur-sm border border-gray-200 rounded-lg px-2 py-1 shadow-soft-md z-10">
          <span className="text-xs text-gray-400">Click to edit</span>
        </div>
      )}

      <div className="flex items-center justify-between mb-2">
        <h3 className="font-semibold text-gray-800 text-sm">{title}</h3>
        {isSelected && (
          <span className="text-xs font-medium text-primary-600 bg-primary-50 px-2 py-0.5 rounded-md">
            Editing
          </span>
        )}
      </div>
      <ul className="text-sm text-gray-600 space-y-1">
        {items.slice(0, 5).map((item, idx) => (
          <li key={idx} className="flex items-start gap-2">
            <span className="text-primary-400 mt-0.5">•</span>
            <span className="line-clamp-2 leading-relaxed">{item}</span>
          </li>
        ))}
        {items.length > 5 && (
          <li className="text-gray-400 italic pl-4">
            +{items.length - 5} more items
          </li>
        )}
      </ul>
    </div>
  )
}

interface SectionWithSubsectionsProps {
  section: ReportSection
  basePath: string
  selectedPath: string | null
  onSelectSection: (path: string | null) => void
}

function SectionWithSubsections({
  section,
  basePath,
  selectedPath,
  onSelectSection,
}: SectionWithSubsectionsProps) {
  const isSelected = selectedPath === basePath
  const [showToolbar, setShowToolbar] = useState(false)

  return (
    <div className="space-y-3">
      <div
        onClick={() => onSelectSection(isSelected ? null : basePath)}
        onMouseEnter={() => setShowToolbar(true)}
        onMouseLeave={() => setShowToolbar(false)}
        className={`
          relative bg-white rounded-xl p-5 cursor-pointer transition-all
          ${isSelected
            ? 'ring-2 ring-primary-500 ring-offset-1 shadow-soft-md'
            : 'border border-gray-100 hover:border-gray-200 hover:shadow-soft shadow-soft'
          }
        `}
      >
        {showToolbar && !isSelected && (
          <div className="floating-toolbar-enter absolute -top-3 right-3 flex items-center gap-1 bg-white/90 backdrop-blur-sm border border-gray-200 rounded-lg px-2 py-1 shadow-soft-md z-10">
            <span className="text-xs text-gray-400">Click to edit</span>
          </div>
        )}

        <div className="flex items-center justify-between mb-2">
          <h3 className="font-semibold text-gray-800 text-sm">{section.title}</h3>
          {isSelected && (
            <span className="text-xs font-medium text-primary-600 bg-primary-50 px-2 py-0.5 rounded-md">
              Editing
            </span>
          )}
        </div>
        <p className="text-sm text-gray-600 whitespace-pre-wrap line-clamp-6 leading-relaxed">
          {section.content}
        </p>
      </div>

      {/* Subsections */}
      {section.subsections.length > 0 && (
        <div className="ml-4 space-y-3 border-l-2 border-gray-100 pl-4">
          {section.subsections.map((subsection, subIdx) => (
            <SectionWithSubsections
              key={subIdx}
              section={subsection}
              basePath={`${basePath}.subsections.${subIdx}`}
              selectedPath={selectedPath}
              onSelectSection={onSelectSection}
            />
          ))}
        </div>
      )}
    </div>
  )
}
