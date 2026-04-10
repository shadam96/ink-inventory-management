import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Package } from 'lucide-react'

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
import { Header } from '@/components/layout/Header'
import { SortableTableHead } from '@/components/SortableTableHead'
import { formatDate, formatNumber, daysUntilExpiration, getExpirationStatus } from '@/lib/utils'
import { batchesApi } from '@/lib/api'

interface Batch {
  id: string
  batch_number: string
  item_id: string
  item_sku?: string
  item_name?: string
  quantity_available: number
  quantity_received: number
  expiration_date: string
  receipt_date: string
  status: string
}

export function BatchesPage() {
  const { t } = useTranslation()
  const [batches, setBatches] = useState<Batch[]>([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState<string>('active')
  const [sortBy, setSortBy] = useState<string | null>(null)
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('asc')

  useEffect(() => {
    fetchBatches()
  }, [search, statusFilter, sortBy, sortOrder])

  const handleSort = (key: string) => {
    if (sortBy === key) {
      setSortOrder(prev => prev === 'asc' ? 'desc' : 'asc')
    } else {
      setSortBy(key)
      setSortOrder('asc')
    }
  }

  async function fetchBatches() {
    try {
      setLoading(true)
      const response = await batchesApi.list({
        status_filter: statusFilter === 'all' ? undefined : statusFilter,
        sort_by: sortBy || undefined,
        sort_order: sortBy ? sortOrder : undefined,
      })
      
      // Filter by search locally
      let filtered = response.items || []
      if (search) {
        filtered = filtered.filter((b: Batch) =>
          b.batch_number?.toLowerCase().includes(search.toLowerCase()) ||
          b.item_sku?.toLowerCase().includes(search.toLowerCase()) ||
          b.item_name?.toLowerCase().includes(search.toLowerCase())
        )
      }
      
      setBatches(filtered)
    } catch (error) {
      console.error('Failed to fetch batches:', error)
    } finally {
      setLoading(false)
    }
  }

  const getStatusBadge = (status: string) => {
    switch (status.toLowerCase()) {
      case 'active':
        return <Badge variant="safe">{t('batches.active')}</Badge>
      case 'depleted':
        return <Badge variant="secondary">{t('batches.depleted')}</Badge>
      case 'scrap':
        return <Badge variant="expired">{t('batches.scrap')}</Badge>
      default:
        return <Badge>{status}</Badge>
    }
  }

  const getExpirationBadge = (expirationDate: string) => {
    const days = daysUntilExpiration(expirationDate)
    const status = getExpirationStatus(days)
    
    if (days < 0) {
      return <Badge variant="expired">{t('batches.expired')}</Badge>
    }
    
    return (
      <Badge variant={status}>
        {days} {t('batches.daysUntilExpiration')}
      </Badge>
    )
  }

  return (
    <div className="space-y-6">
      <Header title={t('batches.title')} />

      <div className="flex items-center justify-between gap-4 relative z-10 -mt-2">
        <SearchInput
          value={search}
          onChange={setSearch}
          placeholder={t('batches.searchPlaceholder')}
          className="flex-1 max-w-md"
        />
        
        <div className="flex gap-2">
          <Button
            variant={statusFilter === 'active' ? 'default' : 'outline'}
            size="sm"
            onClick={() => setStatusFilter('active')}
          >
            {t('batches.active')}
          </Button>
          <Button
            variant={statusFilter === 'depleted' ? 'default' : 'outline'}
            size="sm"
            onClick={() => setStatusFilter('depleted')}
          >
            {t('batches.depleted')}
          </Button>
          <Button
            variant={statusFilter === 'scrap' ? 'default' : 'outline'}
            size="sm"
            onClick={() => setStatusFilter('scrap')}
          >
            {t('batches.scrap')}
          </Button>
          <Button
            variant={statusFilter === 'all' ? 'default' : 'outline'}
            size="sm"
            onClick={() => setStatusFilter('all')}
          >
            {t('common.all')}
          </Button>
        </div>
      </div>

      <Card>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <SortableTableHead sortKey="batch_number" currentSort={sortBy} currentOrder={sortOrder} onSort={handleSort}>{t('batches.batchNumber')}</SortableTableHead>
                <TableHead>{t('items.sku')}</TableHead>
                <TableHead>{t('items.name')}</TableHead>
                <SortableTableHead sortKey="quantity_available" currentSort={sortBy} currentOrder={sortOrder} onSort={handleSort} className="text-start">{t('batches.quantity')}</SortableTableHead>
                <SortableTableHead sortKey="receipt_date" currentSort={sortBy} currentOrder={sortOrder} onSort={handleSort}>{t('batches.receiptDate')}</SortableTableHead>
                <SortableTableHead sortKey="expiration_date" currentSort={sortBy} currentOrder={sortOrder} onSort={handleSort}>{t('batches.expirationDate')}</SortableTableHead>
                <SortableTableHead sortKey="status" currentSort={sortBy} currentOrder={sortOrder} onSort={handleSort}>{t('batches.status')}</SortableTableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {loading ? (
                <TableRow>
                  <TableCell colSpan={7} className="text-center py-8">
                    {t('common.loading')}
                  </TableCell>
                </TableRow>
              ) : batches.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={7} className="text-center py-8 text-muted-foreground">
                    <Package className="w-12 h-12 mx-auto mb-2 opacity-50" />
                    <p>{t('common.noData')}</p>
                  </TableCell>
                </TableRow>
              ) : (
                batches.map((batch) => (
                  <TableRow key={batch.id}>
                    <TableCell className="font-mono font-medium">
                      {batch.batch_number}
                    </TableCell>
                    <TableCell className="font-mono text-muted-foreground">
                      {batch.item_sku || '-'}
                    </TableCell>
                    <TableCell>{batch.item_name || '-'}</TableCell>
                    <TableCell className="text-start">
                      <div className="flex flex-col">
                        <span className="font-medium">
                          {formatNumber(batch.quantity_available)}
                        </span>
                        <span className="text-xs text-muted-foreground">
                          {t('batches.outOf', { total: formatNumber(batch.quantity_received) })}
                        </span>
                      </div>
                    </TableCell>
                    <TableCell>
                      {formatDate(batch.receipt_date)}
                    </TableCell>
                    <TableCell>
                      <div className="flex flex-col gap-1">
                        <span className="text-sm">{formatDate(batch.expiration_date)}</span>
                        {batch.status.toLowerCase() === 'active' && getExpirationBadge(batch.expiration_date)}
                      </div>
                    </TableCell>
                    <TableCell>
                      {getStatusBadge(batch.status)}
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {/* Summary */}
      <div className="grid grid-cols-4 gap-4">
        <Card>
          <CardContent className="p-4 text-center">
            <p className="text-2xl font-bold text-primary">
              {batches.filter(b => b.status.toLowerCase() === 'active').length}
            </p>
            <p className="text-sm text-muted-foreground">{t('batches.summaryActive')}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4 text-center">
            <p className="text-2xl font-bold text-status-critical">
              {batches.filter(b => {
                const days = daysUntilExpiration(b.expiration_date)
                return b.status.toLowerCase() === 'active' && days < 30
              }).length}
            </p>
            <p className="text-sm text-muted-foreground">{t('batches.summaryCritical')}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4 text-center">
            <p className="text-2xl font-bold text-status-warning">
              {batches.filter(b => {
                const days = daysUntilExpiration(b.expiration_date)
                return b.status.toLowerCase() === 'active' && days >= 30 && days < 60
              }).length}
            </p>
            <p className="text-sm text-muted-foreground">{t('batches.summaryWarning')}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4 text-center">
            <p className="text-2xl font-bold">
              {batches.reduce((sum, b) => sum + Number(b.quantity_available || 0), 0).toFixed(2)}
            </p>
            <p className="text-sm text-muted-foreground">{t('batches.summaryTotal')}</p>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}

