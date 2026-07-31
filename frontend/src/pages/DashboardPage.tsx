import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { format, parseISO } from 'date-fns'
import {
  Package,
  AlertTriangle,
  TrendingDown,
  Bell,
  ArrowUpRight,
  ArrowDownRight,
  Table2,
  LineChart as LineChartIcon,
} from 'lucide-react'
import {
  PieChart,
  Pie,
  Cell,
  ResponsiveContainer,
  Tooltip,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  LineChart,
  Line,
  AreaChart,
  Area,
} from 'recharts'

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import {
  Table,
  TableHeader,
  TableBody,
  TableRow,
  TableHead,
  TableCell,
} from '@/components/ui/table'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Header } from '@/components/layout/Header'
import { formatCurrency, formatNumber, convertToDisplayCurrency } from '@/lib/utils'
import { getDateFnsLocale } from '@/lib/dateLocale'
import type { InventoryValue, LowStockResponse, MovementTrend, SystemSettings } from '@/lib/api'
import { useDashboardData, type TrendRangeDays } from '@/hooks/useDashboardData'
import { useUIStore } from '@/store/ui'

interface KPICardProps {
  title: string
  value: string | number
  subtitle?: string
  icon: React.ReactNode
  trend?: 'up' | 'down' | null
  variant?: 'default' | 'warning' | 'danger'
}

function KPICard({ title, value, subtitle, icon, trend, variant = 'default' }: KPICardProps) {
  const variants = {
    default: 'border-s-4 border-s-primary',
    warning: 'border-s-4 border-s-status-warning',
    danger: 'border-s-4 border-s-status-critical',
  }

  return (
    <Card className={`${variants[variant]} card-hover`}>
      <CardContent className="p-6">
        <div className="flex items-start justify-between">
          <div className="space-y-1">
            <p className="text-sm text-muted-foreground">{title}</p>
            <p className="text-3xl font-bold">{value}</p>
            {subtitle && (
              <div className="flex items-center gap-1 text-sm text-muted-foreground">
                {trend === 'up' && <ArrowUpRight className="w-4 h-4 text-status-safe" />}
                {trend === 'down' && <ArrowDownRight className="w-4 h-4 text-status-critical" />}
                {subtitle}
              </div>
            )}
          </div>
          <div className="p-3 rounded-lg bg-primary/10 text-primary">
            {icon}
          </div>
        </div>
      </CardContent>
    </Card>
  )
}

const RISK_COLORS = {
  safe: '#10B981',
  caution: '#FBBF24',
  warning: '#F59E0B',
  critical: '#DC2626',
  expired: '#6B7280',
}

// Matches Item.color (backend/app/models/item.py) - standard process-ink
// swatches, not the app's generic theme colors, so a chart reader can
// recognize the ink itself at a glance.
const ITEM_COLOR_HEX: Record<string, string> = {
  cyan: '#00AEEF',
  magenta: '#EC008C',
  yellow: '#FFE800',
  black: '#000000',
  white: '#FFFFFF',
  other: 'hsl(var(--primary))',
}

// Fixed-order categorical colors for the three movement types. Deliberately
// distinct from both RISK_COLORS (reserved for expiration *state*) and
// ITEM_COLOR_HEX (reserved for physical ink identity), since this is a third,
// unrelated category axis appearing on the same page - reusing either of
// those palettes here would make a reader misread "this line is a status" or
// "this line is an ink color" instead of "this line is a movement type".
const MOVEMENT_COLORS: Record<'receipts' | 'dispatches' | 'scraps', string> = {
  receipts: '#3B82F6',
  dispatches: '#8B5CF6',
  scraps: '#64748B',
}

function DistributionTooltip({ active, payload, currency }: { active?: boolean; payload?: any[]; currency: 'ILS' | 'USD' | 'EUR' | 'TRY' }) {
  if (!active || !payload || payload.length === 0) return null
  const data = payload[0].payload
  return (
    <div style={{ backgroundColor: 'hsl(var(--card))', border: '1px solid hsl(var(--border))', color: 'hsl(var(--foreground))', borderRadius: '0.5rem', padding: '0.5rem 0.75rem' }}>
      <p className="font-medium">{data.name}</p>
      <p className="text-sm text-muted-foreground">{formatNumber(data.quantity)} {data.unit}</p>
      <p className="text-sm">{formatCurrency(data.value, currency)}</p>
    </div>
  )
}

function RiskTooltip({ active, payload }: { active?: boolean; payload?: any[] }) {
  const { t } = useTranslation()
  if (!active || !payload || payload.length === 0) return null
  const data = payload[0].payload
  return (
    <div style={{ backgroundColor: 'hsl(var(--card))', border: '1px solid hsl(var(--border))', color: 'hsl(var(--foreground))', borderRadius: '0.5rem', padding: '0.5rem 0.75rem' }}>
      <p className="font-medium">{data.name}</p>
      <p className="text-sm">{formatNumber(data.quantity)} {t('common.liter')}</p>
    </div>
  )
}

function TrendTooltip({ active, payload, label }: { active?: boolean; payload?: any[]; label?: string }) {
  if (!active || !payload || payload.length === 0) return null
  return (
    <div style={{ backgroundColor: 'hsl(var(--card))', border: '1px solid hsl(var(--border))', color: 'hsl(var(--foreground))', borderRadius: '0.5rem', padding: '0.5rem 0.75rem' }}>
      <p className="font-medium text-sm mb-1">{label}</p>
      {payload.map((entry) => (
        <p key={entry.dataKey} className="text-sm" style={{ color: entry.color }}>
          {entry.name}: {formatNumber(entry.value)}
        </p>
      ))}
    </div>
  )
}

function MiniSparkline({ data, dataKey, color }: { data: any[]; dataKey: string; color: string }) {
  return (
    <div className="h-8 mt-1">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={data}>
          <Area
            type="monotone"
            dataKey={dataKey}
            stroke={color}
            fill={color}
            fillOpacity={0.15}
            strokeWidth={1.5}
            isAnimationActive={false}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  )
}

const MOVEMENT_SERIES_KEYS = ['receipts', 'dispatches', 'scraps'] as const
const MOVEMENT_SERIES_LABEL_KEY: Record<(typeof MOVEMENT_SERIES_KEYS)[number], string> = {
  receipts: 'dashboard.seriesReceipts',
  dispatches: 'dashboard.seriesDispatches',
  scraps: 'dashboard.seriesScraps',
}
const MOVEMENT_SERIES_TOTAL_KEY: Record<(typeof MOVEMENT_SERIES_KEYS)[number], string> = {
  receipts: 'dashboard.totalReceipts',
  dispatches: 'dashboard.totalDispatches',
  scraps: 'dashboard.totalScraps',
}

function ActivityTrendCard({
  trend,
  trendDays,
  onTrendDaysChange,
  trendLoading,
}: {
  trend: MovementTrend | null
  trendDays: TrendRangeDays
  onTrendDaysChange: (days: TrendRangeDays) => void
  trendLoading: boolean
}) {
  const { t } = useTranslation()
  const [viewMode, setViewMode] = useState<'chart' | 'table'>('chart')
  const locale = getDateFnsLocale()

  const chartData = (trend?.series ?? []).map((point) => ({
    ...point,
    label: format(parseISO(point.date), 'MMM d', { locale }),
  }))

  const totals = chartData.reduce(
    (acc, point) => ({
      receipts: acc.receipts + point.receipts,
      dispatches: acc.dispatches + point.dispatches,
      scraps: acc.scraps + point.scraps,
    }),
    { receipts: 0, dispatches: 0, scraps: 0 }
  )

  return (
    <Card>
      <CardHeader className="flex flex-row flex-wrap items-center justify-between gap-3 space-y-0">
        <CardTitle className="text-lg">{t('dashboard.activityTrend')}</CardTitle>
        <div className="flex items-center gap-2">
          <Select
            value={String(trendDays)}
            onValueChange={(value) => onTrendDaysChange(Number(value) as TrendRangeDays)}
          >
            <SelectTrigger className="w-28 h-9">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="7">{t('dashboard.trendRange7')}</SelectItem>
              <SelectItem value="30">{t('dashboard.trendRange30')}</SelectItem>
              <SelectItem value="90">{t('dashboard.trendRange90')}</SelectItem>
            </SelectContent>
          </Select>
          <Button
            variant="outline"
            size="sm"
            onClick={() => setViewMode(viewMode === 'chart' ? 'table' : 'chart')}
          >
            {viewMode === 'chart' ? (
              <Table2 className="w-4 h-4 me-1.5" />
            ) : (
              <LineChartIcon className="w-4 h-4 me-1.5" />
            )}
            {viewMode === 'chart' ? t('dashboard.viewAsTable') : t('dashboard.viewAsChart')}
          </Button>
        </div>
      </CardHeader>
      <CardContent>
        {chartData.length === 0 ? (
          <div className="h-64 flex items-center justify-center text-muted-foreground">
            {t('common.noData')}
          </div>
        ) : viewMode === 'chart' ? (
          <>
            <div className={trendLoading ? 'h-64 opacity-50 transition-opacity' : 'h-64'}>
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={chartData} margin={{ top: 4, right: 8, left: 0, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="hsl(var(--border))" />
                  <XAxis dataKey="label" stroke="hsl(var(--muted-foreground))" tick={{ fontSize: 12 }} />
                  <YAxis stroke="hsl(var(--muted-foreground))" tick={{ fontSize: 12 }} tickFormatter={(value) => formatNumber(value)} />
                  <Tooltip content={(props: any) => <TrendTooltip {...props} />} />
                  {MOVEMENT_SERIES_KEYS.map((key) => (
                    <Line
                      key={key}
                      type="monotone"
                      dataKey={key}
                      name={t(MOVEMENT_SERIES_LABEL_KEY[key])}
                      stroke={MOVEMENT_COLORS[key]}
                      strokeWidth={2}
                      dot={false}
                    />
                  ))}
                </LineChart>
              </ResponsiveContainer>
            </div>
            <div className="flex flex-wrap justify-center gap-4 mt-3">
              {MOVEMENT_SERIES_KEYS.map((key) => (
                <div key={key} className="flex items-center gap-2">
                  <div className="w-3 h-3 rounded-full" style={{ backgroundColor: MOVEMENT_COLORS[key] }} />
                  <span className="text-sm">{t(MOVEMENT_SERIES_LABEL_KEY[key])}</span>
                </div>
              ))}
            </div>
          </>
        ) : (
          <div className="max-h-64 overflow-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>{t('dashboard.tableDate')}</TableHead>
                  {MOVEMENT_SERIES_KEYS.map((key) => (
                    <TableHead key={key}>{t(MOVEMENT_SERIES_LABEL_KEY[key])}</TableHead>
                  ))}
                </TableRow>
              </TableHeader>
              <TableBody>
                {chartData.map((point) => (
                  <TableRow key={point.date}>
                    <TableCell>{point.label}</TableCell>
                    <TableCell>{formatNumber(point.receipts)}</TableCell>
                    <TableCell>{formatNumber(point.dispatches)}</TableCell>
                    <TableCell>{formatNumber(point.scraps)}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        )}

        {chartData.length > 0 && (
          <div className="mt-4 pt-4 border-t grid grid-cols-1 sm:grid-cols-3 gap-2">
            {MOVEMENT_SERIES_KEYS.map((key) => (
              <div
                key={key}
                className="rounded-lg p-3"
                style={{ backgroundColor: `${MOVEMENT_COLORS[key]}1A`, border: `1px solid ${MOVEMENT_COLORS[key]}4D` }}
              >
                <p className="text-xl font-bold text-center" style={{ color: MOVEMENT_COLORS[key] }}>
                  {formatNumber(totals[key])}
                </p>
                <p className="text-xs text-muted-foreground text-center">{t(MOVEMENT_SERIES_TOTAL_KEY[key])}</p>
                <MiniSparkline data={chartData} dataKey={key} color={MOVEMENT_COLORS[key]} />
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  )
}

function LowStockCard({ lowStock }: { lowStock: LowStockResponse | null }) {
  const { t } = useTranslation()
  const items = (lowStock?.items ?? []).slice(0, 6)

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg">{t('dashboard.lowStock')}</CardTitle>
      </CardHeader>
      <CardContent>
        {items.length === 0 ? (
          <div className="h-48 flex items-center justify-center text-center text-muted-foreground text-sm px-4">
            {t('dashboard.noLowStockItems')}
          </div>
        ) : (
          <div className="space-y-4">
            {items.map((item) => {
              const percent = item.reorder_point > 0
                ? Math.min(100, (item.current_quantity / item.reorder_point) * 100)
                : 0
              const critical = item.is_critical
              return (
                <div key={item.item_id}>
                  <div className="flex items-center justify-between text-sm mb-1 gap-2">
                    <span className="font-medium truncate">{item.name}</span>
                    <span className={critical ? 'text-status-critical shrink-0' : 'text-status-warning shrink-0'}>
                      -{formatNumber(item.shortage)} {t('dashboard.shortage')}
                    </span>
                  </div>
                  <div className="h-2 rounded-full bg-muted overflow-hidden">
                    <div
                      className={critical ? 'h-full rounded-full bg-status-critical' : 'h-full rounded-full bg-status-warning'}
                      style={{ width: `${percent}%` }}
                    />
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </CardContent>
    </Card>
  )
}

function CurrencyBreakdownCard({
  inventoryValue,
  fxRates,
  currency,
}: {
  inventoryValue: InventoryValue | null
  fxRates: SystemSettings | null
  currency: 'ILS' | 'USD' | 'EUR' | 'TRY'
}) {
  const { t } = useTranslation()
  const totals = inventoryValue?.totals_by_currency ?? {}
  const entries = (Object.entries(totals) as ['ILS' | 'USD' | 'EUR' | 'TRY', number][])
    .filter(([, amount]) => amount > 0)
    .sort(([, a], [, b]) => b - a)

  const displayTotal = fxRates ? convertToDisplayCurrency(totals, currency, fxRates) : 0
  const displayAmounts = fxRates
    ? entries.map(([ccy, amount]) => convertToDisplayCurrency({ [ccy]: amount }, currency, fxRates))
    : []
  const maxDisplayAmount = displayAmounts.length > 0 ? Math.max(...displayAmounts) : 0

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg">{t('dashboard.currencyBreakdown')}</CardTitle>
      </CardHeader>
      <CardContent>
        <p className="text-3xl font-bold mb-4">{formatCurrency(displayTotal, currency)}</p>
        {entries.length === 0 ? (
          <div className="h-24 flex items-center justify-center text-muted-foreground">
            {t('common.noData')}
          </div>
        ) : (
          <div className="space-y-3">
            {entries.map(([ccy, amount], index) => {
              const displayAmount = displayAmounts[index]
              const percent = maxDisplayAmount > 0 ? (displayAmount / maxDisplayAmount) * 100 : 0
              return (
                <div key={ccy}>
                  <div className="flex items-center justify-between text-sm mb-1">
                    <span className="font-medium">{ccy}</span>
                    <span className="text-muted-foreground">{formatCurrency(amount, ccy)}</span>
                  </div>
                  <div className="h-2 rounded-full bg-muted overflow-hidden">
                    <div className="h-full rounded-full bg-primary" style={{ width: `${percent}%` }} />
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </CardContent>
    </Card>
  )
}

export function DashboardPage() {
  const { t } = useTranslation()
  const { currency } = useUIStore()
  const {
    kpis,
    riskData,
    distribution,
    fxRates,
    inventoryValue,
    lowStock,
    movementTrend,
    trendDays,
    setTrendDays,
    loading,
    trendLoading,
  } = useDashboardData()

  const inventoryValueDisplay = fxRates
    ? convertToDisplayCurrency(kpis?.inventory_value_by_currency ?? {}, currency, fxRates)
    : 0
  const atRiskValue = fxRates
    ? convertToDisplayCurrency(kpis?.at_risk_value_by_currency ?? {}, currency, fxRates)
    : 0

  // Slice size stays value-based (bucketed by currency, like
  // inventory_value_by_currency - summing raw amounts across currencies
  // without conversion would be meaningless). Only the hover tooltip shows
  // quantity instead, via each level's own `quantity` (already computed
  // server-side, no FX conversion needed for a physical unit).
  const riskChartData = riskData && fxRates ? [
    { name: t('dashboard.riskSafe'), value: convertToDisplayCurrency(riskData.risk_levels.safe.value_by_currency, currency, fxRates), quantity: riskData.risk_levels.safe.quantity, color: RISK_COLORS.safe },
    { name: t('dashboard.riskCaution'), value: convertToDisplayCurrency(riskData.risk_levels.caution.value_by_currency, currency, fxRates), quantity: riskData.risk_levels.caution.quantity, color: RISK_COLORS.caution },
    { name: t('dashboard.riskWarning'), value: convertToDisplayCurrency(riskData.risk_levels.warning.value_by_currency, currency, fxRates), quantity: riskData.risk_levels.warning.quantity, color: RISK_COLORS.warning },
    { name: t('dashboard.riskCritical'), value: convertToDisplayCurrency(riskData.risk_levels.critical.value_by_currency, currency, fxRates), quantity: riskData.risk_levels.critical.quantity, color: RISK_COLORS.critical },
    { name: t('dashboard.riskExpired'), value: convertToDisplayCurrency(riskData.risk_levels.expired.value_by_currency, currency, fxRates), quantity: riskData.risk_levels.expired.quantity, color: RISK_COLORS.expired },
  ].filter(d => d.value > 0) : []

  // Bar length/X-axis is quantity on hand (not price); the tooltip still
  // shows total value, so `value` is carried through for that lookup.
  const distributionChartData = distribution.slice(0, 8).map(item => ({
    name: item.sku,
    quantity: item.quantity,
    value: item.value,
    unit: item.unit,
    color: ITEM_COLOR_HEX[item.color] ?? ITEM_COLOR_HEX.other,
  }))

  if (loading) {
    return (
      <div className="flex items-center justify-center h-[calc(100vh-6rem)]">
        <div className="animate-pulse text-muted-foreground">
          {t('common.loading')}
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <Header title={t('dashboard.title')} alertCount={kpis?.unread_alerts || 0} />

      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-2">
        <KPICard
          title={t('dashboard.inventoryValue')}
          value={formatCurrency(inventoryValueDisplay, currency)}
          subtitle={t('dashboard.itemsCount', { count: kpis?.items_in_stock || 0 })}
          icon={<Package className="w-6 h-6" />}
        />
        <KPICard
          title={t('dashboard.atRisk')}
          value={formatCurrency(atRiskValue, currency)}
          subtitle={t('dashboard.percentOfInventory', { percent: kpis?.at_risk_percentage?.toFixed(1) || 0 })}
          icon={<AlertTriangle className="w-6 h-6" />}
          variant={kpis?.at_risk_percentage && kpis.at_risk_percentage > 20 ? 'danger' : 'warning'}
        />
        <KPICard
          title={t('dashboard.lowStock')}
          value={kpis?.low_stock_items || 0}
          subtitle={t('dashboard.criticalCount', { count: kpis?.critical_low_stock || 0 })}
          icon={<TrendingDown className="w-6 h-6" />}
          variant={kpis?.critical_low_stock && kpis.critical_low_stock > 0 ? 'danger' : 'default'}
        />
        <KPICard
          title={t('dashboard.unreadAlerts')}
          value={kpis?.unread_alerts || 0}
          icon={<Bell className="w-6 h-6" />}
          variant={kpis?.unread_alerts && kpis.unread_alerts > 5 ? 'warning' : 'default'}
        />
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Expiration Risk Chart */}
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">{t('dashboard.expirationRisk')}</CardTitle>
          </CardHeader>
          <CardContent>
            {riskChartData.length > 0 ? (
              <div className="h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={riskChartData}
                      cx="50%"
                      cy="50%"
                      innerRadius={60}
                      outerRadius={90}
                      paddingAngle={2}
                      dataKey="value"
                    >
                      {riskChartData.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={entry.color} />
                      ))}
                    </Pie>
                    <Tooltip content={(props: any) => <RiskTooltip {...props} />} />
                  </PieChart>
                </ResponsiveContainer>
                <div className="flex flex-wrap justify-center gap-4 mt-4">
                  {riskChartData.map((entry, index) => (
                    <div key={index} className="flex items-center gap-2">
                      <div
                        className="w-3 h-3 rounded-full"
                        style={{ backgroundColor: entry.color }}
                      />
                      <span className="text-sm">{entry.name}</span>
                    </div>
                  ))}
                </div>
              </div>
            ) : (
              <div className="h-64 flex items-center justify-center text-muted-foreground">
                {t('common.noData')}
              </div>
            )}

            {/* The chart above only shows currency value per slice - these
                are the batch counts behind the warning/critical slices. */}
            <div className="mt-4 pt-4 border-t">
              <p className="text-xs text-muted-foreground mb-2">{t('dashboard.riskFooterCaption')}</p>
              <div className="grid grid-cols-2 gap-2">
                <div className="rounded-lg p-3 text-center bg-status-warning/10 border border-status-warning/30">
                  <p className="text-xl font-bold text-status-warning">{riskData?.risk_levels?.warning?.batches || 0}</p>
                  <p className="text-xs text-muted-foreground">{t('dashboard.batchesWarning')}</p>
                </div>
                <div className="rounded-lg p-3 text-center bg-status-critical/10 border border-status-critical/30">
                  <p className="text-xl font-bold text-status-critical">{riskData?.risk_levels?.critical?.batches || 0}</p>
                  <p className="text-xs text-muted-foreground">{t('dashboard.batchesCritical')}</p>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Inventory Distribution Chart */}
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">{t('dashboard.inventoryDistribution')}</CardTitle>
          </CardHeader>
          <CardContent>
            {distributionChartData.length > 0 ? (
              <div className="h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={distributionChartData} layout="vertical">
                    <CartesianGrid strokeDasharray="3 3" horizontal={true} vertical={false} stroke="hsl(var(--border))" />
                    <XAxis type="number" tickFormatter={(value) => formatNumber(value)} stroke="hsl(var(--muted-foreground))" />
                    <YAxis type="category" dataKey="name" width={80} stroke="hsl(var(--muted-foreground))" />
                    <Tooltip
                      content={(props: any) => <DistributionTooltip {...props} currency={currency} />}
                      cursor={false}
                    />
                    <Bar
                      dataKey="quantity"
                      radius={[0, 4, 4, 0]}
                      activeBar={{ stroke: 'hsl(var(--foreground))', strokeWidth: 2 }}
                    >
                      {distributionChartData.map((entry, index) => (
                        <Cell
                          key={`cell-${index}`}
                          fill={entry.color}
                          stroke={entry.color === ITEM_COLOR_HEX.white ? 'hsl(var(--border))' : undefined}
                        />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
            ) : (
              <div className="h-64 flex items-center justify-center text-muted-foreground">
                {t('common.noData')}
              </div>
            )}

            {/* Recent movement activity behind this inventory snapshot. */}
            <div className="mt-4 pt-4 border-t">
              <p className="text-xs text-muted-foreground mb-2">{t('dashboard.distributionFooterCaption')}</p>
              <div className="grid grid-cols-2 gap-2">
                <div className="rounded-lg p-3 text-center bg-status-safe/10 border border-status-safe/30">
                  <p className="text-xl font-bold text-status-safe">{formatNumber(kpis?.recent_receipts || 0)}</p>
                  <p className="text-xs text-muted-foreground">{t('dashboard.recentReceipts')}</p>
                </div>
                <div className="rounded-lg p-3 text-center bg-ink-cyan/10 border border-ink-cyan/30">
                  <p className="text-xl font-bold text-ink-cyan">{formatNumber(kpis?.recent_dispatches || 0)}</p>
                  <p className="text-xs text-muted-foreground">{t('dashboard.recentDispatches')}</p>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Activity Trend - full width, its own range control */}
      <ActivityTrendCard
        trend={movementTrend}
        trendDays={trendDays}
        onTrendDaysChange={setTrendDays}
        trendLoading={trendLoading}
      />

      {/* Low Stock + Currency Breakdown */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <LowStockCard lowStock={lowStock} />
        <CurrencyBreakdownCard inventoryValue={inventoryValue} fxRates={fxRates} currency={currency} />
      </div>
    </div>
  )
}
