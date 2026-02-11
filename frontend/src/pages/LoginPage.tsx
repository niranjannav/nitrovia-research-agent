import { useState } from 'react'
import { Navigate } from 'react-router-dom'
import { useAuthStore } from '../stores/authStore'
import LoginForm from '../components/auth/LoginForm'
import SignupForm from '../components/auth/SignupForm'

export default function LoginPage() {
  const { user } = useAuthStore()
  const [isLogin, setIsLogin] = useState(true)

  // Redirect if already logged in
  if (user) {
    return <Navigate to="/" replace />
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-md w-full">
        {/* Logo and title */}
        <div className="text-center mb-8">
          <div className="mx-auto w-14 h-14 bg-primary-800 rounded-2xl flex items-center justify-center shadow-soft-md">
            <svg
              className="w-8 h-8 text-accent-400"
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
          <h2 className="mt-5 text-2xl font-bold text-primary-800 tracking-tight">
            Shambani Milk
          </h2>
          <p className="mt-1 text-sm text-gray-500">
            AI-Powered Report Generator
          </p>
          <p className="mt-3 text-sm text-gray-500">
            {isLogin
              ? 'Sign in to your account'
              : 'Create your account to get started'}
          </p>
        </div>

        {/* Form card */}
        <div className="bg-white py-8 px-6 shadow-soft-lg rounded-2xl border border-gray-100">
          {isLogin ? (
            <LoginForm onToggle={() => setIsLogin(false)} />
          ) : (
            <SignupForm onToggle={() => setIsLogin(true)} />
          )}
        </div>
      </div>
    </div>
  )
}
