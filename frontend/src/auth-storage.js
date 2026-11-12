const ACCESS_TOKEN_KEY = 'accessToken'
const REFRESH_TOKEN_KEY = 'refreshToken'

export function createTokenStore(sessionStorage, legacyStorage) {
  let migrationComplete = false

  function migrateLegacyTokens() {
    if (migrationComplete) return

    const hasTabSession = sessionStorage.getItem(ACCESS_TOKEN_KEY) || sessionStorage.getItem(REFRESH_TOKEN_KEY)
    if (!hasTabSession) {
      const legacyAccess = legacyStorage.getItem(ACCESS_TOKEN_KEY)
      const legacyRefresh = legacyStorage.getItem(REFRESH_TOKEN_KEY)
      if (legacyAccess) sessionStorage.setItem(ACCESS_TOKEN_KEY, legacyAccess)
      if (legacyRefresh) sessionStorage.setItem(REFRESH_TOKEN_KEY, legacyRefresh)
    }

    legacyStorage.removeItem(ACCESS_TOKEN_KEY)
    legacyStorage.removeItem(REFRESH_TOKEN_KEY)
    migrationComplete = true
  }

  return {
    getAccessToken() {
      migrateLegacyTokens()
      return sessionStorage.getItem(ACCESS_TOKEN_KEY)
    },
    getRefreshToken() {
      migrateLegacyTokens()
      return sessionStorage.getItem(REFRESH_TOKEN_KEY)
    },
    setTokens(accessToken, refreshToken) {
      migrateLegacyTokens()
      sessionStorage.setItem(ACCESS_TOKEN_KEY, accessToken)
      sessionStorage.setItem(REFRESH_TOKEN_KEY, refreshToken)
    },
    updateAccessToken(accessToken) {
      migrateLegacyTokens()
      sessionStorage.setItem(ACCESS_TOKEN_KEY, accessToken)
    },
    updateRefreshToken(refreshToken) {
      migrateLegacyTokens()
      sessionStorage.setItem(REFRESH_TOKEN_KEY, refreshToken)
    },
    clearTokens() {
      migrateLegacyTokens()
      sessionStorage.removeItem(ACCESS_TOKEN_KEY)
      sessionStorage.removeItem(REFRESH_TOKEN_KEY)
    },
  }
}

const tokenStore = typeof window === 'undefined'
  ? null
  : createTokenStore(window.sessionStorage, window.localStorage)

export const getAccessToken = () => tokenStore?.getAccessToken() ?? null
export const getRefreshToken = () => tokenStore?.getRefreshToken() ?? null
export const setTokens = (accessToken, refreshToken) => tokenStore?.setTokens(accessToken, refreshToken)
export const updateAccessToken = (accessToken) => tokenStore?.updateAccessToken(accessToken)
export const updateRefreshToken = (refreshToken) => tokenStore?.updateRefreshToken(refreshToken)
export const clearTokens = () => tokenStore?.clearTokens()
