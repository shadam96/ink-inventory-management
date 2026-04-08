import { type ClassValue, clsx } from "clsx"
import { twMerge } from "tailwind-merge"
import i18n from "@/i18n"
import { resolveLanguage } from "@/i18n/config"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

/** Current Intl locale tag derived from i18next. */
function currentIntlLocale(): string {
  return resolveLanguage(i18n.language).intlLocale
}

/**
 * Format a number using the current language's locale conventions
 * (thousands separator, decimal mark, digit grouping).
 */
export function formatNumber(value: number, decimals = 0): string {
  return new Intl.NumberFormat(currentIntlLocale(), {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  }).format(value)
}

/**
 * Format a currency amount using the current language's locale conventions.
 * The currency code is independent of language (a Hebrew user can display USD).
 */
export function formatCurrency(
  value: number,
  currency: 'ILS' | 'USD' | 'EUR' = 'ILS',
): string {
  return new Intl.NumberFormat(currentIntlLocale(), {
    style: 'currency',
    currency,
  }).format(value)
}

/**
 * Format a date as DD/MM/YYYY style appropriate to the current locale.
 */
export function formatDate(date: Date | string): string {
  const d = typeof date === 'string' ? new Date(date) : date
  return new Intl.DateTimeFormat(currentIntlLocale(), {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
  }).format(d)
}

/**
 * Calculate days until expiration
 */
export function daysUntilExpiration(expirationDate: Date | string): number {
  const exp = typeof expirationDate === 'string' ? new Date(expirationDate) : expirationDate
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  exp.setHours(0, 0, 0, 0)
  const diff = exp.getTime() - today.getTime()
  return Math.ceil(diff / (1000 * 60 * 60 * 24))
}

/**
 * Get expiration status color
 */
export function getExpirationStatus(days: number): 'safe' | 'warning' | 'critical' | 'expired' {
  if (days < 0) return 'expired'
  if (days <= 30) return 'critical'
  if (days <= 60) return 'warning'
  return 'safe'
}

/**
 * Generate a unique ID
 */
export function generateId(): string {
  return Math.random().toString(36).substring(2, 15)
}

