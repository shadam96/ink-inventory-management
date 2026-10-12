import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { format, parseISO } from 'date-fns'
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { getDateFnsLocale } from '@/lib/dateLocale'
import { cn, convertToDisplayCurrency, formatCurrencyShort } from '@/lib/utils'
import type { CurrencyTotals, MovementTrend, SystemSettings } from '@/lib/api'
import type { TrendRangeDays } from '@/hooks/useDashboardData'
import { AXIS_TICK, AXIS_TICK_SMALL, type DisplayCurrency, useChartRtl, useIsNarrow } from './chartUtils'
import { ChartTooltipFrame, SeriesSwatch, ViewToggle } from './ChartParts'

const SERIES = [
  { key: 'receipts', labelKey: 'dashboard.seriesReceipts', totalKey: 'dashboard.totalReceipts', color: 'var(--chart-receipts)' },
  { key: 'outbound', labelKey: 'dashboard.seriesOutbound', totalKey: 'dashboard.totalOutbound', color: 'var(--chart-outbound)' },
] as const

// Up to two weeks reads fine as daily bars; longer ranges are summed into
// 7-day periods so the bars stay legible on a phone.
const MAX_DAILY_POINTS = 14

interface Period {
  start: string
  end: string
  label: string
  rangeLabel: string
  receipts: number
  outbound: number
}

function toPeriods(trend: MovementTrend | null, convert: (amounts: CurrencyTotals) => number): Period[] {
  const locale = getDateFnsLocale()
  const short = (iso: string) => format(parseISO(iso), 'd MMM', { locale })
  const days = (trend?.series ?? []).map((point) => ({
    date: point.date,
    receipts: convert(point.receipts_value_by_currency ?? {}),
    outbound: convert(point.outbound_value_by_currency ?? {}),
  }))

  if (days.length <= MAX_DAILY_POINTS) {
    return days.map((day) => ({
      start: day.date,
      end: day.date,
      label: short(day.date),
      rangeLabel: format(parseISO(day.date), 'EEEE, d MMM', { locale }),
      receipts: day.receipts,
      outbound: day.outbound,
    }))
  }

  // Whole weeks counted back from today; a leading partial week is
  // dropped rather than drawn as a misleadingly short bar.
  const periods: Period[] = []
  for (let end = days.length; end - 7 >= 0; end -= 7) {
    const week = days.slice(end - 7, end)
    const first = week[0].date
    const last = week[week.length - 1].date
    periods.unshift({
      start: first,
      end: last,
      label: short(first),
      rangeLabel: `${short(first)} – ${short(last)}`,
      receipts: week.reduce((sum, day) => sum + day.receipts, 0),
      outbound: week.reduce((sum, day) => sum + day.outbound, 0),
    })
  }
  return periods
}

function TrendTooltip({ active, period, currency }: { active?: boolean; period?: Period; currency: DisplayCurrency }) {
  const { t } = useTranslation()
  if (!active || !period) return null
  return (
    <ChartTooltipFrame title={period.rangeLabel}>
      {SERIES.map((series) => (
        <p key={series.key} className="flex items-center gap-2">
          <SeriesSwatch color={series.color} />
          <span className="text-muted-foreground">{t(series.labelKey)}</span>
          <span className="ms-auto ps-3 font-medium tabular-nums">{formatCurrencyShort(period[series.key], currency)}</span>
        </p>
      ))}
    </ChartTooltipFrame>
  )
}

interface ActivityTrendCardProps {
  trend: MovementTrend | null
  fxRates: SystemSettings | null
  currency: DisplayCurrency
  trendDays: TrendRangeDays
  onTrendDaysChange: (days: TrendRangeDays) => void
  trendLoading: boolean
}

export function ActivityTrendCard({ trend, fxRates, currency, trendDays, onTrendDaysChange, trendLoading }: ActivityTrendCardProps) {
  const { t } = useTranslation()
  const rtl = useChartRtl()
  const narrow = useIsNarrow()
  const [mode, setMode] = useState<'chart' | 'table'>('chart')

  const convert = (amounts: CurrencyTotals) => (fxRates ? convertToDisplayCurrency(amounts, currency, fxRates) : 0)
  const periods = toPeriods(trend, convert)
  const totals = {
    receipts: periods.reduce((sum, p) => sum + p.receipts, 0),
    outbound: periods.reduce((sum, p) => sum + p.outbound, 0),
  }
  const hasActivity = totals.receipts > 0 || totals.outbound > 0

  return (
    <Card className="flex h-full flex-col">
      <CardHeader className="flex flex-row flex-wrap items-start justify-between gap-3 space-y-0 pb-2">
        <div className="space-y-1">
          <CardTitle className="text-lg">{t('dashboard.activityTrend')}</CardTitle>
          <p className="text-sm text-muted-foreground">{t('dashboard.activitySubtitle')}</p>
        </div>
        <div className="flex items-center gap-1">
          <Select value={String(trendDays)} onValueChange={(value) => onTrendDaysChange(Number(value) as TrendRangeDays)}>
            <SelectTrigger className="h-8 w-28">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="7">{t('dashboard.trendRange7')}</SelectItem>
              <SelectItem value="30">{t('dashboard.trendRange30')}</SelectItem>
              <SelectItem value="90">{t('dashboard.trendRange90')}</SelectItem>
            </SelectContent>
          </Select>
          <ViewToggle mode={mode} onToggle={() => setMode(mode === 'chart' ? 'table' : 'chart')} />
        </div>
      </CardHeader>
      <CardContent className={cn('flex flex-1 flex-col transition-opacity', trendLoading && 'opacity-50')}>
        <div className="mb-3 grid grid-cols-2 gap-3">
          {SERIES.map((series) => (
            <div key={series.key} className="rounded-lg bg-muted/50 px-3 py-2">
              <p className="flex items-center gap-1.5 text-xs text-muted-foreground">
                <SeriesSwatch color={series.color} />
                {t(series.totalKey)}
              </p>
              <p className="text-lg font-semibold">{formatCurrencyShort(totals[series.key], currency)}</p>
            </div>
          ))}
        </div>

        {!hasActivity ? (
          <div className="flex h-56 items-center justify-center text-muted-foreground sm:h-72">{t('common.noData')}</div>
        ) : mode === 'chart' ? (
          <div className="min-h-56 flex-1 sm:min-h-72" dir="ltr">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={periods} margin={{ top: 8, right: 4, left: 4, bottom: 0 }} barGap={2} barCategoryGap="25%">
                <CartesianGrid vertical={false} stroke="hsl(var(--border))" />
                <XAxis
                  dataKey="label"
                  reversed={rtl}
                  tickLine={false}
                  axisLine={{ stroke: 'hsl(var(--border))' }}
                  tick={narrow ? AXIS_TICK_SMALL : AXIS_TICK}
                  minTickGap={8}
                />
                <YAxis
                  orientation={rtl ? 'right' : 'left'}
                  width={narrow ? 44 : 56}
                  tickLine={false}
                  axisLine={false}
                  tick={narrow ? AXIS_TICK_SMALL : AXIS_TICK}
                  tickFormatter={(value) => formatCurrencyShort(value, currency, { compact: true })}
                />
                <Tooltip
                  cursor={{ fill: 'hsl(var(--muted))', opacity: 0.6 }}
                  content={({ active, payload }) => (
                    <TrendTooltip active={active} period={payload?.[0]?.payload as Period | undefined} currency={currency} />
                  )}
                />
                {SERIES.map((series) => (
                  <Bar
                    key={series.key}
                    dataKey={series.key}
                    name={t(series.labelKey)}
                    fill={series.color}
                    maxBarSize={16}
                    radius={[4, 4, 0, 0]}
                    isAnimationActive={false}
                  />
                ))}
              </BarChart>
            </ResponsiveContainer>
          </div>
        ) : (
          <div className="max-h-56 overflow-auto sm:max-h-72">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>{t('dashboard.tableDate')}</TableHead>
                  {SERIES.map((series) => (
                    <TableHead key={series.key}>{t(series.labelKey)}</TableHead>
                  ))}
                </TableRow>
              </TableHeader>
              <TableBody>
                {periods.map((period) => (
                  <TableRow key={period.start}>
                    <TableCell>{period.rangeLabel}</TableCell>
                    <TableCell className="tabular-nums">{formatCurrencyShort(period.receipts, currency)}</TableCell>
                    <TableCell className="tabular-nums">{formatCurrencyShort(period.outbound, currency)}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
