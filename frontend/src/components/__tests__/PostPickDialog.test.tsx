import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { PostPickDialog } from '../PostPickDialog'
import { pickingApi } from '@/lib/api'

vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
  }),
}))

vi.mock('@/lib/api', () => ({
  pickingApi: {
    generateDispatchDocument: vi.fn(),
  },
}))

const DESKTOP_CHROME =
  'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36'

describe('PostPickDialog', () => {
  beforeEach(() => {
    vi.spyOn(window.navigator, 'userAgent', 'get').mockReturnValue(DESKTOP_CHROME)
    Object.defineProperty(URL, 'createObjectURL', {
      configurable: true,
      writable: true,
      value: vi.fn(() => 'blob:pick-note'),
    })
    Object.defineProperty(URL, 'revokeObjectURL', {
      configurable: true,
      writable: true,
      value: vi.fn(),
    })
  })

  afterEach(() => {
    document.querySelectorAll('iframe').forEach((frame) => frame.remove())
    vi.restoreAllMocks()
  })

  it('sends the pick note to the print dialog when Print is clicked', async () => {
    vi.mocked(pickingApi.generateDispatchDocument).mockResolvedValue({
      success: true,
      document_type: 'pick_note',
      action: 'print',
      reference_number: 'DSP-261010-001',
      message: 'ok',
      pdf_base64: 'JVBERi0xLjQK',
    })
    const user = userEvent.setup()
    render(<PostPickDialog open onOpenChange={() => {}} referenceNumber="DSP-261010-001" />)

    // The pick note section comes first, so its Print button is the first.
    await user.click(screen.getAllByRole('button', { name: 'common.print' })[0])

    expect(pickingApi.generateDispatchDocument).toHaveBeenCalledWith(
      'DSP-261010-001',
      'pick_note',
      'print',
    )
    await waitFor(() => {
      expect(document.querySelector('iframe')?.src).toBe('blob:pick-note')
    })
  })
})
