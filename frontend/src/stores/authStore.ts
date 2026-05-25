import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import { decodeJwt, setTokens, clearTokens } from '@/lib/api'
import type { UserDto, AuthResponse } from '@/lib/types'

interface JwtPayload {
  sub: string
  email: string
  firstName?: string
  lastName?: string
  role: 'user' | 'admin'
  exp: number
}

interface AuthState {
  user: UserDto | null
  isAuthenticated: boolean
  theme: 'dark' | 'light'
  _hasHydrated: boolean

  login: (response: AuthResponse) => void
  logout: () => void
  toggleTheme: () => void
  setUser: (user: UserDto) => void
  setHasHydrated: (v: boolean) => void
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      isAuthenticated: false,
      theme: 'light',
      _hasHydrated: false,

      login(response: AuthResponse) {
        setTokens(response.accessToken, response.refreshToken, response.expiresAt)

        const claims = decodeJwt<JwtPayload>(response.accessToken)
        const user: UserDto = claims
          ? {
              id: claims.sub,
              email: claims.email,
              firstName: claims.firstName ?? response.user.firstName,
              lastName: claims.lastName ?? response.user.lastName,
              role: claims.role,
              createdAt: response.user.createdAt,
            }
          : response.user

        set({ user, isAuthenticated: true })
      },

      logout() {
        clearTokens()
        set({ user: null, isAuthenticated: false })
        window.location.href = '/login'
      },

      setUser(user: UserDto) {
        set({ user })
      },

      toggleTheme() {
        set((s) => {
          const next = s.theme === 'dark' ? 'light' : 'dark'
          document.documentElement.classList.toggle('light', next === 'light')
          return { theme: next }
        })
      },

      setHasHydrated(v: boolean) {
        set({ _hasHydrated: v })
      },
    }),
    {
      name: 'auth-store',
      partialize: (s) => ({ user: s.user, isAuthenticated: s.isAuthenticated, theme: s.theme }),
      onRehydrateStorage: () => (state) => {
        state?.setHasHydrated(true)
      },
    }
  )
)
