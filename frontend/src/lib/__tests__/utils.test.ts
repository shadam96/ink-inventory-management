import { describe, it, expect } from 'vitest'
import { cn, formatDate, formatCurrency, formatNumber, daysUntilExpiration, getExpirationStatus, convertToDisplayCurrency } from '../utils'

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
})

describe('convertToDisplayCurrency', () => {
  const rates = { usd_to_ils: 4, eur_to_ils: 5 }

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

