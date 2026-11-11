import { useEffect, useState } from 'react'
import { api, jsonRequest } from './api'
import { AuthContext } from './auth-context'

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(Boolean(localStorage.getItem('accessToken')))

  useEffect(() => {
    if (!localStorage.getItem('accessToken')) return
    api('/auth/profile/')
      .then(setUser)
      .catch(() => {
        localStorage.removeItem('accessToken')
        localStorage.removeItem('refreshToken')
      })
      .finally(() => setLoading(false))
  }, [])

  async function signIn(email, password) {
    const tokens = await api('/auth/login/', jsonRequest('POST', { email, password }))
    localStorage.setItem('accessToken', tokens.access)
    localStorage.setItem('refreshToken', tokens.refresh)
    const profile = await api('/auth/profile/')
    setUser(profile)
    return profile
  }

  async function register(values) {
    await api('/auth/register/', jsonRequest('POST', values))
    return signIn(values.email, values.password)
  }

  async function signOut() {
    const refresh = localStorage.getItem('refreshToken')
    try {
      if (refresh) await api('/auth/logout/', jsonRequest('POST', { refresh }))
    } catch {
      // Clear the local session even if the prototype API cannot be reached.
    } finally {
      localStorage.removeItem('accessToken')
      localStorage.removeItem('refreshToken')
      setUser(null)
    }
  }

  const value = { user, setUser, loading, signIn, register, signOut }
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}
