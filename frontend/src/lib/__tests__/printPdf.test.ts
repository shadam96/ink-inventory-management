import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { printPdf } from '../utils'

// "%PDF-1.4\n" - enough bytes for a Blob, the content is never parsed here.
const PDF_BASE64 = 'JVBERi0xLjQK'

const DESKTOP_CHROME =
  'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36'
const ANDROID_CHROME =
  'Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Mobile Safari/537.36'
const DESKTOP_SAFARI =
  'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Safari/605.1.15'

function printFrames(): HTMLIFrameElement[] {
  return Array.from(document.querySelectorAll('iframe'))
}

/** Fire the frame's load event with its print() stubbed - jsdom has no
 * PDF viewer and implements neither print nor focus. */
function loadFrame(frame: HTMLIFrameElement, print: () => void = () => {}) {
  vi.spyOn(frame.contentWindow!, 'focus').mockImplementation(() => {})
  const spy = vi.spyOn(frame.contentWindow!, 'print').mockImplementation(print)
  frame.dispatchEvent(new Event('load'))
  return spy
}

describe('printPdf', () => {
  let blobCount: number
  let openSpy: ReturnType<typeof vi.spyOn>

  beforeEach(() => {
    blobCount = 0
    Object.defineProperty(URL, 'createObjectURL', {
      configurable: true,
      writable: true,
      value: vi.fn(() => `blob:pdf-${++blobCount}`),
    })
    Object.defineProperty(URL, 'revokeObjectURL', {
      configurable: true,
      writable: true,
      value: vi.fn(),
    })
    openSpy = vi.spyOn(window, 'open').mockReturnValue(null)
  })

  afterEach(() => {
    printFrames().forEach((frame) => frame.remove())
    vi.restoreAllMocks()
  })

  function useBrowser(userAgent: string) {
    vi.spyOn(window.navigator, 'userAgent', 'get').mockReturnValue(userAgent)
  }

  it('opens the print dialog from a hidden frame on desktop Chrome', () => {
    useBrowser(DESKTOP_CHROME)

    printPdf(PDF_BASE64)

    const [frame] = printFrames()
    expect(frame.src).toBe('blob:pdf-1')
    const print = loadFrame(frame)
    expect(print).toHaveBeenCalledOnce()
    expect(openSpy).not.toHaveBeenCalled()
  })

  it('opens the PDF in a new tab on a phone, which cannot print from a frame', () => {
    useBrowser(ANDROID_CHROME)

    printPdf(PDF_BASE64)

    expect(printFrames()).toHaveLength(0)
    expect(openSpy).toHaveBeenCalledWith('blob:pdf-1', '_blank')
  })

  it('opens the PDF in a new tab on Safari', () => {
    useBrowser(DESKTOP_SAFARI)

    printPdf(PDF_BASE64)

    expect(printFrames()).toHaveLength(0)
    expect(openSpy).toHaveBeenCalledWith('blob:pdf-1', '_blank')
  })

  it('falls back to a new tab when the frame refuses to print', () => {
    useBrowser(DESKTOP_CHROME)

    printPdf(PDF_BASE64)
    loadFrame(printFrames()[0], () => {
      throw new DOMException('Blocked', 'SecurityError')
    })

    expect(openSpy).toHaveBeenCalledWith('blob:pdf-1', '_blank')
  })

  it('replaces the previous frame and frees its PDF on the next print', () => {
    useBrowser(DESKTOP_CHROME)

    printPdf(PDF_BASE64)
    // printPdf keeps its frame between calls, so an earlier test's frame
    // may be freed by the first call - only the second call is under test.
    vi.mocked(URL.revokeObjectURL).mockClear()
    printPdf(PDF_BASE64)

    const frames = printFrames()
    expect(frames).toHaveLength(1)
    expect(frames[0].src).toBe('blob:pdf-2')
    expect(URL.revokeObjectURL).toHaveBeenCalledWith('blob:pdf-1')
  })
})
