import { useReportStore } from '../../stores/reportStore'

const FILE_ICONS: Record<string, string> = {
  pdf: 'M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z',
  docx: 'M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z',
  xlsx: 'M3 10h18M3 14h18m-9-4v8m-7 0h14a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z',
  pptx: 'M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z',
}

const FILE_COLORS: Record<string, string> = {
  pdf: 'text-red-500',
  docx: 'text-blue-500',
  xlsx: 'text-green-500',
  pptx: 'text-orange-500',
}

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

export default function FileList() {
  const { selectedFiles, removeFile } = useReportStore()

  if (selectedFiles.length === 0) {
    return null
  }

  return (
    <div className="space-y-2">
      <h3 className="text-sm font-medium text-gray-700">
        Selected files ({selectedFiles.length})
      </h3>

      <ul className="divide-y divide-gray-200 border border-gray-200 rounded-lg">
        {selectedFiles.map((file) => (
          <li
            key={file.id}
            className="flex items-center justify-between px-4 py-3 hover:bg-gray-50"
          >
            <div className="flex items-center space-x-3 min-w-0">
              <svg
                className={`w-5 h-5 flex-shrink-0 ${FILE_COLORS[file.type] || 'text-gray-400'}`}
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={1.5}
                  d={FILE_ICONS[file.type] || FILE_ICONS.pdf}
                />
              </svg>

              <div className="min-w-0">
                <p className="text-sm font-medium text-gray-900 truncate">
                  {file.name}
                </p>
                <p className="text-xs text-gray-500">
                  {file.type.toUpperCase()} • {formatFileSize(file.size)}
                  {file.source === 'google_drive' && ' • Google Drive'}
                </p>
              </div>
            </div>

            <button
              onClick={() => removeFile(file.id)}
              className="text-gray-400 hover:text-red-500 p-1 rounded transition-colors"
              title="Remove file"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={1.5}
                  d="M6 18L18 6M6 6l12 12"
                />
              </svg>
            </button>
          </li>
        ))}
      </ul>
    </div>
  )
}
