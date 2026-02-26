import type { ParsedExcelData } from '../../utils/excelParser'

interface DataPreviewProps {
  data: ParsedExcelData
  fileName: string
}

export default function DataPreview({ data, fileName }: DataPreviewProps) {
  const displayRows = data.rows.slice(0, 5)

  return (
    <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
      <div className="px-4 py-3 border-b border-gray-100 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <svg
            className="w-5 h-5 text-green-500"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={1.5}
              d="M3 10h18M3 14h18m-9-4v8m-7 0h14a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z"
            />
          </svg>
          <div>
            <h3 className="text-sm font-semibold text-gray-800">{fileName}</h3>
            <p className="text-xs text-gray-500">
              {data.rows.length} rows × {data.headers.length} columns
            </p>
          </div>
        </div>
        <span className="text-xs bg-green-50 text-green-700 px-2 py-1 rounded-full font-medium">
          Data loaded
        </span>
      </div>
      <div className="overflow-x-auto max-h-48">
        <table className="w-full text-xs">
          <thead className="bg-gray-50 sticky top-0">
            <tr>
              {data.headers.map((header) => (
                <th
                  key={header}
                  className="px-3 py-2 text-left font-medium text-gray-500 uppercase tracking-wider whitespace-nowrap"
                >
                  {header}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {displayRows.map((row, idx) => (
              <tr key={idx} className="hover:bg-gray-50">
                {data.headers.map((header) => (
                  <td
                    key={`${idx}-${header}`}
                    className="px-3 py-1.5 text-gray-700 whitespace-nowrap"
                  >
                    {row[header] !== null && row[header] !== undefined
                      ? String(row[header])
                      : '—'}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {data.rows.length > 5 && (
        <div className="px-4 py-2 border-t border-gray-100 text-xs text-gray-400 text-center">
          Showing first 5 of {data.rows.length} rows
        </div>
      )}
    </div>
  )
}
