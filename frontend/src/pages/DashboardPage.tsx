import { useEffect } from 'react'
import { Link } from 'react-router-dom'
import { useAuthStore } from '../stores/authStore'
import { useReportStore } from '../stores/reportStore'

export default function DashboardPage() {
  const { user, quota, fetchQuota } = useAuthStore()
  const { reports, totalReports, fetchReports, isLoading } = useReportStore()

  useEffect(() => {
    fetchReports(1)
    fetchQuota()
  }, [fetchReports, fetchQuota])

  const recentReports = reports.slice(0, 5)

  const completedCount = reports.filter((r) => r.status === 'completed').length
  const processingCount = reports.filter(
    (r) => r.status === 'processing' || r.status === 'pending'
  ).length

  return (
    <div className="space-y-8">
      {/* Welcome section */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">
          Welcome back{user?.full_name ? `, ${user.full_name.split(' ')[0]}` : ''}
        </h1>
        <p className="text-gray-600 mt-1">
          Generate research reports and presentations from your documents
        </p>
      </div>

      {/* Quick stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="bg-white rounded-xl shadow-sm p-6 border border-gray-100">
          <div className="flex items-center">
            <div className="p-3 bg-primary-100 rounded-lg">
              <svg
                className="w-6 h-6 text-primary-600"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                />
              </svg>
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-500">Total Reports</p>
              <p className="text-2xl font-semibold text-gray-900">{totalReports}</p>
            </div>
          </div>
        </div>

        <div className="bg-white rounded-xl shadow-sm p-6 border border-gray-100">
          <div className="flex items-center">
            <div className="p-3 bg-green-100 rounded-lg">
              <svg
                className="w-6 h-6 text-green-600"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M5 13l4 4L19 7"
                />
              </svg>
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-500">Completed</p>
              <p className="text-2xl font-semibold text-gray-900">{completedCount}</p>
            </div>
          </div>
        </div>

        <div className="bg-white rounded-xl shadow-sm p-6 border border-gray-100">
          <div className="flex items-center">
            <div className="p-3 bg-yellow-100 rounded-lg">
              <svg
                className="w-6 h-6 text-yellow-600"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
                />
              </svg>
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-500">Processing</p>
              <p className="text-2xl font-semibold text-gray-900">{processingCount}</p>
            </div>
          </div>
        </div>
      </div>

      {/* Quick actions */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className={`rounded-xl p-6 text-white ${
          quota && !quota.is_admin && quota.exceeded
            ? 'bg-gradient-to-r from-gray-500 to-gray-600'
            : 'bg-gradient-to-r from-primary-600 to-primary-700'
        }`}>
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-xl font-semibold">
                {quota && !quota.is_admin && quota.exceeded
                  ? 'Monthly Limit Reached'
                  : 'Create a New Report'}
              </h2>
              <p className={quota && !quota.is_admin && quota.exceeded ? 'text-gray-200 mt-1' : 'text-primary-100 mt-1'}>
                {quota && !quota.is_admin && quota.exceeded
                  ? `You've used all ${quota.limit} reports this month. Resets ${new Date(quota.resets_at).toLocaleDateString()}.`
                  : quota && !quota.is_admin
                  ? `${quota.remaining} of ${quota.limit} reports remaining this month`
                  : 'Upload documents and generate professional reports'}
              </p>
            </div>
            {(!quota || quota.is_admin || !quota.exceeded) && (
              <Link
                to="/reports/new"
                className="inline-flex items-center px-6 py-3 bg-white text-primary-600 font-medium rounded-lg hover:bg-primary-50 transition-colors"
              >
                <svg
                  className="w-5 h-5 mr-2"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M12 4v16m8-8H4"
                  />
                </svg>
                New Report
              </Link>
            )}
          </div>
        </div>

        <div className="rounded-xl p-6 text-white bg-gradient-to-r from-green-600 to-emerald-700">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-xl font-semibold">Data Analysis</h2>
              <p className="text-green-100 mt-1">
                Upload an Excel file and chat with your data using AI
              </p>
            </div>
            <Link
              to="/data-analysis"
              className="inline-flex items-center px-6 py-3 bg-white text-green-600 font-medium rounded-lg hover:bg-green-50 transition-colors"
            >
              <svg
                className="w-5 h-5 mr-2"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                />
              </svg>
              Analyze Data
            </Link>
          </div>
        </div>
      </div>

      {/* Recent reports */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-100">
        <div className="px-6 py-4 border-b border-gray-100 flex items-center justify-between">
          <h2 className="font-semibold text-gray-900">Recent Reports</h2>
          <Link
            to="/reports"
            className="text-sm text-primary-600 hover:text-primary-700 font-medium"
          >
            View all
          </Link>
        </div>

        {isLoading ? (
          <div className="flex items-center justify-center py-12">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
          </div>
        ) : recentReports.length === 0 ? (
          <div className="text-center py-12">
            <svg
              className="mx-auto w-12 h-12 text-gray-400"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={1.5}
                d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
              />
            </svg>
            <p className="text-gray-500 mt-2">No reports yet</p>
            <Link
              to="/reports/new"
              className="text-primary-600 hover:text-primary-700 font-medium mt-1 inline-block"
            >
              Create your first report
            </Link>
          </div>
        ) : (
          <ul className="divide-y divide-gray-100">
            {recentReports.map((report) => (
              <li key={report.id}>
                <Link
                  to={report.status === 'completed' ? `/reports/${report.id}` : '#'}
                  className={`block px-6 py-4 hover:bg-gray-50 transition-colors ${
                    report.status === 'completed' ? 'cursor-pointer' : 'cursor-default'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="font-medium text-gray-900">
                        {report.title || 'Untitled Report'}
                      </p>
                      <p className="text-sm text-gray-500">
                        {new Date(report.created_at || '').toLocaleDateString()} •{' '}
                        {report.detail_level}
                      </p>
                    </div>
                    <div className="flex items-center gap-3">
                      <span
                        className={`px-2.5 py-0.5 rounded-full text-xs font-medium ${
                          report.status === 'completed'
                            ? 'bg-green-100 text-green-700'
                            : report.status === 'failed'
                            ? 'bg-red-100 text-red-700'
                            : 'bg-yellow-100 text-yellow-700'
                        }`}
                      >
                        {report.status}
                      </span>
                      {report.status === 'completed' && (
                        <svg
                          className="w-5 h-5 text-gray-400"
                          fill="none"
                          stroke="currentColor"
                          viewBox="0 0 24 24"
                        >
                          <path
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            strokeWidth={2}
                            d="M9 5l7 7-7 7"
                          />
                        </svg>
                      )}
                    </div>
                  </div>
                </Link>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  )
}
