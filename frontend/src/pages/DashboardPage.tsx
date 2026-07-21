import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import {
  Package,
  AlertTriangle,
  TrendingDown,
  Bell,
  ArrowUpRight,
  ArrowDownRight,
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
} from 'recharts'

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Header } from '@/components/layout/Header'
import { formatCurrency, formatNumber, convertToDisplayCurrency } from '@/lib/utils'
import { dashboardApi, systemSettingsApi, type DashboardKPIs, type SystemSettings } from '@/lib/api'
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

export function DashboardPage() {
  const { t } = useTranslation()
  const { currency } = useUIStore()
  const [kpis, setKpis] = useState<DashboardKPIs | null>(null)
  const [riskData, setRiskData] = useState<any>(null)
  const [distribution, setDistribution] = useState<any[]>([])
  const [fxRates, setFxRates] = useState<SystemSettings | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    async function fetchData() {
      try {
        const [kpisRes, riskRes, distRes, fxRes] = await Promise.all([
          dashboardApi.getKpis(),
          dashboardApi.getExpirationRisk(),
          dashboardApi.getInventoryDistribution(),
          systemSettingsApi.get(),
        ])
        setKpis(kpisRes)
        setRiskData(riskRes)
        setDistribution(distRes.items || [])
        setFxRates(fxRes)
      } catch (error) {
        console.error('Failed to fetch dashboard data:', error)
      } finally {
        setLoading(false)
      }
    }
    fetchData()
  }, [])

  const inventoryValue = fxRates
    ? convertToDisplayCurrency(kpis?.inventory_value_by_currency ?? {}, currency, fxRates)
    : 0
  const atRiskValue = fxRates
    ? convertToDisplayCurrency(kpis?.at_risk_value_by_currency ?? {}, currency, fxRates)
    : 0

  // Each level's value is bucketed by currency (like inventory_value_by_currency) -
  // summing raw amounts across currencies without conversion would be
  // meaningless as soon as two items use different currencies.
  const riskChartData = riskData && fxRates ? [
    { name: t('dashboard.riskSafe'), value: convertToDisplayCurrency(riskData.risk_levels.safe.value_by_currency, currency, fxRates), color: RISK_COLORS.safe },
    { name: t('dashboard.riskCaution'), value: convertToDisplayCurrency(riskData.risk_levels.caution.value_by_currency, currency, fxRates), color: RISK_COLORS.caution },
    { name: t('dashboard.riskWarning'), value: convertToDisplayCurrency(riskData.risk_levels.warning.value_by_currency, currency, fxRates), color: RISK_COLORS.warning },
    { name: t('dashboard.riskCritical'), value: convertToDisplayCurrency(riskData.risk_levels.critical.value_by_currency, currency, fxRates), color: RISK_COLORS.critical },
    { name: t('dashboard.riskExpired'), value: convertToDisplayCurrency(riskData.risk_levels.expired.value_by_currency, currency, fxRates), color: RISK_COLORS.expired },
  ].filter(d => d.value > 0) : []

  const distributionChartData = distribution.slice(0, 8).map(item => ({
    name: item.sku,
    value: item.value,
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
          value={formatCurrency(inventoryValue, currency)}
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
                    <Tooltip
                      formatter={(value: number) => formatCurrency(value, currency)}
                      contentStyle={{ backgroundColor: 'hsl(var(--card))', border: '1px solid hsl(var(--border))', color: 'hsl(var(--foreground))', borderRadius: '0.5rem' }}
                    />
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
                    <XAxis type="number" tickFormatter={(value) => formatCurrency(value, currency)} stroke="hsl(var(--muted-foreground))" />
                    <YAxis type="category" dataKey="name" width={80} stroke="hsl(var(--muted-foreground))" />
                    <Tooltip
                      formatter={(value: number) => formatCurrency(value, currency)}
                      contentStyle={{ backgroundColor: 'hsl(var(--card))', border: '1px solid hsl(var(--border))', color: 'hsl(var(--foreground))', borderRadius: '0.5rem' }}
                    />
                    <Bar dataKey="value" fill="hsl(var(--primary))" radius={[0, 4, 4, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            ) : (
              <div className="h-64 flex items-center justify-center text-muted-foreground">
                {t('common.noData')}
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Quick Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
        <Card className="bg-status-safe/10 border-status-safe/30">
          <CardContent className="p-4 text-center">
            <p className="text-2xl font-bold text-status-safe">
              {formatNumber(kpis?.recent_receipts || 0)}
            </p>
            <p className="text-sm text-muted-foreground">{t('dashboard.recentReceipts')}</p>
          </CardContent>
        </Card>
        <Card className="bg-ink-cyan/10 border-ink-cyan/30">
          <CardContent className="p-4 text-center">
            <p className="text-2xl font-bold text-ink-cyan">
              {formatNumber(kpis?.recent_dispatches || 0)}
            </p>
            <p className="text-sm text-muted-foreground">{t('dashboard.recentDispatches')}</p>
          </CardContent>
        </Card>
        <Card className="bg-status-warning/10 border-status-warning/30">
          <CardContent className="p-4 text-center">
            <p className="text-2xl font-bold text-status-warning">
              {riskData?.risk_levels?.warning?.batches || 0}
            </p>
            <p className="text-sm text-muted-foreground">{t('dashboard.batchesWarning')}</p>
          </CardContent>
        </Card>
        <Card className="bg-status-critical/10 border-status-critical/30">
          <CardContent className="p-4 text-center">
            <p className="text-2xl font-bold text-status-critical">
              {riskData?.risk_levels?.critical?.batches || 0}
            </p>
            <p className="text-sm text-muted-foreground">{t('dashboard.batchesCritical')}</p>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}

