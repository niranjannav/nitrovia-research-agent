import { Link, useLocation } from 'react-router-dom'
import { useAuthStore } from '../../stores/authStore'

export default function Header() {
  const { user, signOut } = useAuthStore()
  const location = useLocation()

  const isActive = (path: string) => location.pathname === path

  return (
    <header className="bg-white border-b border-gray-100 shadow-soft">
      <div className="px-6 lg:px-8">
        <div className="flex justify-between items-center h-14">
          {/* Logo */}
          <Link to="/" className="flex items-center space-x-2.5">
            <div className="w-8 h-8 bg-primary-800 rounded-lg flex items-center justify-center">
              <svg
                className="w-5 h-5 text-accent-400"
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
            <span className="text-base font-semibold text-primary-800 tracking-tight">
              Shambani Milk
            </span>
          </Link>

          {/* Center nav with History breadcrumb */}
          <nav className="flex items-center space-x-1">
            <Link
              to="/"
              className={`px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
                isActive('/')
                  ? 'bg-primary-50 text-primary-700'
                  : 'text-gray-500 hover:text-gray-800 hover:bg-gray-50'
              }`}
            >
              Dashboard
            </Link>
            <Link
              to="/reports/new"
              className={`px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
                isActive('/reports/new')
                  ? 'bg-primary-50 text-primary-700'
                  : 'text-gray-500 hover:text-gray-800 hover:bg-gray-50'
              }`}
            >
              New Report
            </Link>
            <Link
              to="/reports"
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
                isActive('/reports')
                  ? 'bg-primary-50 text-primary-700'
                  : 'text-gray-500 hover:text-gray-800 hover:bg-gray-50'
              }`}
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              History
            </Link>
          </nav>

          {/* User menu */}
          <div className="flex items-center space-x-3">
            <span className="text-sm text-gray-500">{user?.email}</span>
            <button
              onClick={() => signOut()}
              className="text-sm text-gray-500 hover:text-gray-700 px-2.5 py-1.5 rounded-md hover:bg-gray-50 transition-colors"
            >
              Sign out
            </button>
          </div>
        </div>
      </div>
    </header>
  )
}
