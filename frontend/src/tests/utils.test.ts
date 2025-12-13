import { describe, it, expect } from 'vitest'
import {
  formatDate,
  formatCurrency,
  formatNumber,
  daysUntilExpiration,
  getExpirationStatus,
} from '@/lib/utils'

describe('Utility Functions', () => {
  describe('formatDate', () => {
    it('should format ISO date to DD/MM/YYYY', () => {
      const result = formatDate('2024-12-13')
      expect(result).toMatch(/\d{2}\/\d{2}\/\d{4}/)
    })

    it('should handle empty string', () => {
      const result = formatDate('')
      expect(result).toBe('-')
    })
  })

  describe('formatCurrency', () => {
    it('should format number with ₪ symbol', () => {
      const result = formatCurrency(1234.56)
      expect(result).toContain('1,234.56')
      expect(result).toContain('₪')
    })

    it('should handle zero', () => {
      const result = formatCurrency(0)
      expect(result).toContain('0')
    })

    it('should handle large numbers', () => {
      const result = formatCurrency(1000000)
      expect(result).toContain('1,000,000')
    })
  })

  describe('formatNumber', () => {
    it('should format number with thousand separators', () => {
      const result = formatNumber(1234567.89)
      expect(result).toBe('1,234,567.89')
    })

    it('should limit to 2 decimal places', () => {
      const result = formatNumber(123.456789)
      expect(result).toBe('123.46')
    })
  })

  describe('daysUntilExpiration', () => {
    it('should calculate days until future date', () => {
      const futureDate = new Date()
      futureDate.setDate(futureDate.getDate() + 30)
      const result = daysUntilExpiration(futureDate.toISOString())
      expect(result).toBeGreaterThanOrEqual(29)
      expect(result).toBeLessThanOrEqual(31)
    })

    it('should return negative for past dates', () => {
      const pastDate = new Date()
      pastDate.setDate(pastDate.getDate() - 10)
      const result = daysUntilExpiration(pastDate.toISOString())
      expect(result).toBeLessThan(0)
    })
  })

  describe('getExpirationStatus', () => {
    it('should return "expired" for negative days', () => {
      expect(getExpirationStatus(-1)).toBe('expired')
    })

    it('should return "critical" for 0-29 days', () => {
      expect(getExpirationStatus(0)).toBe('critical')
      expect(getExpirationStatus(29)).toBe('critical')
    })

    it('should return "warning" for 30-59 days', () => {
      expect(getExpirationStatus(30)).toBe('warning')
      expect(getExpirationStatus(59)).toBe('warning')
    })

    it('should return "info" for 60-89 days', () => {
      expect(getExpirationStatus(60)).toBe('info')
      expect(getExpirationStatus(89)).toBe('info')
    })

    it('should return "safe" for 90+ days', () => {
      expect(getExpirationStatus(90)).toBe('safe')
      expect(getExpirationStatus(120)).toBe('safe')
    })
  })
})

