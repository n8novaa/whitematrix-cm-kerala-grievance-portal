import assert from 'node:assert/strict'
import test from 'node:test'
import { createTokenStore } from './auth-storage.js'

function createStorage(initial = {}) {
  const values = new Map(Object.entries(initial))
  return {
    getItem(key) { return values.has(key) ? values.get(key) : null },
    setItem(key, value) { values.set(key, String(value)) },
    removeItem(key) { values.delete(key) },
  }
}

test('legacy tokens migrate into one tab and logins, refreshes, and logout stay tab-local', () => {
  const legacyStorage = createStorage({ accessToken: 'legacy-officer', refreshToken: 'legacy-refresh' })
  const officerSession = createStorage()
  const cmoSession = createStorage()
  const officer = createTokenStore(officerSession, legacyStorage)

  assert.equal(officer.getAccessToken(), 'legacy-officer')
  assert.equal(officer.getRefreshToken(), 'legacy-refresh')
  assert.equal(legacyStorage.getItem('accessToken'), null)

  const cmo = createTokenStore(cmoSession, legacyStorage)
  assert.equal(cmo.getAccessToken(), null)
  cmo.setTokens('cmo-access', 'cmo-refresh')
  cmo.updateAccessToken('cmo-refreshed')

  assert.equal(officer.getAccessToken(), 'legacy-officer')
  assert.equal(officer.getRefreshToken(), 'legacy-refresh')
  assert.equal(cmo.getAccessToken(), 'cmo-refreshed')
  assert.equal(cmo.getRefreshToken(), 'cmo-refresh')

  cmo.clearTokens()
  assert.equal(cmo.getAccessToken(), null)
  assert.equal(officer.getAccessToken(), 'legacy-officer')
})

test('existing tab session takes precedence over and clears shared legacy tokens', () => {
  const sharedLegacy = createStorage({ accessToken: 'stale-shared', refreshToken: 'stale-refresh' })
  const session = createStorage({ accessToken: 'current-tab', refreshToken: 'current-refresh' })
  const store = createTokenStore(session, sharedLegacy)

  assert.equal(store.getAccessToken(), 'current-tab')
  assert.equal(store.getRefreshToken(), 'current-refresh')
  assert.equal(sharedLegacy.getItem('accessToken'), null)
})
