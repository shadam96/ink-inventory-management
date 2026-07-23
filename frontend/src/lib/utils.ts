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

export interface FxRates {
  /** Price of 1 USD in ILS. */
  usd_to_ils: number
  /** Price of 1 EUR in ILS. */
  eur_to_ils: number
}

/**
 * Convert a per-currency breakdown into a single amount in the display currency.
 * Rates are anchored to ILS — inputs are summed in ILS first, then converted to
 * the chosen display currency. Missing buckets are treated as zero.
 */
export function convertToDisplayCurrency(
  amounts: Partial<Record<'ILS' | 'USD' | 'EUR', number>>,
  displayCurrency: 'ILS' | 'USD' | 'EUR',
  rates: FxRates,
): number {
  const inIls =
    (amounts.ILS ?? 0) +
    (amounts.USD ?? 0) * rates.usd_to_ils +
    (amounts.EUR ?? 0) * rates.eur_to_ils

  switch (displayCurrency) {
    case 'ILS':
      return inIls
    case 'USD':
      return inIls / rates.usd_to_ils
    case 'EUR':
      return inIls / rates.eur_to_ils
  }
}

/** Convert a single amount from one currency to another via ILS-anchored rates. */
export function convertAmount(
  amount: number,
  from: 'ILS' | 'USD' | 'EUR',
  to: 'ILS' | 'USD' | 'EUR',
  rates: FxRates,
): number {
  if (from === to) return amount
  return convertToDisplayCurrency({ [from]: amount }, to, rates)
}

/**
 * Format a date as DD/MM/YYYY style appropriate to the current locale.
 */
export function formatDate(date: Date | string): string {
  const d = typeof date === 'string' ? new Date(date) : date
  if (Number.isNaN(d.getTime())) return '-'
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
  // A bare "YYYY-MM-DD" string (what date-only inputs and the backend's
  // `date` fields produce) is parsed by `new Date(string)` as UTC midnight,
  // then setHours below would re-zero it in the browser's LOCAL timezone -
  // shifting the calendar day back by one for any negative UTC offset.
  // Parsing the components directly constructs a local-midnight Date
  // instead, so the day never shifts regardless of timezone.
  const dateOnlyMatch =
    typeof expirationDate === 'string' ? expirationDate.match(/^(\d{4})-(\d{2})-(\d{2})$/) : null
  const exp = dateOnlyMatch
    ? new Date(Number(dateOnlyMatch[1]), Number(dateOnlyMatch[2]) - 1, Number(dateOnlyMatch[3]))
    : typeof expirationDate === 'string'
      ? new Date(expirationDate)
      : expirationDate
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

/**
 * Decode a base64-encoded PDF and open it in a new tab as a Blob URL -
 * avoids a bare `window.open` on an authenticated API response, and
 * doesn't require a second round-trip to a download endpoint.
 */
export function openPdfInNewTab(base64: string): void {
  const binary = atob(base64)
  const bytes = new Uint8Array(binary.length)
  for (let i = 0; i < binary.length; i++) {
    bytes[i] = binary.charCodeAt(i)
  }
  const blob = new Blob([bytes], { type: 'application/pdf' })
  const url = URL.createObjectURL(blob)
  window.open(url, '_blank')
  // Revoke after a delay rather than immediately - the new tab needs time
  // to actually load the blob URL before it's invalidated.
  setTimeout(() => URL.revokeObjectURL(url), 30_000)
}

