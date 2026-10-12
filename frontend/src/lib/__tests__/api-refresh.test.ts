import { describe, it, expect, beforeAll, afterAll, afterEach, beforeEach } from 'vitest'
import { http, HttpResponse } from 'msw'
import { setupServer } from 'msw/node'

import api from '../api'

/**
 * Regression test for the single-flight refresh fix: concurrent 401s
 * previously each triggered an independent POST /auth/refresh call. If the
 * backend rotates/invalidates the refresh token on use, the first call
 * succeeds and stores new tokens, but the second call's refresh (using the
 * now-already-consumed token) fails - logging the user out even though a
 * valid refreshed session exists from the first call.
 *
 * Uses its own local MSW server (rather than the shared src/test/mockServer)
 * so it isn't coupled to that fixture's unrelated pre-existing issues.
 */

const API_BASE = 'http://localhost:8000/api/v1'

let refreshCallCount = 0

const server = setupServer(
  http.get(`${API_BASE}/protected`, ({ request }) => {
    const auth = request.headers.get('authorization')
    if (auth === 'Bearer new-token') {
      return HttpResponse.json({ ok: true })
    }
    return new HttpResponse(null, { status: 401 })
  }),
  http.post(`${API_BASE}/auth/refresh`, async () => {
    refreshCallCount++
    // Simulate network latency so both concurrent 401s are guaranteed to
    // observe "a refresh is already in flight" rather than racing to be
    // first to set refreshPromise.
    await new Promise((resolve) => setTimeout(resolve, 20))
    return HttpResponse.json({
      access_token: 'new-token',
      refresh_token: 'rotated-refresh-token',
    })
  })
)

beforeAll(() => server.listen({ onUnhandledRequest: 'bypass' }))
afterEach(() => server.resetHandlers())
afterAll(() => server.close())

describe('api.ts 401 refresh single-flight', () => {
  beforeEach(() => {
    refreshCallCount = 0
    localStorage.setItem('access_token', 'old-token')
    localStorage.setItem('refresh_token', 'valid-refresh-token')
  })

  it('shares one refresh call across concurrent 401s and retries both requests', async () => {
    const [first, second] = await Promise.all([
      api.get('/protected'),
      api.get('/protected'),
    ])

    expect(first.data).toEqual({ ok: true })
    expect(second.data).toEqual({ ok: true })
    expect(refreshCallCount).toBe(1)
    expect(localStorage.getItem('access_token')).toBe('new-token')
  })
})
