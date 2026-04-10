import * as React from 'react'
import { useTranslation } from 'react-i18next'
import {
  ChevronLeft,
  ChevronRight,
  ArrowLeft,
  ArrowRight,
  type LucideProps,
} from 'lucide-react'

/**
 * Direction-aware icon wrappers.
 *
 * `Start` and `End` are *logical* sides — they swap automatically
 * when the document direction changes.
 *
 *  - `<ChevronStart />` points toward the start of reading direction
 *    (left in LTR, right in RTL).
 *  - `<ChevronEnd />` points toward the end of reading direction
 *    (right in LTR, left in RTL).
 *
 * Use these for back/forward, prev/next, expand/collapse — anywhere
 * the icon's *meaning* is "previous content" or "next content"
 * rather than a fixed compass direction.
 */

function useIsRTL(): boolean {
  const { i18n } = useTranslation()
  return i18n.dir() === 'rtl'
}

export const ChevronStart = React.forwardRef<SVGSVGElement, LucideProps>(
  function ChevronStart(props, ref) {
    const Icon = useIsRTL() ? ChevronRight : ChevronLeft
    return <Icon ref={ref} {...props} />
  },
)

export const ChevronEnd = React.forwardRef<SVGSVGElement, LucideProps>(
  function ChevronEnd(props, ref) {
    const Icon = useIsRTL() ? ChevronLeft : ChevronRight
    return <Icon ref={ref} {...props} />
  },
)

export const ArrowStart = React.forwardRef<SVGSVGElement, LucideProps>(
  function ArrowStart(props, ref) {
    const Icon = useIsRTL() ? ArrowRight : ArrowLeft
    return <Icon ref={ref} {...props} />
  },
)

export const ArrowEnd = React.forwardRef<SVGSVGElement, LucideProps>(
  function ArrowEnd(props, ref) {
    const Icon = useIsRTL() ? ArrowLeft : ArrowRight
    return <Icon ref={ref} {...props} />
  },
)
