import axios from 'axios'
import { createClient } from '@supabase/supabase-js'

// Initialize Supabase client
export const supabase = createClient(
  import.meta.env.VITE_SUPABASE_URL,
  import.meta.env.VITE_SUPABASE_ANON_KEY
)

// Create axios instance for API calls
const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Add auth token to all requests
api.interceptors.request.use(async (config) => {
  const { data: { session } } = await supabase.auth.getSession()

  if (session?.access_token) {
    config.headers.Authorization = `Bearer ${session.access_token}`
  }

  return config
})

// Handle response errors
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    // Handle 401 Unauthorized
    if (error.response?.status === 401) {
      // Try to refresh the session
      const { data: { session } } = await supabase.auth.refreshSession()

      if (session) {
        // Retry the request with new token
        error.config.headers.Authorization = `Bearer ${session.access_token}`
        return api.request(error.config)
      }

      // If refresh failed, sign out
      await supabase.auth.signOut()
      window.location.href = '/login'
    }

    return Promise.reject(error)
  }
)

export default api
