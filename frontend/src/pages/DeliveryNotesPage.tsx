import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { FileText, Download, Eye, Plus } from 'lucide-react'

import { Button } from '@/components/ui/button'
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
import { formatDate } from '@/lib/utils'
import { deliveryNotesApi } from '@/lib/api'

interface DeliveryNote {
  id: string
  delivery_note_number: string
  customer_name: string
  status: string
  issue_date: string | null
  items_count: number
  total_quantity: number
  created_at: string
}

export function DeliveryNotesPage() {
  const { t } = useTranslation()
  const [notes, setNotes] = useState<DeliveryNote[]>([])
  const [loading, setLoading] = useState(true)
  const [page, setPage] = useState(1)
  const [total, setTotal] = useState(0)
  const [sortBy, setSortBy] = useState<string | null>(null)
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc')
  const pageSize = 20

  useEffect(() => {
    fetchNotes()
  }, [page, sortBy, sortOrder])

  const handleSort = (key: string) => {
    if (sortBy === key) {
      setSortOrder(prev => prev === 'asc' ? 'desc' : 'asc')
    } else {
      setSortBy(key)
      setSortOrder('asc')
    }
    setPage(1)
  }

  async function fetchNotes() {
    try {
      setLoading(true)
      const response = await deliveryNotesApi.list({
        page,
        sort_by: sortBy || undefined,
        sort_order: sortBy ? sortOrder : undefined,
      })
      setNotes(response.items || [])
      setTotal(response.total || 0)
    } catch (error) {
      console.error('Failed to fetch delivery notes:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleDownloadPdf = async (id: string, number: string) => {
    try {
      const blob = await deliveryNotesApi.downloadPdf(id)
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `${number}.pdf`
      a.click()
      window.URL.revokeObjectURL(url)
    } catch (error) {
      console.error('Failed to download PDF:', error)
      alert(t('deliveryNotes.pdfDownloadError'))
    }
  }

  const getStatusBadge = (status: string) => {
    switch (status.toLowerCase()) {
      case 'draft':
        return <Badge variant="secondary">{t('deliveryNotes.draft')}</Badge>
      case 'issued':
        return <Badge variant="warning">{t('deliveryNotes.issued')}</Badge>
      case 'delivered':
        return <Badge variant="safe">{t('deliveryNotes.delivered')}</Badge>
      case 'cancelled':
        return <Badge variant="critical">{t('deliveryNotes.cancelled')}</Badge>
      default:
        return <Badge>{status}</Badge>
    }
  }

  const totalPages = Math.ceil(total / pageSize)

  return (
    <div className="space-y-6">
      <Header title={t('deliveryNotes.title')} />

      <div className="flex items-center justify-between relative z-10 -mt-2">
        <div className="flex items-center gap-2">
          <FileText className="w-5 h-5 text-muted-foreground" />
          <span className="text-muted-foreground">
            {t('deliveryNotes.countLabel', { count: total })}
          </span>
        </div>
        <Button>
          <Plus className="w-4 h-4 me-2" />
          {t('deliveryNotes.create')}
        </Button>
      </div>

      <Card>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <SortableTableHead sortKey="delivery_note_number" currentSort={sortBy} currentOrder={sortOrder} onSort={handleSort}>{t('deliveryNotes.number')}</SortableTableHead>
                <TableHead>{t('deliveryNotes.customer')}</TableHead>
                <SortableTableHead sortKey="status" currentSort={sortBy} currentOrder={sortOrder} onSort={handleSort}>{t('deliveryNotes.status')}</SortableTableHead>
                <SortableTableHead sortKey="issue_date" currentSort={sortBy} currentOrder={sortOrder} onSort={handleSort}>{t('deliveryNotes.issueDate')}</SortableTableHead>
                <TableHead className="text-start">{t('deliveryNotes.items')}</TableHead>
                <TableHead className="text-start">{t('deliveryNotes.totalQuantity')}</TableHead>
                <TableHead className="w-12">{t('common.actions')}</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {loading ? (
                <TableRow>
                  <TableCell colSpan={7} className="text-center py-8">
                    {t('common.loading')}
                  </TableCell>
                </TableRow>
              ) : notes.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={7} className="text-center py-8 text-muted-foreground">
                    <FileText className="w-12 h-12 mx-auto mb-2 opacity-50" />
                    <p>{t('common.noData')}</p>
                  </TableCell>
                </TableRow>
              ) : (
                notes.map((note) => (
                  <TableRow key={note.id}>
                    <TableCell className="font-mono font-medium">
                      {note.delivery_note_number}
                    </TableCell>
                    <TableCell>{note.customer_name || '-'}</TableCell>
                    <TableCell>{getStatusBadge(note.status)}</TableCell>
                    <TableCell>
                      {note.issue_date ? formatDate(note.issue_date) : '-'}
                    </TableCell>
                    <TableCell className="text-start">
                      {t('deliveryNotes.itemsCount', { count: note.items_count })}
                    </TableCell>
                    <TableCell className="text-start">
                      {note.total_quantity.toFixed(2)}
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center gap-1">
                        <Button
                          variant="ghost"
                          size="icon"
                          className="h-8 w-8"
                          title={t('common.view')}
                        >
                          <Eye className="w-4 h-4" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="icon"
                          className="h-8 w-8"
                          title={t('deliveryNotes.downloadPdf')}
                          onClick={() => handleDownloadPdf(note.id, note.delivery_note_number)}
                        >
                          <Download className="w-4 h-4" />
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between">
          <p className="text-sm text-muted-foreground">
            {t('common.page')} {page} {t('common.of')} {totalPages}
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

