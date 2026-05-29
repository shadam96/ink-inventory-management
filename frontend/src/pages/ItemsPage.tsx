import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Plus, Pencil, Trash2, Download, FileSpreadsheet } from 'lucide-react'
import { toast } from 'sonner'

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
import { ItemDialog } from '@/components/ItemDialog'
import { formatCurrency, formatNumber, convertAmount } from '@/lib/utils'
import { itemsApi, systemSettingsApi, type Item, type CreateItemData, type SystemSettings } from '@/lib/api'
import { useUIStore } from '@/store/ui'

export function ItemsPage() {
  const { t } = useTranslation()
  const { currency: displayCurrency } = useUIStore()
  const [items, setItems] = useState<Item[]>([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [page, setPage] = useState(1)
  const [total, setTotal] = useState(0)
  const [dialogOpen, setDialogOpen] = useState(false)
  const [editingItem, setEditingItem] = useState<Item | null>(null)
  const [sortBy, setSortBy] = useState<string | null>(null)
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('asc')
  const [fxRates, setFxRates] = useState<SystemSettings | null>(null)
  const pageSize = 20

  useEffect(() => {
    fetchItems()
  }, [page, search, sortBy, sortOrder])

  // FX rates are fetched once on mount; the global display currency may change
  // afterwards, but the underlying rates don't depend on it.
  useEffect(() => {
    systemSettingsApi.get().then(setFxRates).catch((e) => {
      console.error('Failed to fetch FX rates:', e)
    })
  }, [])

  const handleSort = (key: string) => {
    if (sortBy === key) {
      setSortOrder(prev => prev === 'asc' ? 'desc' : 'asc')
    } else {
      setSortBy(key)
      setSortOrder('asc')
    }
    setPage(1)
  }

  async function fetchItems() {
    try {
      setLoading(true)
      const response = await itemsApi.list({
        page,
        page_size: pageSize,
        search: search || undefined,
        sort_by: sortBy || undefined,
        sort_order: sortBy ? sortOrder : undefined,
      })
      setItems(response.items)
      setTotal(response.total)
    } catch (error) {
      console.error('Failed to fetch items:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleSearch = (value: string) => {
    setSearch(value)
    setPage(1)
  }

  const handleAdd = () => {
    setEditingItem(null)
    setDialogOpen(true)
  }

  const handleEdit = (item: Item) => {
    setEditingItem(item)
    setDialogOpen(true)
  }

  const handleDelete = async (item: Item) => {
    if (!confirm(t('items.confirmDelete', { name: item.name }))) {
      return
    }

    try {
      await itemsApi.delete(item.id)
      fetchItems()
    } catch (error) {
      console.error('Failed to delete item:', error)
      alert(t('items.deleteError'))
    }
  }

  const handleSubmit = async (data: CreateItemData) => {
    try {
      if (editingItem) {
        await itemsApi.update(editingItem.id, data)
      } else {
        await itemsApi.create(data)
      }
      fetchItems()
    } catch (error: any) {
      const message = error.response?.data?.detail || t('items.saveError')
      alert(message)
      throw error
    }
  }

  const totalPages = Math.ceil(total / pageSize)

  const handleExport = async (format: 'excel' | 'csv') => {
    try {
      const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1'
      const response = await fetch(`${apiUrl}/items/export/${format}`, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
        },
      })
      
      if (!response.ok) throw new Error('Export failed')
      
      const blob = await response.blob()
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `items_export.${format === 'excel' ? 'xlsx' : 'csv'}`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      window.URL.revokeObjectURL(url)
      
      toast.success(t('items.exportSuccess', { format: format === 'excel' ? 'Excel' : 'CSV' }))
    } catch (error) {
      console.error('Export failed:', error)
      toast.error(t('items.exportError'))
    }
  }

  return (
    <div className="space-y-6">
      <Header title={t('items.title')} />

      <div className="flex items-center justify-between relative z-10 -mt-2">
        <SearchInput
          value={search}
          onChange={handleSearch}
          placeholder={t('items.search')}
          className="w-80"
        />
        <div className="flex gap-2">
          <Button variant="outline" onClick={() => handleExport('excel')}>
            <FileSpreadsheet className="w-4 h-4 me-2" />
            Excel
          </Button>
          <Button variant="outline" onClick={() => handleExport('csv')}>
            <Download className="w-4 h-4 me-2" />
            CSV
          </Button>
          <Button onClick={handleAdd}>
            <Plus className="w-4 h-4 me-2" />
            {t('items.add')}
          </Button>
        </div>
      </div>

      <Card>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <SortableTableHead sortKey="sku" currentSort={sortBy} currentOrder={sortOrder} onSort={handleSort}>{t('items.sku')}</SortableTableHead>
                <SortableTableHead sortKey="name" currentSort={sortBy} currentOrder={sortOrder} onSort={handleSort}>{t('items.name')}</SortableTableHead>
                <SortableTableHead sortKey="supplier" currentSort={sortBy} currentOrder={sortOrder} onSort={handleSort}>{t('items.supplier')}</SortableTableHead>
                <TableHead>{t('items.unit')}</TableHead>
                <SortableTableHead sortKey="cost_price" currentSort={sortBy} currentOrder={sortOrder} onSort={handleSort} className="text-start">{t('items.costPrice')}</SortableTableHead>
                <SortableTableHead sortKey="reorder_point" currentSort={sortBy} currentOrder={sortOrder} onSort={handleSort} className="text-start">{t('items.reorderPoint')}</SortableTableHead>
                <TableHead className="w-12">{t('items.actions')}</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {loading ? (
                <TableRow>
                  <TableCell colSpan={7} className="text-center py-8">
                    {t('common.loading')}
                  </TableCell>
                </TableRow>
              ) : items.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={7} className="text-center py-8 text-muted-foreground">
                    {t('common.noData')}
                  </TableCell>
                </TableRow>
              ) : (
                items.map((item) => (
                  <TableRow key={item.id}>
                    <TableCell className="font-mono font-medium">
                      {item.sku}
                    </TableCell>
                    <TableCell>{item.name}</TableCell>
                    <TableCell className="text-muted-foreground">
                      {item.supplier}
                    </TableCell>
                    <TableCell>
                      <Badge variant="secondary">{item.unit_of_measure}</Badge>
                    </TableCell>
                    <TableCell className="text-start font-mono">
                      {fxRates
                        ? formatCurrency(
                            convertAmount(item.cost_price, item.currency, displayCurrency, fxRates),
                            displayCurrency,
                          )
                        : formatCurrency(item.cost_price, item.currency)}
                    </TableCell>
                    <TableCell className="text-start">
                      {formatNumber(item.reorder_point)}
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center gap-1">
                        <Button
                          variant="ghost"
                          size="icon"
                          className="h-8 w-8"
                          onClick={() => handleEdit(item)}
                        >
                          <Pencil className="w-4 h-4" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="icon"
                          className="h-8 w-8 text-destructive"
                          onClick={() => handleDelete(item)}
                        >
                          <Trash2 className="w-4 h-4" />
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
            {t('common.page')} {page} {t('common.of')} {totalPages} ({total} {t('common.total')})
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

      {/* Item Dialog */}
      <ItemDialog
        open={dialogOpen}
        onOpenChange={setDialogOpen}
        item={editingItem}
        onSubmit={handleSubmit}
      />
    </div>
  )
}
