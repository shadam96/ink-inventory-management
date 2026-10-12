import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'

import { isRTL } from '@/i18n/config'
import { formatNumber } from '@/lib/utils'
import type { ExpiryBucketKey } from '@/lib/api'

export type DisplayCurrency = 'ILS' | 'USD' | 'EUR' | 'TRY'

// Expiration *state* colors - the same status palette the batches page
// uses, so a reader sees "red = critical" everywhere in the app. Reserved
// for expiry/stock state; never reused as a series color.
export const RISK_COLORS = {
  safe: '#10B981',
  caution: '#FBBF24',
  warning: '#F59E0B',
  critical: '#DC2626',
  expired: '#6B7280',
}

export const BUCKET_COLORS: Record<ExpiryBucketKey, string> = {
  expired: RISK_COLORS.expired,
  d0_30: RISK_COLORS.critical,
  d31_60: RISK_COLORS.warning,
  d61_90: RISK_COLORS.caution,
  d91_180: RISK_COLORS.safe,
  d181_plus: RISK_COLORS.safe,
}

// Status text needs more contrast than the status fills (amber text on
// white is unreadable), so text uses darker steps of the same hues.
export const STATUS_TEXT = {
  critical: 'text-red-600 dark:text-red-400',
  warning: 'text-amber-700 dark:text-amber-400',
}

// Matches Item.color (backend/app/models/item.py) - standard process-ink
// swatches, so a reader recognizes the ink itself at a glance.
export const ITEM_COLOR_HEX: Record<string, string> = {
  cyan: '#00AEEF',
  magenta: '#EC008C',
  yellow: '#FFE800',
  black: '#1A1A1A',
  white: '#FFFFFF',
  other: '#94A3B8',
}

export const AXIS_TICK = { fontSize: 12, fill: 'hsl(var(--muted-foreground))' }
export const AXIS_TICK_SMALL = { ...AXIS_TICK, fontSize: 11 }

/** Charts mirror in RTL so time and order read from the reading start. */
export function useChartRtl(): boolean {
  const { i18n } = useTranslation()
  return isRTL(i18n.language)
}

const NARROW_QUERY = '(max-width: 639px)'

/** True below Tailwind's `sm` breakpoint - charts drop their value axis
 * there (bars are labeled) to give the category labels room. */
export function useIsNarrow(): boolean {
  const [narrow, setNarrow] = useState(
    () => typeof window !== 'undefined' && !!window.matchMedia?.(NARROW_QUERY).matches
  )
  useEffect(() => {
    const media = window.matchMedia?.(NARROW_QUERY)
    if (!media) return
    const onChange = () => setNarrow(media.matches)
    media.addEventListener('change', onChange)
    return () => media.removeEventListener('change', onChange)
  }, [])
  return narrow
}

// Unicode first-strong isolate / pop directional isolate.
const FSI = String.fromCodePoint(0x2068)
const PDI = String.fromCodePoint(0x2069)

/**
 * Wraps text in a first-strong isolate so it keeps its own direction inside
 * the surrounding paragraph: Hebrew bidi otherwise reorders "15 KG" to
 * "KG 15", "0–30" to "30–0" and "4.7×" to "×4.7". A Hebrew unit
 * ("15 ליטר") still runs right-to-left, since the isolate takes its
 * direction from the first strong character.
 */
export function isolate(text: string): string {
  return `${FSI}${text}${PDI}`
}

export function formatQuantity(value: number, unit: string, decimals = 0): string {
  return isolate(`${formatNumber(value, decimals)} ${unit}`)
}
