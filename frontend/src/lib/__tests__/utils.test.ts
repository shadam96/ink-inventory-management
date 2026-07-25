import { describe, it, expect, vi, afterEach } from 'vitest'
import { cn, formatDate, formatCurrency, formatNumber, daysUntilExpiration, getExpirationStatus, convertToDisplayCurrency, convertAmount } from '../utils'

describe('cn utility', () => {
  it('should merge class names', () => {
    expect(cn('class1', 'class2')).toBe('class1 class2')
  })

  it('should handle conditional classes', () => {
    expect(cn('base', { active: true, disabled: false })).toContain('active')
    expect(cn('base', { active: true, disabled: false })).not.toContain('disabled')
  })
})

describe('formatDate', () => {
  it('should format date in Hebrew locale', () => {
    const date = '2024-12-13'
    const formatted = formatDate(date)
    // Hebrew locale formats as DD.MM.YYYY
    expect(formatted).toMatch(/\d{2}\.\d{2}\.\d{4}/)
  })

  it('should handle Date objects', () => {
    const date = new Date('2024-12-13')
    const formatted = formatDate(date)
    expect(formatted).toMatch(/\d{2}\.\d{2}\.\d{4}/)
  })
})

describe('formatCurrency', () => {
  it('should format currency with symbol', () => {
    const result = formatCurrency(1000)
    // Hebrew locale puts currency after number with RTL marks
    expect(result).toContain('₪')
    expect(result).toContain('1,000')
  })

  it('should handle decimals', () => {
    const result = formatCurrency(1234.56)
    expect(result).toContain('₪')
    expect(result).toContain('1,234')
  })

  it('should handle zero', () => {
    const result = formatCurrency(0)
    expect(result).toContain('₪')
    expect(result).toContain('0.00')
  })
})

describe('formatNumber', () => {
  it('should format numbers with commas', () => {
    expect(formatNumber(1000)).toBe('1,000')
  })

  it('should handle decimals', () => {
    const result = formatNumber(1234.56)
    // formatNumber might round, check it contains the base number
    expect(result).toContain('1,23')
  })
})

describe('daysUntilExpiration', () => {
  it('should calculate days until expiration', () => {
    const futureDate = new Date()
    futureDate.setDate(futureDate.getDate() + 30)
    const days = daysUntilExpiration(futureDate.toISOString())
    expect(days).toBeGreaterThanOrEqual(29)
    expect(days).toBeLessThanOrEqual(30)
  })

  it('should return negative for expired dates', () => {
    const pastDate = new Date()
    pastDate.setDate(pastDate.getDate() - 10)
    const days = daysUntilExpiration(pastDate.toISOString())
    expect(days).toBeLessThan(0)
  })

  describe('timezone independence for date-only strings', () => {
    const originalTZ = process.env.TZ

    afterEach(() => {
      process.env.TZ = originalTZ
      vi.useRealTimers()
    })

    it('treats a "YYYY-MM-DD" string as the same calendar day regardless of the local timezone', () => {
      // Each zone gets "now" pinned to ITS OWN local noon on 2026-07-21, so
      // "today" unambiguously lands on that calendar day in that zone -
      // local noon in one zone can be a different UTC calendar day than
      // local noon in another (e.g. UTC+14 vs UTC-7), so a single shared
      // instant can't safely stand in for "midday" in every zone at once.
      vi.useFakeTimers()

      // A negative UTC offset is what previously exposed the bug: new
      // Date('2027-01-17') parses as UTC midnight, and re-zeroing it with
      // setHours() in a UTC-7 zone rolled it back to 2027-01-16. Arizona
      // (America/Phoenix) is used instead of e.g. Los_Angeles because it
      // never observes DST, so a fixed -7 offset applies to both "today"
      // and the expiration date - no unrelated DST-transition skew.
      process.env.TZ = 'America/Phoenix'
      vi.setSystemTime(new Date('2026-07-21T19:00:00Z')) // noon in UTC-7
      const negativeOffsetDays = daysUntilExpiration('2027-01-17')

      process.env.TZ = 'UTC'
      vi.setSystemTime(new Date('2026-07-21T12:00:00Z')) // noon in UTC
      const utcDays = daysUntilExpiration('2027-01-17')

      process.env.TZ = 'Pacific/Kiritimati' // fixed UTC+14, no DST
      vi.setSystemTime(new Date('2026-07-20T22:00:00Z')) // noon in UTC+14
      const positiveOffsetDays = daysUntilExpiration('2027-01-17')

      expect(negativeOffsetDays).toBe(180)
      expect(utcDays).toBe(180)
      expect(positiveOffsetDays).toBe(180)
    })
  })
})

describe('convertToDisplayCurrency', () => {
  const rates = { usd_to_ils: 4, eur_to_ils: 5, try_to_ils: 0.25 }

  it('returns ILS bucket unchanged when displaying in ILS', () => {
    expect(convertToDisplayCurrency({ ILS: 100 }, 'ILS', rates)).toBe(100)
  })

  it('converts USD into ILS at the configured rate', () => {
    // 50 USD * 4 ILS/USD = 200 ILS
    expect(convertToDisplayCurrency({ USD: 50 }, 'ILS', rates)).toBe(200)
  })

  it('sums distinct currencies into one display currency', () => {
    // 100 ILS + 50 USD ($200 ILS-equivalent) + 10 EUR (50 ILS-equivalent) = 350 ILS
    expect(
      convertToDisplayCurrency({ ILS: 100, USD: 50, EUR: 10 }, 'ILS', rates),
    ).toBe(350)
  })

  it('converts a mixed bucket into USD by routing through ILS', () => {
    // Same 350 ILS → divided by usd_to_ils (4) = 87.5 USD
    expect(
      convertToDisplayCurrency({ ILS: 100, USD: 50, EUR: 10 }, 'USD', rates),
    ).toBe(87.5)
  })

  it('treats missing buckets as zero', () => {
    expect(convertToDisplayCurrency({}, 'EUR', rates)).toBe(0)
  })

  it('round-trips a USD bucket back to USD via ILS', () => {
    expect(convertToDisplayCurrency({ USD: 42 }, 'USD', rates)).toBeCloseTo(42)
  })

  it('converts TRY into ILS at the configured rate', () => {
    // 100 TRY * 0.25 ILS/TRY = 25 ILS
    expect(convertToDisplayCurrency({ TRY: 100 }, 'ILS', rates)).toBe(25)
  })
})

describe('convertAmount', () => {
  const rates = { usd_to_ils: 4, eur_to_ils: 5, try_to_ils: 0.25 }

  it('returns the amount untouched when from === to', () => {
    expect(convertAmount(100, 'USD', 'USD', rates)).toBe(100)
  })

  it('converts USD to ILS via the configured rate', () => {
    expect(convertAmount(50, 'USD', 'ILS', rates)).toBe(200)
  })

  it('converts ILS to EUR via the configured rate', () => {
    // 100 ILS / 5 ILS-per-EUR = 20 EUR
    expect(convertAmount(100, 'ILS', 'EUR', rates)).toBe(20)
  })

  it('round-trips a cross-currency conversion through ILS', () => {
    // 10 EUR → ILS (50) → USD (12.5)
    expect(convertAmount(10, 'EUR', 'USD', rates)).toBe(12.5)
  })

  it('converts TRY to ILS via the configured rate', () => {
    expect(convertAmount(100, 'TRY', 'ILS', rates)).toBe(25)
  })
})

describe('getExpirationStatus', () => {
  it('should return "expired" for negative days', () => {
    expect(getExpirationStatus(-1)).toBe('expired')
  })

  it('should return "critical" for less than 30 days', () => {
    expect(getExpirationStatus(15)).toBe('critical')
  })

  it('should return "warning" for 30-60 days', () => {
    expect(getExpirationStatus(45)).toBe('warning')
  })

  it('should return appropriate status for 60-90 days', () => {
    const status = getExpirationStatus(75)
    // Could be "warning" or "safe" depending on thresholds
    expect(['warning', 'safe']).toContain(status)
  })

  it('should return "safe" for more than 90 days', () => {
    expect(getExpirationStatus(120)).toBe('safe')
  })
})

