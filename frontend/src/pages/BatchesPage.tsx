import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Package, Search } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
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

  useEffect(() => {
    fetchBatches()
  }, [search, statusFilter])

  async function fetchBatches() {
    try {
      setLoading(true)
      const response = await batchesApi.list({
        status: statusFilter === 'all' ? undefined : statusFilter,
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

      <div className="flex items-center justify-between mt-16 gap-4">
        <div className="relative flex-1 max-w-md">
          <Search className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
          <Input
            placeholder="חיפוש אצוות..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pr-10"
          />
        </div>
        
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
            הכל
          </Button>
        </div>
      </div>

      <Card>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>{t('batches.batchNumber')}</TableHead>
                <TableHead>{t('items.sku')}</TableHead>
                <TableHead>{t('items.name')}</TableHead>
                <TableHead className="text-left">{t('batches.quantity')}</TableHead>
                <TableHead>{t('batches.receiptDate')}</TableHead>
                <TableHead>{t('batches.expirationDate')}</TableHead>
                <TableHead>{t('batches.status')}</TableHead>
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
                    <TableCell className="text-left">
                      <div className="flex flex-col">
                        <span className="font-medium">
                          {formatNumber(batch.quantity_available)}
                        </span>
                        <span className="text-xs text-muted-foreground">
                          מתוך {formatNumber(batch.quantity_received)}
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
            <p className="text-sm text-muted-foreground">אצוות פעילות</p>
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
            <p className="text-sm text-muted-foreground">קריטי (30- ימים)</p>
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
            <p className="text-sm text-muted-foreground">אזהרה (30-60 ימים)</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4 text-center">
            <p className="text-2xl font-bold">
              {batches.reduce((sum, b) => sum + b.quantity_available, 0).toFixed(2)}
            </p>
            <p className="text-sm text-muted-foreground">סה"כ כמות זמינה</p>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}

