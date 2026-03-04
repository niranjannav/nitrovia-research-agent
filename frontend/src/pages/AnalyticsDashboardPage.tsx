import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { useAnalyticsStore } from '../stores/analyticsStore'
import type { AnalyticsDomain, AnalyticsUpload } from '../types/analytics'

const DOMAINS: { value: AnalyticsDomain; label: string; color: string; bgColor: string }[] = [
  { value: 'sales', label: 'Sales', color: 'text-primary-600', bgColor: 'bg-primary-100' },
  { value: 'production', label: 'Production', color: 'text-green-600', bgColor: 'bg-green-100' },
  { value: 'qa', label: 'Quality Assurance', color: 'text-purple-600', bgColor: 'bg-purple-100' },
  { value: 'finance', label: 'Finance', color: 'text-amber-600', bgColor: 'bg-amber-100' },
]

function StatusBadge({ status }: { status: AnalyticsUpload['status'] }) {
  const classes = {
    completed: 'bg-green-100 text-green-700',
    processing: 'bg-yellow-100 text-yellow-700',
    pending: 'bg-yellow-100 text-yellow-700',
    failed: 'bg-red-100 text-red-700',
  }
  return (
    <span className={`px-2.5 py-0.5 rounded-full text-xs font-medium ${classes[status]}`}>
      {status}
    </span>
  )
}

export default function AnalyticsDashboardPage() {
  const { uploads, isLoading, fetchUploads, deleteUpload } = useAnalyticsStore()
  const [deletingId, setDeletingId] = useState<string | null>(null)

  useEffect(() => {
    fetchUploads()
  }, [fetchUploads])

  const completedUploads = uploads.filter((u) => u.status === 'completed')

  const uploadsByDomain = (domain: AnalyticsDomain) =>
    completedUploads.filter((u) => u.domain === domain)

  const handleDelete = async (id: string) => {
    if (!confirm('Delete this upload and all its records? This cannot be undone.')) return
    setDeletingId(id)
    await deleteUpload(id)
    setDeletingId(null)
  }

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Analytics</h1>
          <p className="text-gray-600 mt-1">
            Upload structured data and generate time-based analytics reports.
          </p>
        </div>
        <div className="flex gap-3">
          <Link
            to="/analytics/upload"
            className="inline-flex items-center px-4 py-2 border border-gray-300 rounded-lg text-sm font-medium text-gray-700 hover:bg-gray-50 transition-colors"
          >
            <svg className="w-4 h-4 mr-1.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
            </svg>
            Upload Data
          </Link>
          <Link
            to="/analytics/reports/new"
            className="inline-flex items-center px-4 py-2 bg-primary-600 text-white rounded-lg text-sm font-medium hover:bg-primary-700 transition-colors"
          >
            <svg className="w-4 h-4 mr-1.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
            </svg>
            New Report
          </Link>
        </div>
      </div>

      {/* Domain Status Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {DOMAINS.map((d) => {
          const domainUploads = uploadsByDomain(d.value)
          const latest = domainUploads[0]
          return (
            <div key={d.value} className="bg-white rounded-xl shadow-sm border border-gray-100 p-5">
              <div className="flex items-center gap-3 mb-3">
                <div className={`w-9 h-9 rounded-lg ${d.bgColor} flex items-center justify-center`}>
                  <svg className={`w-5 h-5 ${d.color}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                  </svg>
                </div>
                <p className="font-medium text-gray-900">{d.label}</p>
              </div>
              {domainUploads.length > 0 ? (
                <div className="space-y-1">
                  <p className="text-2xl font-semibold text-gray-900">{domainUploads.length}</p>
                  <p className="text-xs text-gray-500">
                    dataset{domainUploads.length !== 1 ? 's' : ''} uploaded
                  </p>
                  {latest && (
                    <p className="text-xs text-gray-400">
                      Last: {new Date(latest.created_at).toLocaleDateString()}
                    </p>
                  )}
                </div>
              ) : (
                <div>
                  <p className="text-sm text-gray-400">No data yet</p>
                  <Link
                    to="/analytics/upload"
                    className={`text-xs font-medium mt-1 inline-block ${d.color} hover:underline`}
                  >
                    Upload now →
                  </Link>
                </div>
              )}
            </div>
          )
        })}
      </div>

      {/* Uploads Table */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-100">
        <div className="px-6 py-4 border-b border-gray-100 flex items-center justify-between">
          <h2 className="font-semibold text-gray-900">All Uploads</h2>
          {uploads.length > 0 && (
            <span className="text-sm text-gray-500">{uploads.length} total</span>
          )}
        </div>

        {isLoading ? (
          <div className="flex items-center justify-center py-12">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600" />
          </div>
        ) : uploads.length === 0 ? (
          <div className="text-center py-12">
            <svg className="mx-auto w-12 h-12 text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
            </svg>
            <p className="text-gray-500 mt-3">No uploads yet</p>
            <Link
              to="/analytics/upload"
              className="text-primary-600 hover:text-primary-700 font-medium mt-1 inline-block text-sm"
            >
              Upload your first dataset
            </Link>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-100 bg-gray-50">
                  <th className="text-left px-6 py-3 text-xs font-medium text-gray-500 uppercase tracking-wide">File</th>
                  <th className="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase tracking-wide">Domain</th>
                  <th className="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase tracking-wide">Period</th>
                  <th className="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase tracking-wide">Records</th>
                  <th className="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase tracking-wide">Status</th>
                  <th className="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase tracking-wide">Uploaded</th>
                  <th className="px-4 py-3" />
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {uploads.map((upload) => (
                  <tr key={upload.id} className="hover:bg-gray-50 transition-colors">
                    <td className="px-6 py-3 font-medium text-gray-900 max-w-xs truncate">
                      {upload.file_name}
                    </td>
                    <td className="px-4 py-3 capitalize text-gray-600">{upload.domain}</td>
                    <td className="px-4 py-3 text-gray-500 whitespace-nowrap">
                      {upload.period_start} – {upload.period_end}
                    </td>
                    <td className="px-4 py-3 text-gray-600">
                      {upload.row_count != null ? upload.row_count.toLocaleString() : '—'}
                    </td>
                    <td className="px-4 py-3">
                      <StatusBadge status={upload.status} />
                    </td>
                    <td className="px-4 py-3 text-gray-400 whitespace-nowrap">
                      {new Date(upload.created_at).toLocaleDateString()}
                    </td>
                    <td className="px-4 py-3 text-right">
                      <button
                        onClick={() => handleDelete(upload.id)}
                        disabled={deletingId === upload.id}
                        className="text-xs text-red-400 hover:text-red-600 transition-colors disabled:opacity-40"
                      >
                        Delete
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}
