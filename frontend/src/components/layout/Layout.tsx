import { Outlet, useLocation } from 'react-router-dom'
import Header from './Header'

export default function Layout() {
  const location = useLocation()
  const isReportView = location.pathname.startsWith('/reports/') && location.pathname !== '/reports' && location.pathname !== '/reports/new'

  return (
    <div className="min-h-screen bg-gray-50">
      <Header />
      <main className={isReportView ? 'h-[calc(100vh-3.5rem)]' : 'max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8'}>
        <Outlet />
      </main>
    </div>
  )
}
