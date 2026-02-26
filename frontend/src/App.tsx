import { Routes, Route, Navigate } from 'react-router-dom'
import { useEffect } from 'react'
import { useAuthStore } from './stores/authStore'
import Layout from './components/layout/Layout'
import AuthGuard from './components/auth/AuthGuard'
import LoginPage from './pages/LoginPage'
import DashboardPage from './pages/DashboardPage'
import NewReportPage from './pages/NewReportPage'
import ReportHistoryPage from './pages/ReportHistoryPage'
import ReportViewPage from './pages/ReportViewPage'
import DataAnalysisPage from './pages/DataAnalysisPage'

function App() {
  const { checkAuth, isLoading } = useAuthStore()

  useEffect(() => {
    checkAuth()
  }, [checkAuth])

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
      </div>
    )
  }

  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />

      <Route element={<AuthGuard />}>
        <Route element={<Layout />}>
          <Route path="/" element={<DashboardPage />} />
          <Route path="/reports/new" element={<NewReportPage />} />
          <Route path="/reports" element={<ReportHistoryPage />} />
          <Route path="/reports/:reportId" element={<ReportViewPage />} />
          <Route path="/data-analysis" element={<DataAnalysisPage />} />
        </Route>
      </Route>

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}

export default App
