import { Link, useLocation } from 'react-router-dom'
import { useEffect } from 'react'
import { useAuthStore } from '../../stores/authStore'
import { useConfigStore } from '../../stores/configStore'

export default function Header() {
  const { user, signOut } = useAuthStore()
  const { productionMode, devToggleAvailable, modelTier, isLoading, fetchMode, toggleMode } = useConfigStore()
  const location = useLocation()

  useEffect(() => {
    fetchMode()
  }, [fetchMode])

  const isActive = (path: string) => location.pathname === path
  const isActivePrefix = (prefix: string) => location.pathname.startsWith(prefix)

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
            <Link
              to="/analytics"
              className={`px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                isActivePrefix('/analytics')
                  ? 'bg-primary-50 text-primary-700'
                  : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'
              }`}
            >
              Analytics
            </Link>
          </nav>

          {/* User menu */}
          <div className="flex items-center space-x-4">
            {/* Production / Dev mode toggle */}
            {devToggleAvailable && !isLoading && (
              <div className="flex items-center space-x-2">
                <span className={`text-xs font-medium ${productionMode ? 'text-gray-400' : 'text-amber-600'}`}>
                  Dev
                </span>
                <button
                  onClick={toggleMode}
                  className={`relative inline-flex h-5 w-9 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-1 ${
                    productionMode ? 'bg-primary-600' : 'bg-amber-400'
                  }`}
                  title={productionMode ? 'Production mode (Sonnet)' : 'Dev mode (Haiku)'}
                >
                  <span
                    className={`inline-block h-3.5 w-3.5 transform rounded-full bg-white transition-transform ${
                      productionMode ? 'translate-x-[1.125rem]' : 'translate-x-0.5'
                    }`}
                  />
                </button>
                <span className={`text-xs font-medium ${productionMode ? 'text-primary-700' : 'text-gray-400'}`}>
                  Prod
                </span>
                <span className={`ml-1 rounded px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide ${
                  productionMode
                    ? 'bg-primary-50 text-primary-700'
                    : 'bg-amber-50 text-amber-700'
                }`}>
                  {modelTier}
                </span>
              </div>
            )}
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
