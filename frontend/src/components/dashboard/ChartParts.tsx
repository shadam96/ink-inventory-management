import { useTranslation } from 'react-i18next'
import { Table2, BarChart3 } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { useChartRtl } from './chartUtils'

/** Chart containers are forced to dir="ltr" (recharts lays SVG text out
 * wrong under an RTL document), so the tooltip restores the reading direction. */
export function ChartTooltipFrame({ title, children }: { title: string; children: React.ReactNode }) {
  const rtl = useChartRtl()
  return (
    <div dir={rtl ? 'rtl' : 'ltr'} className="rounded-lg border bg-card px-3 py-2 text-card-foreground shadow-md">
      <p className="mb-1 text-sm font-medium">{title}</p>
      <div className="space-y-0.5 text-sm">{children}</div>
    </div>
  )
}

export function ViewToggle({ mode, onToggle }: { mode: 'chart' | 'table'; onToggle: () => void }) {
  const { t } = useTranslation()
  return (
    <Button variant="ghost" size="sm" className="h-8 px-2 text-muted-foreground" onClick={onToggle}>
      {mode === 'chart' ? <Table2 className="h-4 w-4 me-1.5" /> : <BarChart3 className="h-4 w-4 me-1.5" />}
      {mode === 'chart' ? t('dashboard.viewAsTable') : t('dashboard.viewAsChart')}
    </Button>
  )
}

export function SeriesSwatch({ color }: { color: string }) {
  return <span className="inline-block h-2.5 w-2.5 shrink-0 rounded-sm" style={{ backgroundColor: color }} />
}
