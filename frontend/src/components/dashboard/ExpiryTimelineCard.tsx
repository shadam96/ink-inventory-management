import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Bar, BarChart, CartesianGrid, Cell, LabelList, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { convertToDisplayCurrency, formatCurrencyShort, formatNumber } from '@/lib/utils'
import type { ExpiryBucketKey, ExpiryTimeline, SystemSettings } from '@/lib/api'
import {
  AXIS_TICK,
  AXIS_TICK_SMALL,
  BUCKET_COLORS,
  type DisplayCurrency,
  formatQuantity,
  isolate,
  useChartRtl,
  useIsNarrow,
} from './chartUtils'
import { ChartTooltipFrame, SeriesSwatch, ViewToggle } from './ChartParts'

const BUCKET_LABEL_KEY: Record<ExpiryBucketKey, string> = {
  expired: 'dashboard.bucketExpired',
  d0_30: 'dashboard.bucket0to30',
  d31_60: 'dashboard.bucket31to60',
  d61_90: 'dashboard.bucket61to90',
  d91_180: 'dashboard.bucket91to180',
  d181_plus: 'dashboard.bucket181plus',
}

interface BucketDatum {
  key: ExpiryBucketKey
  label: string
  value: number
  quantities: string
  batches: number
}

function formatQuantities(quantityByUnit: Record<string, number>): string {
  return Object.entries(quantityByUnit)
    .map(([unit, quantity]) => formatQuantity(quantity, unit))
    .join(' · ')
}

function BucketTooltip({ active, datum, currency }: { active?: boolean; datum?: BucketDatum; currency: DisplayCurrency }) {
  const { t } = useTranslation()
  if (!active || !datum) return null
  return (
    <ChartTooltipFrame title={datum.label}>
      <p className="font-medium">{formatCurrencyShort(datum.value, currency)}</p>
      {datum.quantities && <p className="text-muted-foreground">{datum.quantities}</p>}
      <p className="text-muted-foreground">{t('dashboard.batchesCount', { count: datum.batches })}</p>
    </ChartTooltipFrame>
  )
}

interface ExpiryTimelineCardProps {
  timeline: ExpiryTimeline | null
  fxRates: SystemSettings | null
  currency: DisplayCurrency
  writeOffValue: number
  writeOffRate: number
}

export function ExpiryTimelineCard({ timeline, fxRates, currency, writeOffValue, writeOffRate }: ExpiryTimelineCardProps) {
  const { t } = useTranslation()
  const rtl = useChartRtl()
  const narrow = useIsNarrow()
  const [mode, setMode] = useState<'chart' | 'table'>('chart')

  const data: BucketDatum[] = (timeline?.buckets ?? []).map((bucket) => ({
    key: bucket.key,
    // "0–30" has no strong direction - Hebrew bidi would flip it to "30–0".
    label: isolate(t(BUCKET_LABEL_KEY[bucket.key])),
    value: fxRates ? convertToDisplayCurrency(bucket.value_by_currency, currency, fxRates) : 0,
    quantities: formatQuantities(bucket.quantity_by_unit),
    batches: bucket.batches,
  }))
  const hasStock = data.some((d) => d.value > 0)

  return (
    <Card className="flex h-full flex-col">
      <CardHeader className="flex flex-row items-start justify-between gap-3 space-y-0 pb-2">
        <div className="space-y-1">
          <CardTitle className="text-lg">{t('dashboard.expiryTimeline')}</CardTitle>
          <p className="text-sm text-muted-foreground">{t('dashboard.expiryTimelineSubtitle')}</p>
        </div>
        <ViewToggle mode={mode} onToggle={() => setMode(mode === 'chart' ? 'table' : 'chart')} />
      </CardHeader>
      <CardContent className="flex flex-1 flex-col">
        {!hasStock ? (
          <div className="flex h-60 items-center justify-center text-muted-foreground sm:h-72">{t('common.noData')}</div>
        ) : mode === 'chart' ? (
          <div className="min-h-60 flex-1 sm:min-h-72" dir="ltr">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={data} margin={{ top: 24, right: 4, left: 4, bottom: 0 }} barCategoryGap="30%">
                <CartesianGrid vertical={false} stroke="hsl(var(--border))" />
                <XAxis
                  dataKey="label"
                  reversed={rtl}
                  interval={0}
                  tickLine={false}
                  axisLine={{ stroke: 'hsl(var(--border))' }}
                  tick={narrow ? AXIS_TICK_SMALL : AXIS_TICK}
                />
                {/* On phones the bar caps carry the values, so the value
                    axis gives its width to the category labels. */}
                <YAxis
                  hide={narrow}
                  orientation={rtl ? 'right' : 'left'}
                  width={56}
                  tickLine={false}
                  axisLine={false}
                  tick={AXIS_TICK}
                  tickFormatter={(value) => formatCurrencyShort(value, currency, { compact: true })}
                />
                <Tooltip
                  cursor={{ fill: 'hsl(var(--muted))', opacity: 0.6 }}
                  content={({ active, payload }) => (
                    <BucketTooltip active={active} datum={payload?.[0]?.payload as BucketDatum | undefined} currency={currency} />
                  )}
                />
                <Bar dataKey="value" maxBarSize={40} radius={[4, 4, 0, 0]} isAnimationActive={false}>
                  {data.map((d) => (
                    <Cell key={d.key} fill={BUCKET_COLORS[d.key]} />
                  ))}
                  <LabelList
                    dataKey="value"
                    position="top"
                    formatter={(value) =>
                      typeof value === 'number' && value > 0 ? formatCurrencyShort(value, currency, { compact: true }) : ''
                    }
                    style={{ fontSize: 12, fill: 'hsl(var(--foreground))' }}
                  />
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>{t('dashboard.tableExpiresIn')}</TableHead>
                <TableHead>{t('dashboard.tableValue')}</TableHead>
                <TableHead>{t('dashboard.tableQuantity')}</TableHead>
                <TableHead>{t('dashboard.tableBatches')}</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {data.map((d) => (
                <TableRow key={d.key}>
                  <TableCell>
                    <span className="flex items-center gap-2">
                      <SeriesSwatch color={BUCKET_COLORS[d.key]} />
                      {d.label}
                    </span>
                  </TableCell>
                  <TableCell className="tabular-nums">{formatCurrencyShort(d.value, currency)}</TableCell>
                  <TableCell className="tabular-nums">{d.quantities || '—'}</TableCell>
                  <TableCell className="tabular-nums">{formatNumber(d.batches)}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}

        <div className="mt-4 flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1 border-t pt-3 text-sm">
          <span className="text-muted-foreground">{t('dashboard.writeOff90d')}</span>
          <span>
            <span className="font-semibold">{formatCurrencyShort(writeOffValue, currency)}</span>
            <span className="text-muted-foreground">
              {' · '}
              {t('dashboard.writeOffRate', { rate: formatNumber(writeOffRate, 1) })}
            </span>
          </span>
        </div>
      </CardContent>
    </Card>
  )
}
