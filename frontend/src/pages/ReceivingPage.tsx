import { useState, useEffect, useRef, useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { PackagePlus, Barcode, Plus, X, Loader2, Camera, ScanLine, User } from 'lucide-react'
import { toast } from 'sonner'

import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Textarea } from '@/components/ui/textarea'
import { Header } from '@/components/layout/Header'
import { BarcodeScanner, type ScanResult } from '@/components/BarcodeScanner'
import {
  itemsApi,
  receivingApi,
  type Item,
  type PendingReceiptItem,
  type ReceiveWarning,
} from '@/lib/api'
import { websocketService } from '@/lib/websocket'

const receiveSchema = z.object({
  item_id: z.string().min(1, 'receiving.itemRequired'),
  quantity: z.number().min(1, 'receiving.quantityPositive'),
  expiration_date: z.string().min(1, 'receiving.expirationDateRequired'),
  manufacturing_date: z.string().optional(),
  batch_number: z.string().optional(),
  supplier_batch_number: z.string().optional(),
  notes: z.string().optional(),
})

type ReceiveFormData = z.infer<typeof receiveSchema>

export function ReceivingPage() {
  const { t } = useTranslation()
  const [items, setItems] = useState<Item[]>([])
  const [queue, setQueue] = useState<PendingReceiptItem[]>([])
  const [barcode, setBarcode] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [adding, setAdding] = useState(false)
  const [showScanner, setShowScanner] = useState(false)
  const [autoFilledFields, setAutoFilledFields] = useState<Set<string>>(new Set())
  const autoFillTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  const {
    register,
    handleSubmit,
    reset,
    setValue,
    watch,
    formState: { errors },
  } = useForm<ReceiveFormData>({
    resolver: zodResolver(receiveSchema),
    defaultValues: {
      quantity: 1,
      expiration_date: '',
      manufacturing_date: '',
      batch_number: '',
      supplier_batch_number: '',
      notes: '',
    },
  })

  const selectedItemId = watch('item_id')

  useEffect(() => {
    fetchItems()
  }, [])

  const loadQueue = useCallback(async () => {
    try {
      const rows = await receivingApi.listPending()
      setQueue(rows)
    } catch (error) {
      console.error('Failed to load pending queue:', error)
      toast.error(t('receiving.queueLoadError'))
    }
  }, [t])

  useEffect(() => {
    loadQueue()
  }, [loadQueue])

  // Live updates: react to any other user adding/removing/draining the queue.
  useEffect(() => {
    const unsubAdd = websocketService.subscribe('pending_receipt:added', (msg) => {
      const row = msg.data as PendingReceiptItem
      setQueue((prev) => (prev.some((r) => r.id === row.id) ? prev : [...prev, row]))
    })
    const unsubRemove = websocketService.subscribe('pending_receipt:removed', (msg) => {
      const { id } = msg.data as { id: string }
      setQueue((prev) => prev.filter((r) => r.id !== id))
    })
    const unsubClear = websocketService.subscribe('pending_receipt:cleared', () => {
      setQueue([])
    })
    return () => {
      unsubAdd()
      unsubRemove()
      unsubClear()
    }
  }, [])

  async function fetchItems() {
    try {
      const response = await itemsApi.list({ page_size: 100 })
      setItems(response.items)
    } catch (error) {
      console.error('Failed to fetch items:', error)
    }
  }

  const applyParsedData = (parsedData: any) => {
    const filled = new Set<string>()
    if (parsedData.expiration_date) {
      setValue('expiration_date', parsedData.expiration_date, { shouldValidate: true })
      filled.add('expiration_date')
    }
    if (parsedData.manufacturing_date) {
      setValue('manufacturing_date', parsedData.manufacturing_date, { shouldValidate: true })
      filled.add('manufacturing_date')
    }
    if (parsedData.quantity) {
      setValue('quantity', parsedData.quantity, { shouldValidate: true })
      filled.add('quantity')
    }
    if (parsedData.supplier_batch_number) {
      setValue('supplier_batch_number', parsedData.supplier_batch_number, { shouldValidate: true })
      filled.add('supplier_batch_number')
    }
    setAutoFilledFields(filled)
    if (autoFillTimerRef.current) clearTimeout(autoFillTimerRef.current)
    autoFillTimerRef.current = setTimeout(() => setAutoFilledFields(new Set()), 3000)
  }

  const handleBarcodeScanned = async ({ code }: ScanResult): Promise<boolean> => {
    try {
      const result = await receivingApi.validateBarcode(code)
      if (result.valid && result.item) {
        setValue('item_id', result.item.id, { shouldValidate: true })
        setBarcode('')

        if (result.parsed_data) {
          applyParsedData(result.parsed_data)
          toast.success(t('receiving.itemFoundFilled', { name: result.item.name, sku: result.item.sku }))
        } else {
          toast.success(t('receiving.itemFound', { name: result.item.name, sku: result.item.sku }))
        }

        if (navigator.vibrate) navigator.vibrate([100, 50, 100])
        return true
      }
      return false
    } catch (error) {
      console.error('Failed to validate barcode:', error)
      return false
    }
  }

  const handleManualBarcodeScanned = async (code: string) => {
    try {
      const result = await receivingApi.validateBarcode(code)
      if (result.valid && result.item) {
        setValue('item_id', result.item.id, { shouldValidate: true })
        setBarcode('')

        if (result.parsed_data) {
          applyParsedData(result.parsed_data)
          toast.success(t('receiving.itemFoundFilled', { name: result.item.name, sku: result.item.sku }))
        } else {
          toast.success(t('receiving.itemFound', { name: result.item.name, sku: result.item.sku }))
        }

        if (navigator.vibrate) navigator.vibrate([100, 50, 100])
      } else {
        toast.error(t('receiving.barcodeNotFound', { code }))
      }
    } catch (error) {
      console.error('Failed to validate barcode:', error)
      toast.error(t('scanner.barcodeError'))
    }
  }

  const handleBarcodeSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!barcode.trim()) return
    await handleManualBarcodeScanned(barcode)
  }

  const handleAddToList = async (data: ReceiveFormData) => {
    setAdding(true)
    try {
      await receivingApi.addPending({
        item_id: data.item_id,
        quantity: data.quantity,
        expiration_date: data.expiration_date,
        manufacturing_date: data.manufacturing_date || undefined,
        batch_number: data.batch_number || undefined,
        supplier_batch_number: data.supplier_batch_number || undefined,
        notes: data.notes || undefined,
      })
      // The row will also arrive via WS, but add optimistically for the local
      // tab so the UI doesn't wait on a round-trip.
      await loadQueue()
      setAutoFilledFields(new Set())
      reset({
        item_id: '',
        quantity: 1,
        expiration_date: '',
        manufacturing_date: '',
        batch_number: '',
        supplier_batch_number: '',
        notes: '',
      })
    } catch (error: any) {
      console.error('Failed to add item to queue:', error)
      toast.error(error.response?.data?.detail || t('receiving.addError'))
    } finally {
      setAdding(false)
    }
  }

  const handleRemoveFromList = async (id: string) => {
    // Optimistic removal; if it fails we reload to restore.
    setQueue((prev) => prev.filter((row) => row.id !== id))
    try {
      await receivingApi.removePending(id)
    } catch (error: any) {
      console.error('Failed to remove pending item:', error)
      toast.error(error.response?.data?.detail || t('receiving.removeError'))
      await loadQueue()
    }
  }

  const showWarnings = (warnings: ReceiveWarning[]) => {
    for (const w of warnings) {
      const batch = w.batch_number ?? ''
      const days = w.days_until_expiration
      if (w.level === 'critical') {
        toast.error(t('receiving.warningExpiryCritical', { batch, days }), { duration: 8000 })
      } else if (w.level === 'warning') {
        toast.warning(t('receiving.warningExpirySoon', { batch, days }), { duration: 6000 })
      } else {
        toast.info(t('receiving.warningExpiryInfo', { batch, days }))
      }
    }
  }

  const handleReceiveAll = async () => {
    if (queue.length === 0) return

    setSubmitting(true)
    try {
      const response = await receivingApi.receiveAllPending()
      toast.success(t('receiving.success'))
      showWarnings(response.warnings || [])
      // WS clear event will also empty the queue, but wipe locally in case
      // this tab is the only listener.
      setQueue([])
    } catch (error: any) {
      console.error('Failed to receive pending queue:', error)
      toast.error(error.response?.data?.detail || t('receiving.error'))
      await loadQueue()
    } finally {
      setSubmitting(false)
    }
  }

  const selectedItem = items.find(i => i.id === selectedItemId)

  const fieldClass = (name: string) =>
    autoFilledFields.has(name) ? 'ring-2 ring-primary/40 transition-all' : ''

  const formatAddedAt = (iso: string) => {
    try {
      const d = new Date(iso)
      return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    } catch {
      return ''
    }
  }

  return (
    <div className="space-y-6">
      <Header title={t('receiving.title')} />

      {/* Camera Scanner Modal */}
      {showScanner && (
        <BarcodeScanner
          onScan={handleBarcodeScanned}
          onClose={() => setShowScanner(false)}
        />
      )}

      {/* Scan + Form in a single flow */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg flex items-center gap-2">
            <Barcode className="w-5 h-5" />
            {t('receiving.scanBarcode')}
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex gap-2">
            <Button
              type="button"
              variant="outline"
              className="flex-1 h-14 flex items-center justify-center gap-2 border-dashed"
              onClick={() => setShowScanner(true)}
            >
              <Camera className="w-5 h-5 text-primary" />
              <span>{t('receiving.scanWithCamera')}</span>
            </Button>
          </div>

          <div className="relative">
            <div className="absolute inset-0 flex items-center">
              <span className="w-full border-t" />
            </div>
            <div className="relative flex justify-center text-xs uppercase">
              <span className="bg-card px-2 text-muted-foreground">{t('receiving.orEnterManually')}</span>
            </div>
          </div>

          <form onSubmit={handleBarcodeSubmit} className="flex gap-2">
            <Input
              placeholder={t('receiving.enterBarcode')}
              value={barcode}
              onChange={(e) => setBarcode(e.target.value)}
              className="font-mono flex-1"
            />
            <Button type="submit" disabled={!barcode}>
              <ScanLine className="w-4 h-4" />
            </Button>
          </form>
        </CardContent>
      </Card>

      {/* Receive Form */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg flex items-center gap-2">
            <PackagePlus className="w-5 h-5" />
            {t('receiving.title')}
          </CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit(handleAddToList)} className="space-y-4">
            {/* Item Selection + SKU */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <div className="sm:col-span-2 space-y-2">
                <Label htmlFor="item_id">{t('receiving.selectItem')} *</Label>
                <select
                  id="item_id"
                  {...register('item_id')}
                  className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  <option value="">{t('picking.selectItemPlaceholder')}</option>
                  {items.map((item) => (
                    <option key={item.id} value={item.id}>
                      {item.name}
                    </option>
                  ))}
                </select>
                {errors.item_id && (
                  <p className="text-sm text-destructive">{t(errors.item_id.message ?? '')}</p>
                )}
              </div>

              <div className="space-y-2">
                <Label>{t('items.sku')}</Label>
                <Input
                  value={selectedItem?.sku || ''}
                  readOnly
                  className="font-mono bg-muted"
                  placeholder="—"
                />
              </div>
            </div>

            {selectedItem && (
              <div className="p-3 rounded-lg bg-primary/5 border border-primary/20 text-sm flex gap-4 text-muted-foreground">
                <span>{t('items.supplier')}: {selectedItem.supplier}</span>
                <span>{t('picking.unitShort')}: {selectedItem.unit_of_measure}</span>
              </div>
            )}

            {/* Quantity + Dates */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <div className="space-y-2">
                <Label htmlFor="quantity">{t('receiving.quantity')} *</Label>
                <Input
                  id="quantity"
                  type="number"
                  step="1"
                  min={1}
                  inputMode="numeric"
                  {...register('quantity', { valueAsNumber: true })}
                  className={fieldClass('quantity')}
                />
                {errors.quantity && (
                  <p className="text-sm text-destructive">{t(errors.quantity.message ?? '')}</p>
                )}
              </div>

              <div className="space-y-2">
                <Label htmlFor="expiration_date">{t('receiving.expirationDate')} *</Label>
                <Input
                  id="expiration_date"
                  type="date"
                  {...register('expiration_date')}
                  className={fieldClass('expiration_date')}
                />
                {errors.expiration_date && (
                  <p className="text-sm text-destructive">{t(errors.expiration_date.message ?? '')}</p>
                )}
              </div>

              <div className="space-y-2">
                <Label htmlFor="manufacturing_date">{t('receiving.manufacturingDate')}</Label>
                <Input
                  id="manufacturing_date"
                  type="date"
                  {...register('manufacturing_date')}
                  className={fieldClass('manufacturing_date')}
                />
              </div>
            </div>

            {/* Batch numbers */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="batch_number">{t('receiving.batchNumber')}</Label>
                <Input
                  id="batch_number"
                  {...register('batch_number')}
                  placeholder={t('receiving.batchNumberPlaceholder')}
                  className={fieldClass('batch_number')}
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="supplier_batch_number">{t('receiving.supplierBatchNumber')}</Label>
                <Input
                  id="supplier_batch_number"
                  {...register('supplier_batch_number')}
                  placeholder={t('receiving.supplierBatchPlaceholder')}
                  className={fieldClass('supplier_batch_number')}
                />
              </div>
            </div>

            {/* Notes */}
            <div className="space-y-2">
              <Label htmlFor="notes">{t('receiving.notes')}</Label>
              <Textarea
                id="notes"
                {...register('notes')}
                placeholder={t('common.notesPlaceholder')}
                rows={2}
              />
            </div>

            <Button type="submit" className="w-full" disabled={adding}>
              {adding ? (
                <Loader2 className="w-4 h-4 me-2 animate-spin" />
              ) : (
                <Plus className="w-4 h-4 me-2" />
              )}
              {t('receiving.addToList')}
            </Button>
          </form>
        </CardContent>
      </Card>

      {/* Shared Pending Queue */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between flex-wrap gap-4">
            <CardTitle className="text-lg">
              {t('receiving.listTitle', { count: queue.length })}
            </CardTitle>
            <Button
              onClick={handleReceiveAll}
              disabled={submitting || queue.length === 0}
              className="touch-manipulation"
            >
              {submitting ? (
                <>
                  <Loader2 className="w-4 h-4 me-2 animate-spin" />
                  {t('receiving.recording')}
                </>
              ) : (
                <>
                  <PackagePlus className="w-4 h-4 me-2" />
                  {t('receiving.receiveAll')}
                </>
              )}
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          {queue.length === 0 ? (
            <p className="text-sm text-muted-foreground py-4 text-center">
              {t('receiving.queueEmpty')}
            </p>
          ) : (
            <div className="space-y-3">
              {queue.map((row) => {
                const adderName = row.added_by_full_name || row.added_by_username
                return (
                  <div
                    key={row.id}
                    className="flex items-center justify-between p-4 rounded-lg border bg-card"
                  >
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-3 mb-2 flex-wrap">
                        <Badge variant="secondary" className="font-mono">
                          {row.item_sku}
                        </Badge>
                        <span className="font-medium truncate">{row.item_name}</span>
                        <span className="inline-flex items-center gap-1 text-xs text-muted-foreground">
                          <User className="w-3 h-3" />
                          {t('receiving.addedBy', { name: adderName })} · {formatAddedAt(row.created_at)}
                        </span>
                      </div>
                      <div className="flex gap-4 flex-wrap text-sm text-muted-foreground">
                        <span>{t('picking.quantityLabel')}: {row.quantity}</span>
                        <span>{t('picking.expirationLabel')}: {row.expiration_date}</span>
                        {row.manufacturing_date && (
                          <span>{t('receiving.manufacturingShort')}: {row.manufacturing_date}</span>
                        )}
                        {row.batch_number && (
                          <span>{t('receiving.batchShort')}: {row.batch_number}</span>
                        )}
                        {row.supplier_batch_number && (
                          <span>{t('receiving.supplierBatchShort')}: {row.supplier_batch_number}</span>
                        )}
                      </div>
                      {row.notes && (
                        <p className="text-sm text-muted-foreground mt-1 truncate">{row.notes}</p>
                      )}
                    </div>
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={() => handleRemoveFromList(row.id)}
                      className="text-destructive flex-shrink-0 touch-manipulation"
                    >
                      <X className="w-4 h-4" />
                    </Button>
                  </div>
                )
              })}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
