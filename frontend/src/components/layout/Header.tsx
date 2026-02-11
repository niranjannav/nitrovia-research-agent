import { Link, useLocation } from 'react-router-dom'
import { useAuthStore } from '../../stores/authStore'

export default function Header() {
  const { user, signOut } = useAuthStore()
  const location = useLocation()

  const isActive = (path: string) => location.pathname === path

  return (
    <header className="bg-white border-b border-gray-200">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-16">
          {/* Logo */}
          <Link to="/" className="flex items-center space-x-2">
            <div className="w-8 h-8 bg-primary-600 rounded-lg flex items-center justify-center">
              <svg
                className="w-5 h-5 text-white"
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
            <span className="text-lg font-semibold text-gray-900">
              Report Generator
            </span>
          </Link>

          {/* Navigation */}
          <nav className="flex items-center space-x-1">
            <Link
              to="/"
              className={`px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                isActive('/')
                  ? 'bg-primary-50 text-primary-700'
                  : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'
              }`}
            >
              Dashboard
            </Link>
            <Link
              to="/reports/new"
              className={`px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                isActive('/reports/new')
                  ? 'bg-primary-50 text-primary-700'
                  : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'
              }`}
            >
              New Report
            </Link>
          </nav>

          {/* User menu */}
          <div className="flex items-center space-x-4">
            <span className="text-sm text-gray-600">{user?.email}</span>
            <button
              onClick={() => signOut()}
              className="text-sm text-gray-600 hover:text-gray-900 transition-colors"
            >
              Sign out
            </button>
          </div>
        </div>
      </div>
    </header>
  )
}
