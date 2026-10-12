import { useState } from 'react'
import { useTranslation } from 'react-i18next'

import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { cn } from '@/lib/utils'
import type { CoverageStatus, StockCoverage, StockCoverageItem } from '@/lib/api'
import { ITEM_COLOR_HEX, RISK_COLORS, STATUS_TEXT, formatQuantity } from './chartUtils'

const COLLAPSED_ROWS = 7

const BAR_COLOR: Record<CoverageStatus, string> = {
  out: RISK_COLORS.critical,
  below_min: RISK_COLORS.critical,
  below_reorder: RISK_COLORS.warning,
  ok: 'var(--chart-neutral)',
}

const STATUS_LABEL_KEY: Partial<Record<CoverageStatus, string>> = {
  out: 'dashboard.statusOut',
  below_min: 'dashboard.statusBelowMin',
  below_reorder: 'dashboard.statusBelowReorder',
}

/** Bars share one scale, capped so a single slow mover doesn't flatten the
 * rest - anything past the cap fills the track and keeps its true label. */
function scaleMax(items: StockCoverageItem[]): number {
  const longest = Math.max(0, ...items.map((item) => item.days_of_supply ?? 0))
  return Math.min(120, Math.max(30, Math.ceil(longest / 30) * 30))
}

function InkDot({ color }: { color: string }) {
  return (
    <span
      className="inline-block h-2.5 w-2.5 shrink-0 rounded-full ring-1 ring-black/15 dark:ring-white/30"
      style={{ backgroundColor: ITEM_COLOR_HEX[color] ?? ITEM_COLOR_HEX.other }}
    />
  )
}

function CoverageRow({ item, max }: { item: StockCoverageItem; max: number }) {
  const { t } = useTranslation()
  const days = item.days_of_supply ?? 0
  const statusKey = STATUS_LABEL_KEY[item.status]
  const statusClass = item.status === 'below_reorder' ? STATUS_TEXT.warning : STATUS_TEXT.critical

  // Phones stack name/days, a full-width bar, then the details; from `sm`
  // up the bar sits between them on one line.
  return (
    <li
      className={cn(
        'grid grid-cols-[minmax(0,1fr)_auto] gap-x-3 gap-y-1',
        "[grid-template-areas:'name_days'_'bar_bar'_'meta_status']",
        'sm:grid-cols-[minmax(0,11rem)_minmax(0,1fr)_7.5rem] sm:gap-y-0.5',
        "sm:[grid-template-areas:'name_bar_days'_'meta_bar_status']"
      )}
    >
      <div className="flex min-w-0 items-center gap-1.5 [grid-area:name]">
        <InkDot color={item.color} />
        <span className="truncate text-sm font-medium" title={item.name}>{item.name}</span>
      </div>
      <p className="truncate text-xs text-muted-foreground [grid-area:meta]">
        {formatQuantity(item.quantity, item.unit)}
        {' · '}
        {t('dashboard.perDay', { amount: formatQuantity(item.avg_daily_usage, item.unit, 1) })}
      </p>
      <div className="h-2.5 self-center overflow-hidden rounded-full bg-muted [grid-area:bar]">
        <div
          className="h-full rounded-e-full"
          style={{ width: `${Math.min(100, (days / max) * 100)}%`, backgroundColor: BAR_COLOR[item.status] }}
        />
      </div>
      <p className="text-end text-sm font-semibold tabular-nums [grid-area:days]">
        {t('dashboard.daysCount', { count: Math.round(days) })}
      </p>
      <p className={cn('text-end text-xs [grid-area:status]', statusClass)}>{statusKey ? t(statusKey) : ''}</p>
    </li>
  )
}

export function StockCoverageCard({ coverage }: { coverage: StockCoverage | null }) {
  const { t } = useTranslation()
  const [expanded, setExpanded] = useState(false)

  const items = coverage?.items ?? []
  const withDemand = items.filter((item) => item.days_of_supply !== null)
  const noDemand = items.filter((item) => item.days_of_supply === null)
  const visible = expanded ? withDemand : withDemand.slice(0, COLLAPSED_ROWS)
  const max = scaleMax(withDemand)

  return (
    <Card className="h-full">
      <CardHeader className="space-y-1 pb-3">
        <CardTitle className="text-lg">{t('dashboard.stockCoverage')}</CardTitle>
        <p className="text-sm text-muted-foreground">
          {t('dashboard.stockCoverageSubtitle', { days: coverage?.window_days ?? 90 })}
        </p>
      </CardHeader>
      <CardContent>
        {items.length === 0 ? (
          <div className="flex h-48 items-center justify-center text-muted-foreground">{t('common.noData')}</div>
        ) : (
          <>
            <ul className="space-y-3">
              {visible.map((item) => (
                <CoverageRow key={item.item_id} item={item} max={max} />
              ))}
            </ul>
            {withDemand.length > COLLAPSED_ROWS && (
              <Button variant="ghost" size="sm" className="mt-2 h-8 px-2 text-primary" onClick={() => setExpanded(!expanded)}>
                {expanded ? t('dashboard.showLess') : t('dashboard.showAll', { count: withDemand.length })}
              </Button>
            )}
            {noDemand.length > 0 && (
              <div className="mt-4 border-t pt-3">
                <p className="mb-2 text-xs text-muted-foreground">
                  {t('dashboard.noDemand', { days: coverage?.window_days ?? 90 })}
                </p>
                <div className="flex flex-wrap gap-1.5">
                  {noDemand.map((item) => (
                    <span
                      key={item.item_id}
                      className="inline-flex items-center gap-1.5 rounded-full border px-2 py-0.5 text-xs"
                      title={formatQuantity(item.quantity, item.unit)}
                    >
                      <InkDot color={item.color} />
                      {item.name}
                      <span className="text-muted-foreground tabular-nums">{formatQuantity(item.quantity, item.unit)}</span>
                    </span>
                  ))}
                </div>
              </div>
            )}
          </>
        )}
      </CardContent>
    </Card>
  )
}
