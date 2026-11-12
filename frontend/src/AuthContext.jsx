import { useEffect, useState } from 'react'
import { api, jsonRequest } from './api'
import { clearTokens, getAccessToken, getRefreshToken, setTokens } from './auth-storage'
import { AuthContext } from './auth-context'

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(Boolean(getAccessToken()))

  useEffect(() => {
    if (!getAccessToken()) return
    api('/auth/profile/')
      .then(setUser)
      .catch(() => clearTokens())
      .finally(() => setLoading(false))
  }, [])

  async function signIn(email, password) {
    const tokens = await api('/auth/login/', jsonRequest('POST', { email, password }))
    setTokens(tokens.access, tokens.refresh)
    const profile = await api('/auth/profile/')
    setUser(profile)
    return profile
  }

  async function register(values) {
    await api('/auth/register/', jsonRequest('POST', values))
    return signIn(values.email, values.password)
  }

  async function signOut() {
    const refresh = getRefreshToken()
    try {
      if (refresh) await api('/auth/logout/', jsonRequest('POST', { refresh }))
    } catch {
      // Clear this tab's session even if the prototype API cannot be reached.
    } finally {
      clearTokens()
      setUser(null)
    }
  }

  const value = { user, setUser, loading, signIn, register, signOut }
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}
