import { useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import {
  PackageMinus,
  AlertCircle,
  CheckCircle2,
  Loader2,
  Camera,
  ThumbsUp,
  ThumbsDown,
} from 'lucide-react'
import { toast } from 'sonner'

import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Textarea } from '@/components/ui/textarea'
import { Header } from '@/components/layout/Header'
import { BarcodeScanner, type ScanResult } from '@/components/BarcodeScanner'
import { PostPickDialog } from '@/components/PostPickDialog'
import { formatDate, daysUntilExpiration, getExpirationStatus, cn } from '@/lib/utils'
import { itemsApi, customersApi, pickingApi, receivingApi, type Item } from '@/lib/api'
import { addPendingOperation, isOnline } from '@/lib/offline'
import { useAuthStore } from '@/store/auth'

// ---------- Admin schema (requires customer) ----------
const adminPickSchema = z.object({
  item_id: z.string().min(1, 'פריט נדרש'),
  quantity: z.number().int('כמות חייבת להיות מספר שלם').min(1, 'כמות חייבת להיות חיובית'),
  customer_id: z.string().min(1, 'לקוח נדרש'),
  reference_number: z.string().optional(),
  notes: z.string().optional(),
})
type AdminPickFormData = z.infer<typeof adminPickSchema>

// ---------- Customer schema (no customer field) ----------
const customerPickSchema = z.object({
  item_id: z.string().min(1, 'פריט נדרש'),
  quantity: z.number().int('כמות חייבת להיות מספר שלם').min(1, 'כמות חייבת להיות חיובית'),
  notes: z.string().optional(),
})
type CustomerPickFormData = z.infer<typeof customerPickSchema>

interface SuggestedBatch {
  batch_id: string
  batch_number: string
  suggested_quantity: number
  quantity_available: number
  expiration_date: string
  days_until_expiration: number
  warning_level: string
  location_code?: string
}

interface CustomerInfo {
  id: string
  name: string
}

// ===== ADMIN PICKING VIEW =====
type Strategy = 'fefo' | 'fifo' | 'lifo'

function AdminPickingView() {
  const { t } = useTranslation()
  const [items, setItems] = useState<Item[]>([])
  const [customers, setCustomers] = useState<CustomerInfo[]>([])
  const [suggestions, setSuggestions] = useState<SuggestedBatch[]>([])
  const [fifoSuggestions, setFifoSuggestions] = useState<SuggestedBatch[]>([])
  const [lifoSuggestions, setLifoSuggestions] = useState<SuggestedBatch[]>([])
  const [totalAvailable, setTotalAvailable] = useState<number>(0)
  const [canFulfill, setCanFulfill] = useState(true)
  const [activeStrategy, setActiveStrategy] = useState<Strategy>('fefo')
  const [loading, setLoading] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [showScanner, setShowScanner] = useState(false)
  const [selectedBatchId, setSelectedBatchId] = useState<string | null>(null)
  const [postPickRef, setPostPickRef] = useState<string | null>(null)

  const {
    register,
    handleSubmit,
    reset,
    watch,
    setValue,
    formState: { errors },
  } = useForm<AdminPickFormData>({
    resolver: zodResolver(adminPickSchema),
  })

  const selectedItemId = watch('item_id')
  const requestedQuantity = watch('quantity')

  // ----- Validation flow -----
  // Item is "in stock" only if it has more than its configured min_stock floor.
  // A requested quantity is valid only if the pick leaves at least min_stock
  // remaining (i.e. it doesn't dip into the safety stock).
  const selectedItem = items.find(i => i.id === selectedItemId)
  const itemAvailable = selectedItem?.total_quantity_available ?? 0
  const itemMinStock = selectedItem?.min_stock ?? 0
  const itemInStock = !!selectedItem && itemAvailable > itemMinStock
  const pickableQuantity = Math.max(0, itemAvailable - itemMinStock)
  const hasQuantity = typeof requestedQuantity === 'number' && requestedQuantity > 0
  const quantityInStock = itemInStock && hasQuantity && requestedQuantity <= pickableQuantity
  const canSelectCustomer = itemInStock && quantityInStock

  useEffect(() => {
    fetchItems()
    fetchCustomers()
  }, [])

  useEffect(() => {
    if (selectedItemId && itemInStock) {
      fetchSuggestions()
    } else {
      setSuggestions([])
      setFifoSuggestions([])
      setLifoSuggestions([])
      setTotalAvailable(0)
      setCanFulfill(true)
    }
    setSelectedBatchId(null)
  }, [selectedItemId, requestedQuantity, itemInStock])

  async function fetchItems() {
    try {
      const response = await itemsApi.list({ page_size: 100 })
      // Show all items here — the in-stock check happens after selection
      // so we can display a clear "not in stock" message for items that
      // dipped below min_stock.
      setItems(response.items)
    } catch (error) {
      console.error('Failed to fetch items:', error)
    }
  }

  async function fetchCustomers() {
    try {
      const response = await customersApi.list()
      setCustomers(response.items || [])
    } catch (error) {
      console.error('Failed to fetch customers:', error)
    }
  }

  async function fetchSuggestions() {
    if (!selectedItemId) return
    setLoading(true)
    try {
      const qty = requestedQuantity || 0
      const response = await pickingApi.suggestBatches(selectedItemId, qty)
      setSuggestions(response.suggestions || [])
      setFifoSuggestions(response.fifo_suggestions || [])
      setLifoSuggestions(response.lifo_suggestions || [])
      setTotalAvailable(response.total_available ?? 0)
      setCanFulfill(response.can_fulfill ?? true)
    } catch (error) {
      console.error('Failed to fetch suggestions:', error)
      setSuggestions([])
      setFifoSuggestions([])
      setLifoSuggestions([])
    } finally {
      setLoading(false)
    }
  }

  const handleBarcodeScanned = async ({ code }: ScanResult): Promise<boolean> => {
    try {
      const result = await receivingApi.validateBarcode(code)
      if (result.valid && result.item) {
        setValue('item_id', result.item.id)
        toast.success(`נמצא: ${result.item.name} (${result.item.sku})`)
        if (navigator.vibrate) navigator.vibrate([100, 50, 100])
        return true
      }
      return false
    } catch {
      return false
    }
  }

  const handleDispatch = async (data: AdminPickFormData) => {
    if (activeSuggestions.length === 0) {
      toast.error('אין אצוות זמינות לליקוט')
      return
    }

    // If the user manually picked a single batch from the list, use only
    // that one. Otherwise fall back to the strategy's auto-allocation.
    let picks: { batch_id: string; quantity: number }[]
    if (selectedBatchId) {
      const chosen = activeSuggestions.find(s => s.batch_id === selectedBatchId)
      if (!chosen) {
        toast.error('האצווה הנבחרת אינה זמינה')
        return
      }
      // Reject rather than silently clamp — a warehouse operator expects
      // the quantity they typed to go through or fail visibly.
      if (data.quantity > chosen.quantity_available) {
        toast.error(
          `הכמות המבוקשת (${data.quantity}) חורגת מהאצווה (זמין: ${chosen.quantity_available}). בחר אצווה אחרת או צמצם כמות.`
        )
        return
      }
      picks = [{ batch_id: chosen.batch_id, quantity: data.quantity }]
    } else {
      picks = activeSuggestions
        .filter(s => s.suggested_quantity > 0)
        .map(s => ({
          batch_id: s.batch_id,
          quantity: s.suggested_quantity,
        }))
    }

    if (picks.length === 0) {
      toast.error('אין אצוות זמינות לליקוט')
      return
    }

    setSubmitting(true)
    try {
      const payload = {
        items: picks,
        customer_id: data.customer_id,
        reference_number: data.reference_number,
        notes: data.notes,
      }

      if (!isOnline()) {
        await addPendingOperation('pick', '/api/v1/picking/dispatch', 'POST', payload)
        toast.info('אתה במצב אופליין. הליקוט נשמר ויסונכרן כשתחזור לרשת.')
        reset()
        setSuggestions([])
        setSelectedBatchId(null)
        return
      }

      const response = await pickingApi.dispatch(payload)
      toast.success('הליקוט בוצע בהצלחה!')
      reset()
      setSuggestions([])
      setSelectedBatchId(null)
      setPostPickRef(response.reference_number)
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'שגיאה בביצוע ליקוט')
    } finally {
      setSubmitting(false)
    }
  }

  const activeSuggestions =
    activeStrategy === 'fifo' ? fifoSuggestions :
    activeStrategy === 'lifo' ? lifoSuggestions :
    suggestions

  return (
    <>
      {showScanner && (
        <BarcodeScanner
          onScan={handleBarcodeScanned}
          onClose={() => setShowScanner(false)}
        />
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle className="text-lg flex items-center gap-2">
              <PackageMinus className="w-5 h-5" />
              ליקוט ושליחה ללקוח
            </CardTitle>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit(handleDispatch)} className="space-y-4">
              <Button
                type="button"
                variant="outline"
                className="w-full h-16 flex items-center justify-center gap-3 border-dashed"
                onClick={() => setShowScanner(true)}
              >
                <Camera className="w-6 h-6 text-primary" />
                <span>סרוק פריט עם המצלמה</span>
              </Button>

              <div className="space-y-2">
                <Label htmlFor="item_id">{t('picking.selectItem')} *</Label>
                <select
                  id="item_id"
                  {...register('item_id')}
                  className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
                >
                  <option value="">בחר פריט...</option>
                  {items.map((item) => (
                    <option key={item.id} value={item.id}>
                      {item.sku} - {item.name}
                    </option>
                  ))}
                </select>
                {errors.item_id && (
                  <p className="text-sm text-destructive">{errors.item_id.message}</p>
                )}
                {selectedItem && !itemInStock && (
                  <div className="p-3 rounded-lg border border-destructive/30 bg-destructive/10 text-sm text-destructive">
                    הפריט הנבחר אינו קיים במלאי
                  </div>
                )}
                {selectedItem && itemInStock && (
                  <div className="p-3 rounded-lg bg-muted text-sm space-y-1">
                    <p><strong>ספק:</strong> {selectedItem.supplier}</p>
                    <p><strong>יח':</strong> {selectedItem.unit_of_measure}</p>
                    <p><strong>זמין לליקוט:</strong> {pickableQuantity}</p>
                  </div>
                )}
              </div>

              <div className="space-y-2">
                <Label htmlFor="quantity">{t('picking.quantity')} *</Label>
                <Input
                  id="quantity"
                  type="number"
                  step="1"
                  min={1}
                  inputMode="numeric"
                  disabled={!itemInStock}
                  {...register('quantity', { valueAsNumber: true })}
                  placeholder="0"
                />
                {errors.quantity && (
                  <p className="text-sm text-destructive">{errors.quantity.message}</p>
                )}
                {itemInStock && hasQuantity && !quantityInStock && (
                  <p className="text-sm text-destructive">
                    הכמות הנבחרת אינה קיימת במלאי
                  </p>
                )}
              </div>

              <div className="space-y-2">
                <Label htmlFor="customer_id">לקוח *</Label>
                <select
                  id="customer_id"
                  disabled={!canSelectCustomer}
                  {...register('customer_id')}
                  className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  <option value="">בחר לקוח...</option>
                  {customers.map((customer) => (
                    <option key={customer.id} value={customer.id}>
                      {customer.name}
                    </option>
                  ))}
                </select>
                {errors.customer_id && (
                  <p className="text-sm text-destructive">{errors.customer_id.message}</p>
                )}
              </div>

              <div className="space-y-2">
                <Label htmlFor="reference_number">{t('picking.reference')}</Label>
                <Input
                  id="reference_number"
                  {...register('reference_number')}
                  placeholder="מספר אסמכתא"
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="notes">הערות</Label>
                <Textarea
                  id="notes"
                  {...register('notes')}
                  placeholder="הערות..."
                  rows={2}
                />
              </div>

              <Button
                type="submit"
                className="w-full touch-manipulation"
                disabled={
                  !canFulfill ||
                  submitting ||
                  activeSuggestions.length === 0 ||
                  !canSelectCustomer
                }
              >
                {submitting ? (
                  <>
                    <Loader2 className="w-4 h-4 ml-2 animate-spin" />
                    מבצע ליקוט...
                  </>
                ) : (
                  <>
                    <PackageMinus className="w-4 h-4 ml-2" />
                    {t('picking.pick')}
                  </>
                )}
              </Button>
            </form>
          </CardContent>
        </Card>

        {/* Strategy Suggestions */}
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-lg">אצוות מוצעות</CardTitle>
            <div className="flex gap-1 mt-2">
              {(['fefo', 'fifo', 'lifo'] as const).map((s) => (
                <Button
                  key={s}
                  type="button"
                  variant={activeStrategy === s ? 'default' : 'outline'}
                  size="sm"
                  onClick={() => setActiveStrategy(s)}
                >
                  {s.toUpperCase()}
                </Button>
              ))}
            </div>
          </CardHeader>
          <CardContent>
            <BatchSuggestionsList
              loading={loading}
              suggestions={activeSuggestions}
              requestedQuantity={requestedQuantity || 0}
              totalAvailable={totalAvailable}
              canFulfill={canFulfill}
              strategyLabel={activeStrategy.toUpperCase()}
              hasItem={!!selectedItemId}
              selectedBatchId={selectedBatchId}
              onSelectBatch={(id) =>
                setSelectedBatchId(prev => (prev === id ? null : id))
              }
            />
          </CardContent>
        </Card>
      </div>

      <PostPickDialog
        open={postPickRef !== null}
        onOpenChange={(open) => {
          if (!open) setPostPickRef(null)
        }}
        referenceNumber={postPickRef}
      />
    </>
  )
}

// ===== CUSTOMER CONSUMPTION VIEW =====
function CustomerPickingView() {
  const [items, setItems] = useState<Item[]>([])
  const [suggestions, setSuggestions] = useState<SuggestedBatch[]>([])
  const [loading, setLoading] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [showScanner, setShowScanner] = useState(false)
  // Index into suggestions: which batch we're recommending
  const [recommendationIndex, setRecommendationIndex] = useState(0)
  const [showAllBatches, setShowAllBatches] = useState(false)

  const {
    register,
    reset,
    watch,
    setValue,
    formState: { errors },
  } = useForm<CustomerPickFormData>({
    resolver: zodResolver(customerPickSchema),
  })

  const selectedItemId = watch('item_id')
  const requestedQuantity = watch('quantity')

  useEffect(() => {
    fetchItems()
  }, [])

  useEffect(() => {
    if (selectedItemId) {
      fetchSuggestions()
      setRecommendationIndex(0)
      setShowAllBatches(false)
    } else {
      setSuggestions([])
    }
  }, [selectedItemId, requestedQuantity])

  async function fetchItems() {
    try {
      const response = await itemsApi.list({ page_size: 100 })
      setItems(response.items.filter(i => (i.total_quantity_available ?? 0) > 0))
    } catch (error) {
      console.error('Failed to fetch items:', error)
    }
  }

  async function fetchSuggestions() {
    if (!selectedItemId) return
    setLoading(true)
    try {
      const qty = requestedQuantity || 0
      const response = await pickingApi.suggestBatches(selectedItemId, qty)
      setSuggestions(response.suggestions || [])
    } catch (error: any) {
      console.error('Failed to fetch suggestions:', error)
      setSuggestions([])
    } finally {
      setLoading(false)
    }
  }

  const handleBarcodeScanned = async ({ code }: ScanResult): Promise<boolean> => {
    try {
      const result = await receivingApi.validateBarcode(code)
      if (result.valid && result.item) {
        setValue('item_id', result.item.id)
        toast.success(`נמצא: ${result.item.name} (${result.item.sku})`)
        if (navigator.vibrate) navigator.vibrate([100, 50, 100])
        return true
      }
      return false
    } catch {
      return false
    }
  }

  const handleConfirmBatch = async (batch: SuggestedBatch, notes?: string) => {
    setSubmitting(true)
    try {
      await pickingApi.consume({
        batch_id: batch.batch_id,
        quantity: batch.suggested_quantity,
        notes,
      })
      toast.success(`צריכה נרשמה — אצווה ${batch.batch_number}`)
      reset()
      setSuggestions([])
      setRecommendationIndex(0)
      setShowAllBatches(false)
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'שגיאה ברישום צריכה')
    } finally {
      setSubmitting(false)
    }
  }

  const handleReject = () => {
    if (recommendationIndex < suggestions.length - 1) {
      setRecommendationIndex(prev => prev + 1)
    } else {
      setShowAllBatches(true)
    }
  }

  const selectedItem = items.find(i => i.id === selectedItemId)
  const recommended = suggestions[recommendationIndex]
  const notes = watch('notes')

  return (
    <>
      {showScanner && (
        <BarcodeScanner
          onScan={handleBarcodeScanned}
          onClose={() => setShowScanner(false)}
        />
      )}

      <div className="max-w-xl mx-auto space-y-6">
        {/* Item & Quantity selection */}
        <Card>
          <CardHeader>
            <CardTitle className="text-lg flex items-center gap-2">
              <PackageMinus className="w-5 h-5" />
              רישום צריכת דיו
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <Button
              type="button"
              variant="outline"
              className="w-full h-16 flex items-center justify-center gap-3 border-dashed"
              onClick={() => setShowScanner(true)}
            >
              <Camera className="w-6 h-6 text-primary" />
              <span>סרוק פריט עם המצלמה</span>
            </Button>

            <div className="space-y-2">
              <Label htmlFor="c_item_id">בחר פריט *</Label>
              <select
                id="c_item_id"
                {...register('item_id')}
                className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
              >
                <option value="">בחר פריט...</option>
                {items.map((item) => (
                  <option key={item.id} value={item.id}>
                    {item.sku} - {item.name}
                  </option>
                ))}
              </select>
              {errors.item_id && (
                <p className="text-sm text-destructive">{errors.item_id.message}</p>
              )}
              {selectedItem && (
                <div className="p-3 rounded-lg bg-muted text-sm space-y-1">
                  <p><strong>ספק:</strong> {selectedItem.supplier}</p>
                  <p><strong>יח':</strong> {selectedItem.unit_of_measure}</p>
                </div>
              )}
            </div>

            <div className="space-y-2">
              <Label htmlFor="c_quantity">כמות *</Label>
              <Input
                id="c_quantity"
                type="number"
                step="1"
                min={1}
                inputMode="numeric"
                {...register('quantity', { valueAsNumber: true })}
                placeholder="0"
              />
              {errors.quantity && (
                <p className="text-sm text-destructive">{errors.quantity.message}</p>
              )}
            </div>

            <div className="space-y-2">
              <Label htmlFor="c_notes">הערות</Label>
              <Textarea
                id="c_notes"
                {...register('notes')}
                placeholder="הערות..."
                rows={2}
              />
            </div>
          </CardContent>
        </Card>

        {/* FEFO Recommendation */}
        {loading ? (
          <Card>
            <CardContent className="p-8 text-center text-muted-foreground">
              <Loader2 className="w-8 h-8 animate-spin mx-auto mb-2" />
              <p>מחפש אצוות...</p>
            </CardContent>
          </Card>
        ) : suggestions.length > 0 && !showAllBatches ? (
          <Card className="border-primary/30">
            <CardHeader className="pb-3">
              <CardTitle className="text-lg">
                המלצת המערכת (FEFO)
              </CardTitle>
              <p className="text-sm text-muted-foreground">
                המערכת ממליצה להשתמש באצווה הבאה — תפוגה הקרובה ביותר
              </p>
            </CardHeader>
            <CardContent className="space-y-4">
              {recommended && (
                <RecommendedBatchCard
                  batch={recommended}
                  onConfirm={() => handleConfirmBatch(recommended, notes)}
                  onReject={handleReject}
                  submitting={submitting}
                  isLast={recommendationIndex >= suggestions.length - 1}
                />
              )}
              {suggestions.length > 1 && (
                <p className="text-xs text-muted-foreground text-center">
                  המלצה {recommendationIndex + 1} מתוך {suggestions.length} אצוות זמינות
                </p>
              )}
            </CardContent>
          </Card>
        ) : showAllBatches && suggestions.length > 0 ? (
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">כל האצוות הזמינות</CardTitle>
              <p className="text-sm text-muted-foreground">
                בחר אצווה לצריכה
              </p>
            </CardHeader>
            <CardContent className="space-y-3">
              {suggestions.map((batch) => {
                const days = daysUntilExpiration(batch.expiration_date)
                const status = getExpirationStatus(days)
                return (
                  <div
                    key={batch.batch_id}
                    className="p-4 rounded-lg border bg-card hover:border-primary/50 transition-colors"
                  >
                    <div className="flex items-center justify-between mb-2">
                      <span className="font-mono text-sm font-medium">
                        {batch.batch_number}
                      </span>
                      <Badge variant={status}>{days} ימים</Badge>
                    </div>
                    <div className="flex justify-between text-sm mb-3">
                      <span className="text-muted-foreground">
                        תפוגה: {formatDate(batch.expiration_date)}
                      </span>
                      <span className="font-medium">
                        כמות: {batch.suggested_quantity}
                      </span>
                    </div>
                    <Button
                      size="sm"
                      className="w-full"
                      disabled={submitting}
                      onClick={() => handleConfirmBatch(batch, notes)}
                    >
                      {submitting ? (
                        <Loader2 className="w-4 h-4 animate-spin" />
                      ) : (
                        'בחר אצווה זו'
                      )}
                    </Button>
                  </div>
                )
              })}
            </CardContent>
          </Card>
        ) : null}
      </div>
    </>
  )
}

// ===== FEFO Recommendation Card (for customer view) =====
function RecommendedBatchCard({
  batch,
  onConfirm,
  onReject,
  submitting,
  isLast,
}: {
  batch: SuggestedBatch
  onConfirm: () => void
  onReject: () => void
  submitting: boolean
  isLast: boolean
}) {
  const days = daysUntilExpiration(batch.expiration_date)
  const status = getExpirationStatus(days)

  return (
    <div className="p-5 rounded-xl border-2 border-primary/20 bg-primary/5 space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <p className="font-mono text-lg font-semibold">{batch.batch_number}</p>
          {batch.location_code && (
            <p className="text-sm text-muted-foreground">מיקום: {batch.location_code}</p>
          )}
        </div>
        <Badge variant={status} className="text-base px-3 py-1">
          {days} ימים
        </Badge>
      </div>

      <div className="grid grid-cols-2 gap-3 text-sm">
        <div className="p-2 rounded-lg bg-background">
          <p className="text-muted-foreground">תפוגה</p>
          <p className="font-medium">{formatDate(batch.expiration_date)}</p>
        </div>
        <div className="p-2 rounded-lg bg-background">
          <p className="text-muted-foreground">כמות לצריכה</p>
          <p className="font-medium">{batch.suggested_quantity}</p>
        </div>
      </div>

      <div className="flex gap-3">
        <Button
          className="flex-1 h-14 text-base"
          disabled={submitting}
          onClick={onConfirm}
        >
          {submitting ? (
            <Loader2 className="w-5 h-5 animate-spin" />
          ) : (
            <>
              <ThumbsUp className="w-5 h-5 ml-2" />
              אישור
            </>
          )}
        </Button>
        <Button
          variant="outline"
          className="flex-1 h-14 text-base"
          disabled={submitting}
          onClick={onReject}
        >
          <ThumbsDown className="w-5 h-5 ml-2" />
          {isLast ? 'הצג הכל' : 'הבא'}
        </Button>
      </div>
    </div>
  )
}

// ===== Shared batch suggestions list (for admin view) =====
function BatchSuggestionsList({
  loading,
  suggestions,
  requestedQuantity,
  totalAvailable,
  canFulfill,
  strategyLabel,
  hasItem,
  selectedBatchId,
  onSelectBatch,
}: {
  loading: boolean
  suggestions: SuggestedBatch[]
  requestedQuantity: number
  totalAvailable: number
  canFulfill: boolean
  strategyLabel: string
  hasItem: boolean
  selectedBatchId: string | null
  onSelectBatch: (batchId: string) => void
}) {
  if (loading) {
    return (
      <div className="text-center py-8 text-muted-foreground">
        <Loader2 className="w-8 h-8 animate-spin mx-auto mb-2" />
        <p>מחפש אצוות...</p>
      </div>
    )
  }

  if (!hasItem) {
    return (
      <div className="text-center py-8 text-muted-foreground">
        <PackageMinus className="w-12 h-12 mx-auto mb-2 opacity-50" />
        <p>בחר פריט לקבלת הצעות</p>
      </div>
    )
  }

  if (suggestions.length === 0) {
    return (
      <div className="text-center py-8 text-muted-foreground">
        <PackageMinus className="w-12 h-12 mx-auto mb-2 opacity-50" />
        <p>אין אצוות זמינות לפריט זה</p>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {/* Fulfillment status */}
      {requestedQuantity > 0 && (
        canFulfill ? (
          <div className="p-4 rounded-lg bg-status-safe/10 border border-status-safe/30">
            <div className="flex items-center gap-2 text-status-safe mb-1">
              <CheckCircle2 className="w-5 h-5" />
              <span className="font-medium">ניתן לספק</span>
            </div>
            <p className="text-sm">
              זמין: {totalAvailable} / מבוקש: {requestedQuantity}
            </p>
          </div>
        ) : (
          <div className="p-4 rounded-lg bg-status-critical/10 border border-status-critical/30">
            <div className="flex items-center gap-2 text-status-critical mb-1">
              <AlertCircle className="w-5 h-5" />
              <span className="font-medium">מלאי לא מספיק</span>
            </div>
            <p className="text-sm text-status-critical">
              זמין: {totalAvailable} / מבוקש: {requestedQuantity}
            </p>
          </div>
        )
      )}

      <div className="space-y-2">
        <p className="text-sm font-medium">
          סדר מומלץ ({strategyLabel}) — לחץ על אצווה לבחירה ידנית:
        </p>
        {suggestions.map((batch, index) => {
          const days = daysUntilExpiration(batch.expiration_date)
          const status = getExpirationStatus(days)
          const isSelected = selectedBatchId === batch.batch_id
          return (
            <button
              key={batch.batch_id}
              type="button"
              onClick={() => onSelectBatch(batch.batch_id)}
              className={cn(
                'w-full text-right p-3 rounded-lg border bg-card transition-colors',
                'hover:border-primary/50 focus:outline-none focus-visible:ring-2 focus-visible:ring-ring',
                isSelected && 'border-primary bg-primary/5 ring-2 ring-primary/40',
              )}
              aria-pressed={isSelected}
            >
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  <Badge variant="secondary">#{index + 1}</Badge>
                  <span className="font-mono text-sm font-medium">
                    {batch.batch_number}
                  </span>
                  {isSelected && (
                    <Badge variant="safe">נבחר</Badge>
                  )}
                </div>
                <Badge variant={status}>{days} ימים</Badge>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-muted-foreground">
                  תפוגה: {formatDate(batch.expiration_date)}
                </span>
                <span className="text-muted-foreground">
                  זמין: {batch.quantity_available}
                </span>
                {batch.suggested_quantity > 0 && (
                  <span className="font-medium">
                    ליקוט: {batch.suggested_quantity}
                  </span>
                )}
              </div>
            </button>
          )
        })}
        {selectedBatchId && (
          <p className="text-xs text-muted-foreground">
            הליקוט יבוצע מאצווה אחת בלבד. לחץ שוב על האצווה לחזרה להקצאה אוטומטית.
          </p>
        )}
      </div>
    </div>
  )
}

// ===== MAIN PAGE =====
export function PickingPage() {
  const { t } = useTranslation()
  const { user } = useAuthStore()
  const isCustomer = user?.role === 'customer'

  return (
    <div className="space-y-6">
      <Header title={isCustomer ? 'צריכת דיו' : t('picking.title')} />
      {isCustomer ? <CustomerPickingView /> : <AdminPickingView />}
    </div>
  )
}
