import { useReportStore } from '../../stores/reportStore'

export default function EditHistory() {
  const { editHistory, undoEdit } = useReportStore()

  if (editHistory.length === 0) {
    return null
  }

  return (
    <div className="space-y-2">
      <h4 className="text-xs font-semibold text-gray-400 uppercase tracking-wider flex items-center gap-2">
        <HistoryIcon />
        Recent Edits
      </h4>
      <div className="space-y-1.5">
        {editHistory.map((entry, idx) => (
          <div
            key={idx}
            className="flex items-start justify-between gap-2 p-2.5 bg-gray-50 rounded-xl text-sm"
          >
            <div className="flex-1 min-w-0">
              <div className="font-medium text-gray-700 text-xs truncate">
                {entry.sectionTitle}
              </div>
              <div className="text-xs text-gray-400 mt-0.5">
                {formatTime(entry.appliedAt)}
              </div>
            </div>
            <button
              onClick={() => undoEdit(idx)}
              className="p-1 text-gray-300 hover:text-gray-500 transition-colors rounded"
              title="Remove from history"
            >
              <UndoIcon />
            </button>
          </div>
        ))}
      </div>
    </div>
  )
}

function formatTime(isoString: string): string {
  try {
    const date = new Date(isoString)
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
  } catch {
    return ''
  }
}

function HistoryIcon() {
  return (
    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
      />
    </svg>
  )
}

function UndoIcon() {
  return (
    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M3 10h10a8 8 0 018 8v2M3 10l6 6m-6-6l6-6"
      />
    </svg>
  )
}
