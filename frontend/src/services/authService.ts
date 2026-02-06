import { supabase } from './api'
import type { User, SignupRequest, LoginRequest } from '../types/auth'

export const authService = {
  async signUp(data: SignupRequest): Promise<User> {
    const { data: authData, error } = await supabase.auth.signUp({
      email: data.email,
      password: data.password,
      options: {
        data: {
          full_name: data.full_name,
        },
      },
    })

    if (error) throw error
    if (!authData.user) throw new Error('Failed to create user')

    return {
      id: authData.user.id,
      email: authData.user.email!,
      full_name: data.full_name,
    }
  },

  async signIn(data: LoginRequest): Promise<User> {
    const { data: authData, error } = await supabase.auth.signInWithPassword({
      email: data.email,
      password: data.password,
    })

    if (error) throw error
    if (!authData.user) throw new Error('Invalid credentials')

    return {
      id: authData.user.id,
      email: authData.user.email!,
      full_name: authData.user.user_metadata?.full_name || null,
    }
  },

  async signOut(): Promise<void> {
    const { error } = await supabase.auth.signOut()
    if (error) throw error
  },

  async getCurrentUser(): Promise<User | null> {
    const { data: { session } } = await supabase.auth.getSession()

    if (!session?.user) return null

    return {
      id: session.user.id,
      email: session.user.email!,
      full_name: session.user.user_metadata?.full_name || null,
    }
  },

  onAuthStateChange(callback: (user: User | null) => void) {
    return supabase.auth.onAuthStateChange((event, session) => {
      if (session?.user) {
        callback({
          id: session.user.id,
          email: session.user.email!,
          full_name: session.user.user_metadata?.full_name || null,
        })
      } else {
        callback(null)
      }
    })
  },
}
