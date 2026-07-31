import { useState, useEffect, useRef } from 'react'
import { useTranslation } from 'react-i18next'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { PackagePlus, Barcode, Plus, X, XCircle, Loader2, Camera, ScanLine, Pencil } from 'lucide-react'
import { toast } from 'sonner'

import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { QuantityInput } from '@/components/ui/quantity-input'
import { Label } from '@/components/ui/label'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Textarea } from '@/components/ui/textarea'
import { Header } from '@/components/layout/Header'
import { BarcodeScanner, type ScanResult } from '@/components/BarcodeScanner'
import { itemsApi, receivingApi, systemSettingsApi, type Item } from '@/lib/api'
import { addPendingOperation, isOnline } from '@/lib/offline'
import { cn, daysUntilExpiration } from '@/lib/utils'

// Fallback used only until systemSettingsApi.get() resolves - matches the
// backend's own default (system_settings.min_shelf_life_days) so the row
// stays the single source of truth instead of a separately hardcoded copy.
const DEFAULT_MIN_SHELF_LIFE_DAYS = 180

const receiveSchema = z.object({
  item_id: z.string().min(1, 'receiving.itemRequired'),
  // Decimal, not integer: items are commonly measured in KG/L (see
  // Item.unit_of_measure, default "KG") and the backend stores quantity as
  // Numeric(12, 3) - forcing whole numbers here made it impossible to
  // receive an accurately-weighed real-world shipment (e.g. "37.5 KG").
  quantity: z.number().positive('receiving.quantityPositive'),
  expiration_date: z.string().min(1, 'receiving.expirationDateRequired'),
  manufacturing_date: z.string().optional(),
  batch_number: z.string().optional(),
  notes: z.string().optional(),
})

type ReceiveFormData = z.infer<typeof receiveSchema>

interface ReceiveItem extends ReceiveFormData {
  id: string
  item_name?: string
  item_sku?: string
}

export function ReceivingPage() {
  const { t } = useTranslation()
  const [items, setItems] = useState<Item[]>([])
  const [receiveList, _setReceiveList] = useState<ReceiveItem[]>(() => {
    try {
      const saved = localStorage.getItem('receiveList')
      return saved ? JSON.parse(saved) : []
    } catch {
      return []
    }
  })

  // Wrapper that syncs to localStorage on every mutation
  const setReceiveList = (update: ReceiveItem[] | ((prev: ReceiveItem[]) => ReceiveItem[])) => {
    _setReceiveList((prev) => {
      const next = typeof update === 'function' ? update(prev) : update
      if (next.length > 0) {
        localStorage.setItem('receiveList', JSON.stringify(next))
      } else {
        localStorage.removeItem('receiveList')
      }
      return next
    })
  }
  const [barcode, setBarcode] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [showScanner, setShowScanner] = useState(false)
  const [autoFilledFields, setAutoFilledFields] = useState<Set<string>>(new Set())
  const [minShelfLifeDays, setMinShelfLifeDays] = useState(DEFAULT_MIN_SHELF_LIFE_DAYS)
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
      notes: '',
    },
  })

  const selectedItemId = watch('item_id')

  async function fetchItems() {
    try {
      const response = await itemsApi.list({ page_size: 100 })
      setItems(response.items)
    } catch (error) {
      console.error('Failed to fetch items:', error)
    }
  }

  async function fetchMinShelfLifeDays() {
    try {
      const settings = await systemSettingsApi.get()
      setMinShelfLifeDays(settings.min_shelf_life_days)
    } catch (error) {
      console.error('Failed to fetch system settings:', error)
    }
  }

  useEffect(() => {
    fetchItems()
    fetchMinShelfLifeDays()

    // A clerk's tab realistically stays open for a whole shift. Without
    // this, a newly-added item or an admin's live change to the shelf-life
    // threshold (Settings page, in another tab) silently doesn't show up
    // here until a manual reload.
    const handleVisibility = () => {
      if (document.visibilityState === 'visible') {
        fetchItems()
        fetchMinShelfLifeDays()
      }
    }
    document.addEventListener('visibilitychange', handleVisibility)
    return () => document.removeEventListener('visibilitychange', handleVisibility)
  }, [])

  // parsedData only carries the fields the *current* scan's barcode encodes.
  // Any field it omits must be cleared back to its default rather than left
  // as-is, otherwise a value auto-filled by a previous scan (e.g. item A's
  // expiration date/quantity) silently leaks into the next item's receipt.
  const applyParsedData = (parsedData: Record<string, any> | null | undefined) => {
    const data = parsedData || {}
    const filled = new Set<string>()
    if (data.expiration_date) {
      setValue('expiration_date', data.expiration_date, { shouldValidate: true })
      filled.add('expiration_date')
    } else {
      setValue('expiration_date', '')
    }
    if (data.manufacturing_date) {
      setValue('manufacturing_date', data.manufacturing_date, { shouldValidate: true })
      filled.add('manufacturing_date')
    } else {
      setValue('manufacturing_date', '')
    }
    if (data.quantity) {
      setValue('quantity', data.quantity, { shouldValidate: true })
      filled.add('quantity')
    } else {
      setValue('quantity', 1)
    }
    if (data.supplier_batch_number) {
      setValue('batch_number', data.supplier_batch_number, { shouldValidate: true })
      filled.add('batch_number')
    } else {
      setValue('batch_number', '')
    }
    setAutoFilledFields(filled)
    // Clear highlight after 3 seconds
    if (autoFillTimerRef.current) clearTimeout(autoFillTimerRef.current)
    autoFillTimerRef.current = setTimeout(() => setAutoFilledFields(new Set()), 3000)
  }

  // Shared by both the camera scanner and the manual barcode field - only
  // how "not found"/errors are surfaced differs between the two callers.
  const applyScanResult = (result: Awaited<ReturnType<typeof receivingApi.validateBarcode>>): boolean => {
    if (!result.valid || !result.item) return false

    setValue('item_id', result.item.id, { shouldValidate: true })
    setBarcode('')

    applyParsedData(result.parsed_data)
    if (result.parsed_data) {
      toast.success(t('receiving.itemFoundFilled', { name: result.item.name, sku: result.item.sku }))
    } else {
      toast.success(t('receiving.itemFound', { name: result.item.name, sku: result.item.sku }))
    }

    if (navigator.vibrate) navigator.vibrate([100, 50, 100])
    return true
  }

  const handleBarcodeScanned = async ({ code }: ScanResult): Promise<boolean> => {
    // Barcode lookup always hits the network - unlike handleReceiveAll,
    // there's no offline queue for it, so fail fast with a clear reason
    // instead of a confusing generic network error.
    if (!isOnline()) {
      toast.error(t('receiving.offlineBarcodeUnavailable'))
      return false
    }
    try {
      const result = await receivingApi.validateBarcode(code)
      return applyScanResult(result)
    } catch (error) {
      console.error('Failed to validate barcode:', error)
      return false
    }
  }

  const handleManualBarcodeScanned = async (code: string) => {
    if (!isOnline()) {
      toast.error(t('receiving.offlineBarcodeUnavailable'))
      return
    }
    try {
      const result = await receivingApi.validateBarcode(code)
      if (!applyScanResult(result)) {
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

  const handleAddToList = (data: ReceiveFormData) => {
    const item = items.find(i => i.id === data.item_id)
    if (!item) return

    const newItem: ReceiveItem = {
      ...data,
      id: Math.random().toString(36).substring(7),
      item_name: item.name,
      item_sku: item.sku,
    }

    setReceiveList([...receiveList, newItem])
    setAutoFilledFields(new Set())
    toast.success(t('receiving.addedToList'))
    reset({
      item_id: '',
      quantity: 1,
      expiration_date: '',
      manufacturing_date: '',
      batch_number: '',
      notes: '',
    })
  }

  const handleRemoveFromList = (id: string) => {
    setReceiveList(receiveList.filter(item => item.id !== id))
  }

  // Pull a staged line back into the form for editing instead of forcing a
  // full remove-and-re-add - re-typing a multi-field entry (with
  // barcode-parsed batch/expiration data) just to fix one typo was the
  // only option before, and that data entry was lost in the process.
  const handleEditItem = (id: string) => {
    const item = receiveList.find(i => i.id === id)
    if (!item) return

    setValue('item_id', item.item_id, { shouldValidate: true })
    setValue('quantity', item.quantity, { shouldValidate: true })
    setValue('expiration_date', item.expiration_date, { shouldValidate: true })
    setValue('manufacturing_date', item.manufacturing_date || '')
    setValue('batch_number', item.batch_number || '')
    setValue('notes', item.notes || '')

    setReceiveList(receiveList.filter(i => i.id !== id))
    setAutoFilledFields(new Set())
  }

  const handleReceiveAll = async () => {
    if (receiveList.length === 0) return

    // This is a best-effort local grouping, not the authority on whether an
    // item can actually be received - the device's clock could be wrong.
    // The backend re-validates every item with its own clock; splitting
    // here only decides which items we *attempt* now vs. leave staged, so
    // a wrong device clock can delay a valid item but never wrongly force
    // one through (the backend still rejects it) or get one stuck (it just
    // stays in the list untouched, exactly like before submission).
    const eligible = receiveList.filter(
      (item) => daysUntilExpiration(item.expiration_date) >= minShelfLifeDays
    )
    const flagged = receiveList.filter(
      (item) => daysUntilExpiration(item.expiration_date) < minShelfLifeDays
    )

    if (eligible.length === 0) {
      toast.error(t('receiving.expirationTooSoonError'))
      return
    }

    setSubmitting(true)
    try {
      const payload = eligible.length === 1
        ? {
            item_id: eligible[0].item_id,
            quantity: eligible[0].quantity,
            expiration_date: eligible[0].expiration_date,
            manufacturing_date: eligible[0].manufacturing_date || undefined,
            batch_number: eligible[0].batch_number,
            notes: eligible[0].notes,
          }
        : {
            items: eligible.map(item => ({
              item_id: item.item_id,
              quantity: item.quantity,
              expiration_date: item.expiration_date,
              manufacturing_date: item.manufacturing_date || undefined,
              batch_number: item.batch_number,
              notes: item.notes,
            })),
          }

      if (!isOnline()) {
        // Must match the relative paths receivingApi actually posts to
        // (api's baseURL already includes /api/v1, so prefixing it here
        // would double it and 404 on replay - see receivingApi.receive /
        // receiveMultiple in lib/api.ts).
        await addPendingOperation(
          'receive',
          eligible.length === 1 ? '/receiving/receive' : '/receiving/receive-multiple',
          'POST',
          payload
        )
        toast.info(t('receiving.offlineQueued'))
        setReceiveList(flagged)
        if (flagged.length > 0) {
          toast.warning(t('receiving.someItemsHeldBack', { count: flagged.length }))
        }
        return
      }

      if (eligible.length === 1) {
        await receivingApi.receive(payload as any)
      } else {
        await receivingApi.receiveMultiple(payload as any)
      }

      toast.success(t('receiving.success'))
      setReceiveList(flagged)
      if (flagged.length > 0) {
        toast.warning(t('receiving.someItemsHeldBack', { count: flagged.length }))
      }
    } catch (error: any) {
      console.error('Failed to receive items:', error)
      toast.error(error.response?.data?.detail || t('receiving.error'))
      // Nothing was confirmed received - leave the full list (including
      // the eligible items just attempted) staged so nothing is lost.
    } finally {
      setSubmitting(false)
    }
  }

  const selectedItem = items.find(i => i.id === selectedItemId)

  const fieldClass = (name: string) =>
    autoFilledFields.has(name) ? 'ring-2 ring-primary/40 transition-all' : ''

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

            {/* Item info banner */}
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
                <QuantityInput
                  id="quantity"
                  {...register('quantity', { valueAsNumber: true })}
                  step={1}
                  min={0.001}
                  unit={t('common.liter')}
                  inputMode="decimal"
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

            {/* Batch number */}
            <div className="space-y-2">
              <Label htmlFor="batch_number">{t('receiving.batchNumber')}</Label>
              <Input
                id="batch_number"
                {...register('batch_number')}
                placeholder={t('receiving.batchNumberPlaceholder')}
                className={fieldClass('batch_number')}
              />
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

            <Button type="submit" className="w-full">
              <Plus className="w-4 h-4 me-2" />
              {t('receiving.addToList')}
            </Button>
          </form>
        </CardContent>
      </Card>

      {/* Receive List */}
      {receiveList.length > 0 && (
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between flex-wrap gap-4">
              <CardTitle className="text-lg">{t('receiving.listTitle', { count: receiveList.length })}</CardTitle>
              <Button
                onClick={handleReceiveAll}
                disabled={submitting}
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
            <div className="space-y-3">
              {receiveList.map((item) => {
                const expirationTooSoon = daysUntilExpiration(item.expiration_date) < minShelfLifeDays
                return (
                <div
                  key={item.id}
                  className={cn(
                    'flex items-center justify-between p-4 rounded-lg border bg-card',
                    expirationTooSoon && 'border-destructive'
                  )}
                >
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-3 mb-2 flex-wrap">
                      <Badge variant="secondary" className="font-mono">
                        {item.item_sku}
                      </Badge>
                      <span className="font-medium truncate">{item.item_name}</span>
                    </div>
                    <div className="flex gap-4 flex-wrap text-sm text-muted-foreground">
                      <span>{t('picking.quantityLabel')}: {item.quantity}</span>
                      <span
                        className={cn(
                          'flex items-center gap-1',
                          expirationTooSoon && 'text-destructive font-medium'
                        )}
                        title={expirationTooSoon ? t('receiving.expirationTooSoon') : undefined}
                      >
                        {expirationTooSoon && <XCircle className="w-3.5 h-3.5" />}
                        {t('picking.expirationLabel')}: {item.expiration_date}
                      </span>
                      {item.manufacturing_date && <span>{t('receiving.manufacturingShort')}: {item.manufacturing_date}</span>}
                      {item.batch_number && <span>{t('receiving.batchShort')}: {item.batch_number}</span>}
                    </div>
                    {item.notes && (
                      <p className="text-sm text-muted-foreground mt-1 truncate">{item.notes}</p>
                    )}
                  </div>
                  <div className="flex items-center flex-shrink-0">
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={() => handleEditItem(item.id)}
                      title={t('receiving.editItem')}
                      className="touch-manipulation"
                    >
                      <Pencil className="w-4 h-4" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={() => handleRemoveFromList(item.id)}
                      className="text-destructive touch-manipulation"
                    >
                      <X className="w-4 h-4" />
                    </Button>
                  </div>
                </div>
                )
              })}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
