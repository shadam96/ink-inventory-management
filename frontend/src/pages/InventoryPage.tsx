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
import {
  formatCurrency,
  formatNumber,
  formatDate,
  daysUntilExpiration,
  getExpirationStatus,
} from '@/lib/utils'
import { inventoryApi, type InventoryRow, type InventoryTotalCost } from '@/lib/api'

export function InventoryPage() {
  const { t } = useTranslation()
  const [rows, setRows] = useState<InventoryRow[]>([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [page, setPage] = useState(1)
  const [total, setTotal] = useState(0)
  const [sortBy, setSortBy] = useState<string | null>(null)
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('asc')
  const [totalCost, setTotalCost] = useState<InventoryTotalCost['totals']>({})
  const pageSize = 20

  useEffect(() => {
    fetchInventory()
  }, [page, search, sortBy, sortOrder])

  useEffect(() => {
    fetchTotalCost()
  }, [search])

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
        search: search || undefined,
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

  async function fetchTotalCost() {
    try {
      const response = await inventoryApi.totalCost({
        search: search || undefined,
      })
      setTotalCost(response.totals || {})
    } catch (error) {
      console.error('Failed to fetch inventory total cost:', error)
      setTotalCost({})
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
          className="w-80"
        />
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
                  <SortableTableHead sortKey="quantity_available" currentSort={sortBy} currentOrder={sortOrder} onSort={handleSort} className="text-left">
                    {t('batches.quantity')}
                  </SortableTableHead>
                  <TableHead>{t('items.unit')}</TableHead>
                  <SortableTableHead sortKey="expiration_date" currentSort={sortBy} currentOrder={sortOrder} onSort={handleSort}>
                    {t('batches.expirationDate')}
                  </SortableTableHead>
                  <SortableTableHead sortKey="receipt_date" currentSort={sortBy} currentOrder={sortOrder} onSort={handleSort}>
                    {t('batches.receiptDate')}
                  </SortableTableHead>
                  <SortableTableHead sortKey="cost_price" currentSort={sortBy} currentOrder={sortOrder} onSort={handleSort} className="text-left">
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
                        <TableCell className="text-left font-mono">
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
                        <TableCell className="text-left font-mono">
                          {formatCurrency(row.cost_price, row.currency as 'ILS' | 'USD' | 'EUR')}
                        </TableCell>
                        <TableCell className="text-left font-mono font-medium">
                          {formatCurrency(
                            row.quantity_available * row.cost_price,
                            row.currency as 'ILS' | 'USD' | 'EUR'
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

      {Object.keys(totalCost).length > 0 && (
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-end gap-2 sm:gap-4">
          <span className="text-sm font-medium text-muted-foreground">
            {t('inventory.grandTotal')}:
          </span>
          <div className="flex flex-wrap items-center gap-3">
            {Object.entries(totalCost).map(([currency, value]) => (
              <span key={currency} className="font-mono font-semibold text-base">
                {formatCurrency(value, currency as 'ILS' | 'USD' | 'EUR')}
              </span>
            ))}
          </div>
        </div>
      )}

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
              הקודם
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setPage(p => Math.min(totalPages, p + 1))}
              disabled={page === totalPages}
            >
              הבא
            </Button>
          </div>
        </div>
      )}
    </div>
  )
}

function ReceiptDateCell({ dates }: { dates: string[] }) {
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
            <span className="text-muted-foreground text-xs mr-1">
              (+{dates.length - 1})
            </span>
          </span>
        </TooltipTrigger>
        <TooltipContent side="top">
          <div className="space-y-1">
            <p className="font-medium text-xs mb-1">תאריכי קבלה:</p>
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
  const variantMap: Record<string, 'safe' | 'warning' | 'critical' | 'expired' | 'secondary'> = {
    active: 'safe',
    expired: 'expired',
    scrap: 'critical',
    depleted: 'secondary',
  }

  const labelMap: Record<string, string> = {
    active: 'פעיל',
    expired: 'פג תוקף',
    scrap: 'גריטה',
    depleted: 'אזל',
  }

  return (
    <Badge variant={variantMap[status] || 'secondary'}>
      {labelMap[status] || status}
    </Badge>
  )
}
