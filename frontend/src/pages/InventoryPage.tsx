import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'

import { Button } from '@/components/ui/button'
import { SearchInput } from '@/components/SearchInput'
import { Card, CardContent } from '@/components/ui/card'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { Badge } from '@/components/ui/badge'
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip'
import { Header } from '@/components/layout/Header'
import { SortableTableHead } from '@/components/SortableTableHead'
import { Package, Layers, Wallet } from 'lucide-react'
import {
  formatCurrency,
  formatNumber,
  formatDate,
  daysUntilExpiration,
  getExpirationStatus,
  convertAmount,
  convertToDisplayCurrency,
} from '@/lib/utils'
import {
  inventoryApi,
  systemSettingsApi,
  type InventoryRow,
  type InventoryTotalCost,
  type SystemSettings,
} from '@/lib/api'
import { useUIStore } from '@/store/ui'

export function InventoryPage() {
  const { t } = useTranslation()
  const { currency: displayCurrency } = useUIStore()
  const [rows, setRows] = useState<InventoryRow[]>([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  // SearchInput doesn't debounce internally — fire-and-hold the value for
  // a short window so we don't issue two requests per keystroke against
  // the heaviest list in the app.
  const [debouncedSearch, setDebouncedSearch] = useState('')
  const [page, setPage] = useState(1)
  const [total, setTotal] = useState(0)
  const [sortBy, setSortBy] = useState<string | null>(null)
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('asc')
  const [summary, setSummary] = useState<InventoryTotalCost>({ totals: {}, product_count: 0, total_quantity: 0 })
  const [fxRates, setFxRates] = useState<SystemSettings | null>(null)
  const pageSize = 20

  useEffect(() => {
    const id = setTimeout(() => setDebouncedSearch(search), 250)
    return () => clearTimeout(id)
  }, [search])

  useEffect(() => {
    systemSettingsApi.get().then(setFxRates).catch((e) => {
      console.error('Failed to fetch FX rates:', e)
    })
  }, [])

  useEffect(() => {
    fetchInventory()
  }, [page, debouncedSearch, sortBy, sortOrder])

  useEffect(() => {
    fetchSummary()
  }, [debouncedSearch])

  const handleSort = (key: string) => {
    if (sortBy === key) {
      setSortOrder(prev => (prev === 'asc' ? 'desc' : 'asc'))
    } else {
      setSortBy(key)
      setSortOrder('asc')
    }
    setPage(1)
  }

  async function fetchInventory() {
    try {
      setLoading(true)
      const response = await inventoryApi.list({
        page,
        page_size: pageSize,
        search: debouncedSearch || undefined,
        sort_by: sortBy || undefined,
        sort_order: sortBy ? sortOrder : undefined,
      })
      setRows(response.items)
      setTotal(response.total)
    } catch (error) {
      console.error('Failed to fetch inventory:', error)
    } finally {
      setLoading(false)
    }
  }

  async function fetchSummary() {
    try {
      const response = await inventoryApi.totalCost({
        search: debouncedSearch || undefined,
      })
      setSummary(response)
    } catch (error) {
      console.error('Failed to fetch inventory summary:', error)
      setSummary({ totals: {}, product_count: 0, total_quantity: 0 })
    }
  }

  const handleSearch = (value: string) => {
    setSearch(value)
    setPage(1)
  }

  const totalPages = Math.ceil(total / pageSize)

  return (
    <div className="space-y-6">
      <Header title={t('inventory.title')} />

      <div className="flex items-center justify-between relative z-10 -mt-2">
        <SearchInput
          value={search}
          onChange={handleSearch}
          placeholder={t('inventory.search')}
          className="w-full sm:w-80"
        />
      </div>

      <div className="flex justify-center">
        <Card className="w-full max-w-2xl">
          <CardContent className="p-4">
            <div className="grid grid-cols-3 divide-x rtl:divide-x-reverse divide-border">
              <div className="flex flex-col items-center gap-1 px-2">
                <Package className="w-5 h-5 text-primary" />
                <p className="text-2xl font-bold">{formatNumber(summary.product_count)}</p>
                <p className="text-sm text-muted-foreground">{t('inventory.summaryProducts')}</p>
              </div>
              <div className="flex flex-col items-center gap-1 px-2">
                <Layers className="w-5 h-5 text-primary" />
                <p className="text-2xl font-bold">{formatNumber(summary.total_quantity, 1)}</p>
                <p className="text-sm text-muted-foreground">{t('inventory.summaryQuantity')}</p>
              </div>
              <div className="flex flex-col items-center gap-1 px-2">
                <Wallet className="w-5 h-5 text-primary" />
                <p className="text-2xl font-bold font-mono">
                  {fxRates
                    ? formatCurrency(
                        convertToDisplayCurrency(
                          summary.totals as Partial<Record<'ILS' | 'USD' | 'EUR', number>>,
                          displayCurrency,
                          fxRates,
                        ),
                        displayCurrency,
                      )
                    : Object.entries(summary.totals)
                        .map(([currency, value]) =>
                          formatCurrency(value, currency as 'ILS' | 'USD' | 'EUR'),
                        )
                        .join(' + ') || formatCurrency(0, displayCurrency)}
                </p>
                <p className="text-sm text-muted-foreground">{t('inventory.summaryValue')}</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <SortableTableHead sortKey="sku" currentSort={sortBy} currentOrder={sortOrder} onSort={handleSort}>
                    {t('items.sku')}
                  </SortableTableHead>
                  <SortableTableHead sortKey="name" currentSort={sortBy} currentOrder={sortOrder} onSort={handleSort}>
                    {t('items.name')}
                  </SortableTableHead>
                  <SortableTableHead sortKey="batch_number" currentSort={sortBy} currentOrder={sortOrder} onSort={handleSort}>
                    {t('batches.batchNumber')}
                  </SortableTableHead>
                  <SortableTableHead sortKey="quantity_available" currentSort={sortBy} currentOrder={sortOrder} onSort={handleSort} className="text-start">
                    {t('batches.quantity')}
                  </SortableTableHead>
                  <TableHead>{t('items.unit')}</TableHead>
                  <SortableTableHead sortKey="expiration_date" currentSort={sortBy} currentOrder={sortOrder} onSort={handleSort}>
                    {t('batches.expirationDate')}
                  </SortableTableHead>
                  <SortableTableHead sortKey="receipt_date" currentSort={sortBy} currentOrder={sortOrder} onSort={handleSort}>
                    {t('batches.receiptDate')}
                  </SortableTableHead>
                  <SortableTableHead sortKey="cost_price" currentSort={sortBy} currentOrder={sortOrder} onSort={handleSort} className="text-start">
                    {t('items.costPrice')}
                  </SortableTableHead>
                  <TableHead className="text-left">{t('inventory.totalCost')}</TableHead>
                  <SortableTableHead sortKey="status" currentSort={sortBy} currentOrder={sortOrder} onSort={handleSort}>
                    {t('batches.status')}
                  </SortableTableHead>
                  <SortableTableHead sortKey="supplier" currentSort={sortBy} currentOrder={sortOrder} onSort={handleSort}>
                    {t('items.supplier')}
                  </SortableTableHead>
                  <TableHead>{t('items.description')}</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {loading ? (
                  <TableRow>
                    <TableCell colSpan={12} className="text-center py-8">
                      {t('common.loading')}
                    </TableCell>
                  </TableRow>
                ) : rows.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={12} className="text-center py-8 text-muted-foreground">
                      {t('common.noData')}
                    </TableCell>
                  </TableRow>
                ) : (
                  rows.map((row) => {
                    const days = daysUntilExpiration(row.expiration_date)
                    const expirationStatus = getExpirationStatus(days)

                    return (
                      <TableRow key={`${row.sku}-${row.batch_number}`}>
                        <TableCell className="font-mono font-medium">
                          {row.sku}
                        </TableCell>
                        <TableCell>{row.name}</TableCell>
                        <TableCell className="font-mono text-muted-foreground">
                          {row.batch_number}
                        </TableCell>
                        <TableCell className="text-start font-mono">
                          {formatNumber(row.quantity_available, 1)}
                        </TableCell>
                        <TableCell>
                          <Badge variant="secondary">{row.unit_of_measure}</Badge>
                        </TableCell>
                        <TableCell>
                          <Badge variant={expirationStatus}>
                            {formatDate(row.expiration_date)}
                          </Badge>
                        </TableCell>
                        <TableCell>
                          <ReceiptDateCell dates={row.receipt_dates} />
                        </TableCell>
                        <TableCell className="text-start font-mono">
                          {fxRates
                            ? formatCurrency(
                                convertAmount(
                                  row.cost_price,
                                  row.currency as 'ILS' | 'USD' | 'EUR',
                                  displayCurrency,
                                  fxRates,
                                ),
                                displayCurrency,
                              )
                            : formatCurrency(row.cost_price, row.currency as 'ILS' | 'USD' | 'EUR')}
                        </TableCell>
                        <TableCell className="text-left font-mono font-medium">
                          {fxRates
                            ? formatCurrency(
                                convertAmount(
                                  row.quantity_available * row.cost_price,
                                  row.currency as 'ILS' | 'USD' | 'EUR',
                                  displayCurrency,
                                  fxRates,
                                ),
                                displayCurrency,
                              )
                            : formatCurrency(
                                row.quantity_available * row.cost_price,
                                row.currency as 'ILS' | 'USD' | 'EUR',
                              )}
                        </TableCell>
                        <TableCell>
                          <StatusBadge status={row.status} />
                        </TableCell>
                        <TableCell className="text-muted-foreground">
                          {row.supplier}
                        </TableCell>
                        <TableCell className="max-w-[200px]">
                          {row.description ? (
                            <TooltipProvider>
                              <Tooltip>
                                <TooltipTrigger asChild>
                                  <span className="truncate block text-muted-foreground">
                                    {row.description}
                                  </span>
                                </TooltipTrigger>
                                <TooltipContent side="top" className="max-w-xs">
                                  {row.description}
                                </TooltipContent>
                              </Tooltip>
                            </TooltipProvider>
                          ) : (
                            <span className="text-muted-foreground/50">—</span>
                          )}
                        </TableCell>
                      </TableRow>
                    )
                  })
                )}
              </TableBody>
            </Table>
          </div>
        </CardContent>
      </Card>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between">
          <p className="text-sm text-muted-foreground">
            {t('common.page')} {page} {t('common.of')} {totalPages} ({total}{' '}
            {t('common.total')})
          </p>
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setPage(p => Math.max(1, p - 1))}
              disabled={page === 1}
            >
              {t('common.previous')}
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setPage(p => Math.min(totalPages, p + 1))}
              disabled={page === totalPages}
            >
              {t('common.next')}
            </Button>
          </div>
        </div>
      )}
    </div>
  )
}

function ReceiptDateCell({ dates }: { dates: string[] }) {
  const { t } = useTranslation()
  if (dates.length === 0) return <span className="text-muted-foreground/50">—</span>

  const formatted = dates.map(d => formatDate(d))

  if (dates.length === 1) {
    return <span>{formatted[0]}</span>
  }

  return (
    <TooltipProvider>
      <Tooltip>
        <TooltipTrigger asChild>
          <span className="underline decoration-dotted cursor-help">
            {formatted[0]}
            <span className="text-muted-foreground text-xs me-1">
              (+{dates.length - 1})
            </span>
          </span>
        </TooltipTrigger>
        <TooltipContent side="top">
          <div className="space-y-1">
            <p className="font-medium text-xs mb-1">{t('inventory.receiptDates')}</p>
            {formatted.map((d, i) => (
              <p key={i} className="text-xs">{d}</p>
            ))}
          </div>
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  )
}

function StatusBadge({ status }: { status: string }) {
  const { t } = useTranslation()
  const variantMap: Record<string, 'safe' | 'warning' | 'critical' | 'expired' | 'secondary'> = {
    active: 'safe',
    expired: 'expired',
    scrap: 'critical',
    depleted: 'secondary',
  }

  return (
    <Badge variant={variantMap[status] || 'secondary'}>
      {t(`batches.${status}`, status)}
    </Badge>
  )
}
