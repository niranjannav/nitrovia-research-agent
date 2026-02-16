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
        <div className="bg-white rounded-lg border border-gray-200 p-4">
          <h3 className="text-sm font-medium text-gray-500 mb-2">Sources</h3>
          <ul className="text-sm text-gray-600 space-y-1">
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
  return (
    <div
      onClick={() => onSelect(isSelected ? null : path)}
      className={`
        bg-white rounded-lg border-2 p-4 cursor-pointer transition-all
        ${isSelected
          ? 'border-primary-500 ring-2 ring-primary-100'
          : 'border-gray-200 hover:border-gray-300 hover:shadow-sm'
        }
      `}
    >
      <div className="flex items-center justify-between mb-2">
        <h3 className="font-semibold text-gray-900">{title}</h3>
        {isSelected && (
          <span className="text-xs font-medium text-primary-600 bg-primary-50 px-2 py-0.5 rounded">
            Selected
          </span>
        )}
      </div>
      <p className="text-sm text-gray-700 whitespace-pre-wrap line-clamp-6">
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
  return (
    <div
      onClick={() => onSelect(isSelected ? null : path)}
      className={`
        bg-white rounded-lg border-2 p-4 cursor-pointer transition-all
        ${isSelected
          ? 'border-primary-500 ring-2 ring-primary-100'
          : 'border-gray-200 hover:border-gray-300 hover:shadow-sm'
        }
      `}
    >
      <div className="flex items-center justify-between mb-2">
        <h3 className="font-semibold text-gray-900">{title}</h3>
        {isSelected && (
          <span className="text-xs font-medium text-primary-600 bg-primary-50 px-2 py-0.5 rounded">
            Selected
          </span>
        )}
      </div>
      <ul className="text-sm text-gray-700 space-y-1">
        {items.slice(0, 5).map((item, idx) => (
          <li key={idx} className="flex items-start gap-2">
            <span className="text-primary-500 mt-1">•</span>
            <span className="line-clamp-2">{item}</span>
          </li>
        ))}
        {items.length > 5 && (
          <li className="text-gray-500 italic">
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

  return (
    <div className="space-y-3">
      <div
        onClick={() => onSelectSection(isSelected ? null : basePath)}
        className={`
          bg-white rounded-lg border-2 p-4 cursor-pointer transition-all
          ${isSelected
            ? 'border-primary-500 ring-2 ring-primary-100'
            : 'border-gray-200 hover:border-gray-300 hover:shadow-sm'
          }
        `}
      >
        <div className="flex items-center justify-between mb-2">
          <h3 className="font-semibold text-gray-900">{section.title}</h3>
          {isSelected && (
            <span className="text-xs font-medium text-primary-600 bg-primary-50 px-2 py-0.5 rounded">
              Selected
            </span>
          )}
        </div>
        <p className="text-sm text-gray-700 whitespace-pre-wrap line-clamp-6">
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
