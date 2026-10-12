import { useTranslation } from 'react-i18next'
import { ArrowDown, ArrowUp, Clock, Package, RefreshCw, TrendingDown } from 'lucide-react'

import { Header } from '@/components/layout/Header'
import { KpiCard, type KpiTone } from '@/components/dashboard/KpiCard'
import { AttentionCard } from '@/components/dashboard/AttentionCard'
import { ExpiryTimelineCard } from '@/components/dashboard/ExpiryTimelineCard'
import { StockCoverageCard } from '@/components/dashboard/StockCoverageCard'
import { ActivityTrendCard } from '@/components/dashboard/ActivityTrendCard'
import { isolate } from '@/components/dashboard/chartUtils'
import { convertToDisplayCurrency, formatCurrencyShort, formatNumber } from '@/lib/utils'
import type { CurrencyTotals, ExpiryBucketKey } from '@/lib/api'
import { useDashboardData } from '@/hooks/useDashboardData'
import { useUIStore } from '@/store/ui'

function ValueDelta({ now, before }: { now: number; before: number }) {
  const { t } = useTranslation()
  if (before <= 0) return null
  const percent = ((now - before) / before) * 100
  if (Math.abs(percent) < 0.05) return <span>{t('dashboard.noChange30d')}</span>
  const Arrow = percent > 0 ? ArrowUp : ArrowDown
  return (
    <span className="inline-flex items-center gap-1">
      <Arrow className="h-3.5 w-3.5 shrink-0" />
      <span>
        {/* The sign must stay in its own LTR run - Hebrew bidi would
            otherwise move it to the wrong side of the digits. */}
        <span dir="ltr">{`${percent > 0 ? '+' : '−'}${formatNumber(Math.abs(percent), 1)}%`}</span>{' '}
        {t('dashboard.vs30dAgo')}
      </span>
    </span>
  )
}

export function DashboardPage() {
  const { t } = useTranslation()
  const { currency } = useUIStore()
  const {
    kpis,
    fxRates,
    expiryTimeline,
    stockCoverage,
    attention,
    movementTrend,
    trendDays,
    setTrendDays,
    loading,
    trendLoading,
  } = useDashboardData()

  const toDisplay = (amounts: CurrencyTotals | undefined) =>
    fxRates ? convertToDisplayCurrency(amounts ?? {}, currency, fxRates) : 0
  const money = (value: number) => formatCurrencyShort(value, currency)

  const bucket = (key: ExpiryBucketKey) => expiryTimeline?.buckets.find((b) => b.key === key)
  const expiringSoon = bucket('d0_30')
  const expired = bucket('expired')
  const expiringValue = toDisplay(expiringSoon?.value_by_currency)
  const expiredValue = toDisplay(expired?.value_by_currency)

  const inventoryNow = toDisplay(kpis?.inventory_value_by_currency)
  const inventoryBefore = toDisplay(kpis?.inventory_value_30d_ago_by_currency)

  const belowReorder = kpis?.low_stock_items ?? 0
  const belowMin = kpis?.critical_low_stock ?? 0
  const turnover = kpis?.turnover_annualized ?? 0

  const expiryTone: KpiTone = expiredValue > 0 ? 'danger' : expiringValue > 0 ? 'warning' : 'default'
  const stockTone: KpiTone = belowMin > 0 ? 'danger' : belowReorder > 0 ? 'warning' : 'default'

  if (loading) {
    return (
      <div className="flex items-center justify-center h-[calc(100vh-6rem)]">
        <div className="animate-pulse text-muted-foreground">{t('common.loading')}</div>
      </div>
    )
  }

  return (
    <div className="space-y-4 sm:space-y-6">
      <Header title={t('dashboard.title')} alertCount={kpis?.unread_alerts || 0} />

      <div className="grid grid-cols-2 gap-3 sm:gap-4 xl:grid-cols-4">
        <KpiCard
          label={t('dashboard.inventoryValue')}
          value={money(inventoryNow)}
          context={<ValueDelta now={inventoryNow} before={inventoryBefore} />}
          icon={<Package className="h-4 w-4" />}
        />
        <KpiCard
          label={t('dashboard.expiring30')}
          value={money(expiringValue)}
          context={
            <>
              {t('dashboard.batchesCount', { count: expiringSoon?.batches ?? 0 })}
              {expiredValue > 0 && <> · {t('dashboard.alreadyExpired', { value: money(expiredValue) })}</>}
            </>
          }
          icon={<Clock className="h-4 w-4" />}
          tone={expiryTone}
        />
        <KpiCard
          label={t('dashboard.belowReorder')}
          value={formatNumber(belowReorder)}
          context={belowReorder > 0 ? t('dashboard.belowMinCount', { count: belowMin }) : t('dashboard.allAboveReorder')}
          icon={<TrendingDown className="h-4 w-4" />}
          tone={stockTone}
        />
        <KpiCard
          label={t('dashboard.turnover')}
          value={turnover > 0 ? isolate(`${formatNumber(turnover, 1)}×`) : '—'}
          context={
            kpis?.days_on_hand != null
              ? t('dashboard.daysOnHand', { days: formatNumber(kpis.days_on_hand) })
              : t('dashboard.noOutbound')
          }
          icon={<RefreshCw className="h-4 w-4" />}
        />
      </div>

      <div className="grid grid-cols-1 gap-4 sm:gap-6 lg:grid-cols-5">
        <div className="lg:col-span-2">
          <AttentionCard attention={attention} />
        </div>
        <div className="lg:col-span-3">
          <ExpiryTimelineCard
            timeline={expiryTimeline}
            fxRates={fxRates}
            currency={currency}
            writeOffValue={toDisplay(kpis?.write_off_90d_value_by_currency)}
            writeOffRate={kpis?.write_off_90d_rate ?? 0}
          />
        </div>
      </div>

      {/* Side by side only from xl - at half a laptop's width the coverage
          bars get squeezed to stubs. */}
      <div className="grid grid-cols-1 gap-4 sm:gap-6 xl:grid-cols-2">
        <StockCoverageCard coverage={stockCoverage} />
        <ActivityTrendCard
          trend={movementTrend}
          fxRates={fxRates}
          currency={currency}
          trendDays={trendDays}
          onTrendDaysChange={setTrendDays}
          trendLoading={trendLoading}
        />
      </div>
    </div>
  )
}
