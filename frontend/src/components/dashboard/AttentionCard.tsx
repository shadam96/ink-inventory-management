import { Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { AlertOctagon, Archive, CheckCircle2, Clock, TrendingDown } from 'lucide-react'

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { ChevronEnd } from '@/components/ui/DirectionalIcon'
import { cn, formatCurrencyShort, formatNumber } from '@/lib/utils'
import type { AttentionItems, AttentionLot } from '@/lib/api'
import { STATUS_TEXT, formatQuantity, isolate } from './chartUtils'

const ROWS_PER_GROUP = 3

interface Row {
  key: string
  title: string
  detail: string
  amount: string
  note: string
  noteClass: string
}

interface Group {
  key: string
  title: string
  icon: React.ReactNode
  rows: Row[]
  href: string
}

function AttentionRow({ row, href }: { row: Row; href: string }) {
  return (
    <li>
      <Link
        to={href}
        className="flex items-center gap-3 rounded-md px-2 py-1.5 transition-colors hover:bg-muted/60"
      >
        <div className="min-w-0 flex-1">
          <p className="truncate text-sm font-medium">{row.title}</p>
          <p className="truncate text-xs text-muted-foreground">{row.detail}</p>
        </div>
        <div className="shrink-0 text-end">
          <p className="text-sm font-medium tabular-nums">{row.amount}</p>
          <p className={cn('text-xs', row.noteClass)}>{row.note}</p>
        </div>
      </Link>
    </li>
  )
}

export function AttentionCard({ attention }: { attention: AttentionItems | null }) {
  const { t } = useTranslation()

  const lotRow = (lot: AttentionLot, note: string, noteClass: string): Row => ({
    key: lot.batch_id,
    title: lot.name,
    detail: [lot.batch_number, lot.location_code].filter(Boolean).join(' · '),
    amount: formatQuantity(lot.quantity, lot.unit),
    note,
    noteClass,
  })

  const groups: Group[] = attention
    ? [
        {
          key: 'expired',
          title: t('dashboard.attentionExpired'),
          icon: <AlertOctagon className={cn('h-4 w-4', STATUS_TEXT.critical)} />,
          href: '/batches',
          rows: attention.expired_on_shelf.map((lot) =>
            lotRow(lot, t('dashboard.expiredDaysAgo', { count: -lot.days_until_expiration }), STATUS_TEXT.critical)
          ),
        },
        {
          key: 'expiring',
          title: t('dashboard.attentionExpiring'),
          icon: <Clock className={cn('h-4 w-4', STATUS_TEXT.warning)} />,
          href: '/batches',
          rows: attention.expiring_soon.map((lot) =>
            lotRow(
              lot,
              lot.days_until_expiration === 0
                ? t('dashboard.expiresToday')
                : t('dashboard.expiresInDays', { count: lot.days_until_expiration }),
              lot.days_until_expiration <= 7 ? STATUS_TEXT.critical : STATUS_TEXT.warning
            )
          ),
        },
        {
          key: 'below-min',
          title: t('dashboard.attentionBelowMin'),
          icon: <TrendingDown className={cn('h-4 w-4', STATUS_TEXT.critical)} />,
          href: '/items',
          rows: attention.below_min.map((item) => ({
            key: item.item_id,
            title: item.name,
            detail: item.sku,
            amount: isolate(`${formatNumber(item.quantity)} / ${formatNumber(item.min_stock)} ${item.unit}`),
            note: item.quantity === 0 ? t('dashboard.statusOut') : t('dashboard.statusBelowMin'),
            noteClass: STATUS_TEXT.critical,
          })),
        },
        {
          key: 'dead',
          title: t('dashboard.attentionDeadStock'),
          icon: <Archive className="h-4 w-4 text-muted-foreground" />,
          href: '/items',
          rows: attention.dead_stock.map((item) => ({
            key: item.item_id,
            title: item.name,
            detail: item.sku,
            amount: formatCurrencyShort(item.value, item.currency),
            note: t('dashboard.inactiveDays', { count: item.days_inactive }),
            noteClass: 'text-muted-foreground',
          })),
        },
      ].filter((group) => group.rows.length > 0)
    : []

  const total = groups.reduce((sum, group) => sum + group.rows.length, 0)

  return (
    <Card className="h-full">
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-3">
        <CardTitle className="text-lg">{t('dashboard.attention')}</CardTitle>
        {total > 0 && (
          <span className="rounded-full bg-muted px-2.5 py-0.5 text-xs font-medium tabular-nums text-muted-foreground">
            {formatNumber(total)}
          </span>
        )}
      </CardHeader>
      <CardContent>
        {groups.length === 0 ? (
          <div className="flex h-48 flex-col items-center justify-center gap-2 text-center text-sm text-muted-foreground">
            <CheckCircle2 className="h-8 w-8 text-status-safe" />
            {t('dashboard.nothingNeedsAttention')}
          </div>
        ) : (
          <div className="space-y-4">
            {groups.map((group) => (
              <section key={group.key}>
                <div className="mb-1 flex items-center gap-2 px-2">
                  {group.icon}
                  <h4 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                    {group.title}
                  </h4>
                  <span className="text-xs tabular-nums text-muted-foreground">({formatNumber(group.rows.length)})</span>
                </div>
                <ul>
                  {group.rows.slice(0, ROWS_PER_GROUP).map((row) => (
                    <AttentionRow key={row.key} row={row} href={group.href} />
                  ))}
                </ul>
                {group.rows.length > ROWS_PER_GROUP && (
                  <Link
                    to={group.href}
                    className="mt-0.5 flex items-center gap-1 px-2 text-xs font-medium text-primary hover:underline"
                  >
                    {t('dashboard.moreCount', { count: group.rows.length - ROWS_PER_GROUP })}
                    <ChevronEnd className="h-3 w-3" />
                  </Link>
                )}
              </section>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  )
}
