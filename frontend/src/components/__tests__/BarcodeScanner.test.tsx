import { describe, it, expect, beforeEach, vi } from 'vitest'
import { render } from '@testing-library/react'

import { BarcodeScanner } from '../BarcodeScanner'

/**
 * Regression test: the scanning effect depended on the onScan/onClose
 * props directly. PickingPage/ReceivingPage pass fresh inline closures on
 * every render, so any parent re-render while the scanner was open tore
 * down and restarted the camera (stop() wasn't even awaited before the
 * next start()). The fix reads the latest callback from a ref and depends
 * only on facingMode, so an unrelated parent re-render must not restart
 * the camera.
 */

const startMock = vi.fn().mockResolvedValue(undefined)
const stopMock = vi.fn().mockResolvedValue(undefined)

vi.mock('html5-qrcode', () => ({
  Html5Qrcode: vi.fn().mockImplementation(function MockHtml5Qrcode(this: any) {
    this.start = startMock
    this.stop = stopMock
    this.isScanning = false
  }),
}))

describe('BarcodeScanner', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('does not restart the camera when the parent re-renders with new onScan/onClose closures', async () => {
    const { rerender } = render(
      <BarcodeScanner onScan={() => true} onClose={() => {}} />
    )

    // Let the async startScanner() microtask resolve.
    await vi.waitFor(() => expect(startMock).toHaveBeenCalledTimes(1))

    // Simulate the parent re-rendering with brand new inline closures -
    // exactly what PickingPage/ReceivingPage do on every state update.
    for (let i = 0; i < 3; i++) {
      rerender(<BarcodeScanner onScan={() => true} onClose={() => {}} />)
    }

    // Give any (incorrect) effect re-run a chance to fire.
    await new Promise((resolve) => setTimeout(resolve, 0))

    expect(startMock).toHaveBeenCalledTimes(1)
    expect(stopMock).not.toHaveBeenCalled()
  })
})
