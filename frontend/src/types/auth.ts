export interface User {
  id: string
  email: string
  full_name: string | null
}

export interface AuthResponse {
  user: User
  access_token: string | null
  refresh_token: string | null
}

export interface SignupRequest {
  email: string
  password: string
  full_name: string
}

export interface LoginRequest {
  email: string
  password: string
}
