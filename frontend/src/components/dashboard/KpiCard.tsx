import { Card, CardContent } from '@/components/ui/card'
import { cn } from '@/lib/utils'

export type KpiTone = 'default' | 'warning' | 'danger'

interface KpiCardProps {
  label: string
  value: string
  /** One line of context: a comparison, a breakdown or a target. */
  context?: React.ReactNode
  icon: React.ReactNode
  tone?: KpiTone
}

const ICON_TONE: Record<KpiTone, string> = {
  default: 'bg-primary/10 text-primary',
  warning: 'bg-status-warning/15 text-amber-700 dark:text-amber-400',
  danger: 'bg-status-critical/10 text-red-600 dark:text-red-400',
}

export function KpiCard({ label, value, context, icon, tone = 'default' }: KpiCardProps) {
  return (
    <Card className="h-full">
      <CardContent className="flex h-full flex-col p-4 sm:p-5">
        <div className="flex items-start justify-between gap-2">
          <p className="min-h-[2lh] text-xs font-medium leading-snug text-muted-foreground sm:min-h-0 sm:text-sm">{label}</p>
          <div className={cn('shrink-0 rounded-md p-1.5', ICON_TONE[tone])}>{icon}</div>
        </div>
        <p className="mt-1.5 text-2xl font-semibold tracking-tight sm:mt-2 sm:text-3xl">{value}</p>
        {context && <div className="mt-auto pt-1 text-xs text-muted-foreground sm:text-sm">{context}</div>}
      </CardContent>
    </Card>
  )
}
