import { useReportStore } from '../../stores/reportStore'
import type { DetailLevel, OutputFormat } from '../../types/report'

export default function ReportConfigForm() {
  const { config, updateConfig } = useReportStore()

  const detailLevels: { value: DetailLevel; label: string; description: string }[] = [
    {
      value: 'executive',
      label: 'Executive',
      description: '1-2 pages, high-level summary',
    },
    {
      value: 'standard',
      label: 'Standard',
      description: '3-5 pages, balanced detail',
    },
    {
      value: 'comprehensive',
      label: 'Comprehensive',
      description: '5-10 pages, in-depth analysis',
    },
  ]

  const outputFormats: { value: OutputFormat; label: string }[] = [
    { value: 'pdf', label: 'PDF' },
    { value: 'docx', label: 'Word (DOCX)' },
    { value: 'pptx', label: 'PowerPoint (PPTX)' },
  ]

  const toggleFormat = (format: OutputFormat) => {
    const current = config.outputFormats
    if (current.includes(format)) {
      if (current.length > 1) {
        updateConfig({ outputFormats: current.filter((f) => f !== format) })
      }
    } else {
      updateConfig({ outputFormats: [...current, format] })
    }
  }

  return (
    <div className="space-y-6">
      {/* Title */}
      <div>
        <label htmlFor="title" className="block text-sm font-medium text-gray-700">
          Report Title (optional)
        </label>
        <input
          id="title"
          type="text"
          value={config.title}
          onChange={(e) => updateConfig({ title: e.target.value })}
          className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-lg shadow-sm focus:ring-primary-500 focus:border-primary-500"
          placeholder="Auto-generated if left blank"
        />
      </div>

      {/* Custom Instructions */}
      <div>
        <label htmlFor="instructions" className="block text-sm font-medium text-gray-700">
          Custom Instructions (optional)
        </label>
        <textarea
          id="instructions"
          rows={3}
          value={config.customInstructions}
          onChange={(e) => updateConfig({ customInstructions: e.target.value })}
          className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-lg shadow-sm focus:ring-primary-500 focus:border-primary-500"
          placeholder="Any specific focus areas or requirements..."
        />
      </div>

      {/* Detail Level */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Detail Level
        </label>
        <div className="grid grid-cols-3 gap-3">
          {detailLevels.map((level) => (
            <button
              key={level.value}
              type="button"
              onClick={() => updateConfig({ detailLevel: level.value })}
              className={`p-3 border rounded-lg text-left transition-colors ${
                config.detailLevel === level.value
                  ? 'border-primary-500 bg-primary-50 ring-1 ring-primary-500'
                  : 'border-gray-300 hover:border-gray-400'
              }`}
            >
              <p className="font-medium text-sm text-gray-900">{level.label}</p>
              <p className="text-xs text-gray-500 mt-1">{level.description}</p>
            </button>
          ))}
        </div>
      </div>

      {/* Output Formats */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Output Formats
        </label>
        <div className="flex flex-wrap gap-2">
          {outputFormats.map((format) => (
            <button
              key={format.value}
              type="button"
              onClick={() => toggleFormat(format.value)}
              className={`px-4 py-2 border rounded-lg text-sm font-medium transition-colors ${
                config.outputFormats.includes(format.value)
                  ? 'border-primary-500 bg-primary-50 text-primary-700'
                  : 'border-gray-300 text-gray-700 hover:border-gray-400'
              }`}
            >
              {format.label}
            </button>
          ))}
        </div>
      </div>

      {/* Slide Count (only if PPTX selected) */}
      {config.outputFormats.includes('pptx') && (
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Slide Count Range
          </label>
          <div className="flex items-center space-x-3">
            <input
              type="number"
              min={5}
              max={30}
              value={config.slideCountMin}
              onChange={(e) =>
                updateConfig({ slideCountMin: parseInt(e.target.value) || 10 })
              }
              className="w-20 px-3 py-2 border border-gray-300 rounded-lg shadow-sm focus:ring-primary-500 focus:border-primary-500"
            />
            <span className="text-gray-500">to</span>
            <input
              type="number"
              min={5}
              max={30}
              value={config.slideCountMax}
              onChange={(e) =>
                updateConfig({ slideCountMax: parseInt(e.target.value) || 15 })
              }
              className="w-20 px-3 py-2 border border-gray-300 rounded-lg shadow-sm focus:ring-primary-500 focus:border-primary-500"
            />
            <span className="text-gray-500">slides</span>
          </div>
        </div>
      )}
    </div>
  )
}
