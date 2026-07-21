import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'

/**
 * Regression tests for two bugs in the WebSocket singleton service:
 *
 * 1. disconnect() didn't clear `this.token`, so the WebSocket's own async
 *    `onclose` handler (bound before disconnect() was called - close events
 *    fire asynchronously) could still fire afterward and schedule a
 *    reconnect using the just-disconnected token.
 * 2. Reconnect reused the token captured at the original connect() call,
 *    so after api.ts silently rotated the stored access token via its 401
 *    refresh flow (no React re-render involved), a dropped connection
 *    would reconnect with the stale token instead of the current one.
 */

class MockWebSocket {
  static instances: MockWebSocket[] = []
  static OPEN = 1
  static CLOSED = 3

  url: string
  readyState = MockWebSocket.OPEN
  onopen: (() => void) | null = null
  onmessage: ((event: { data: string }) => void) | null = null
  onerror: ((error: unknown) => void) | null = null
  onclose: (() => void) | null = null

  constructor(url: string) {
    this.url = url
    MockWebSocket.instances.push(this)
  }

  send() {}

  close() {
    this.readyState = MockWebSocket.CLOSED
    // Real WebSocket close events are asynchronous - simulate that by not
    // invoking onclose synchronously here. Tests trigger it explicitly to
    // control timing relative to disconnect().
  }

  // Test helper: simulate the connection opening successfully.
  triggerOpen() {
    this.readyState = MockWebSocket.OPEN
    this.onopen?.()
  }

  // Test helper: simulate the async close event arriving. Real close
  // events only fire once readyState has actually transitioned to
  // CLOSED, and connect()'s "already open" guard checks readyState - so
  // this must flip it before invoking the handler.
  triggerClose() {
    this.readyState = MockWebSocket.CLOSED
    this.onclose?.()
  }
}

describe('websocketService', () => {
  beforeEach(() => {
    vi.resetModules()
    vi.useFakeTimers()
    MockWebSocket.instances = []
    ;(global as any).WebSocket = MockWebSocket
    window.localStorage.clear()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('does not reconnect after an intentional disconnect even when the async onclose fires afterward', async () => {
    const { websocketService } = await import('../websocket')

    websocketService.connect('token-a')
    expect(MockWebSocket.instances).toHaveLength(1)
    MockWebSocket.instances[0].triggerOpen()

    websocketService.disconnect()

    // Simulate the WebSocket's own async close event landing after
    // disconnect() already ran - this previously still scheduled (and
    // eventually executed) a reconnect using the cleared token.
    MockWebSocket.instances[0].triggerClose()

    // Advance past the reconnect delay (and its exponential backoff) -
    // no new WebSocket should ever be constructed.
    await vi.advanceTimersByTimeAsync(60000)

    expect(MockWebSocket.instances).toHaveLength(1)
  })

  it('reconnects using the current localStorage token, not the stale one captured at connect() time', async () => {
    const { websocketService } = await import('../websocket')

    window.localStorage.setItem('access_token', 'token-a')
    websocketService.connect('token-a')
    MockWebSocket.instances[0].triggerOpen()

    // Simulate api.ts's refresh interceptor silently rotating the token
    // in localStorage - no React re-render, no call to connect() again.
    window.localStorage.setItem('access_token', 'token-b')

    // Connection drops unexpectedly (not an intentional disconnect).
    MockWebSocket.instances[0].triggerClose()

    await vi.advanceTimersByTimeAsync(10000)

    expect(MockWebSocket.instances).toHaveLength(2)
    expect(MockWebSocket.instances[1].url).toContain('token-b')
  })
})
