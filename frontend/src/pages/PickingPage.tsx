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
import { formatDate, daysUntilExpiration, getExpirationStatus } from '@/lib/utils'
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
function AdminPickingView() {
  const { t } = useTranslation()
  const [items, setItems] = useState<Item[]>([])
  const [customers, setCustomers] = useState<CustomerInfo[]>([])
  const [suggestions, setSuggestions] = useState<SuggestedBatch[]>([])
  const [loading, setLoading] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [showScanner, setShowScanner] = useState(false)

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

  useEffect(() => {
    fetchItems()
    fetchCustomers()
  }, [])

  useEffect(() => {
    if (selectedItemId && requestedQuantity > 0) {
      fetchSuggestions()
    } else {
      setSuggestions([])
    }
  }, [selectedItemId, requestedQuantity])

  async function fetchItems() {
    try {
      const response = await itemsApi.list({ page_size: 100 })
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
    if (!selectedItemId || !requestedQuantity) return
    setLoading(true)
    try {
      const response = await pickingApi.suggestBatches(selectedItemId, requestedQuantity)
      setSuggestions(response.suggestions || [])
    } catch (error) {
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

  const handleDispatch = async (data: AdminPickFormData) => {
    if (suggestions.length === 0) {
      toast.error('אין אצוות זמינות לליקוט')
      return
    }

    setSubmitting(true)
    try {
      const picks = suggestions.map(s => ({
        batch_id: s.batch_id,
        quantity: s.suggested_quantity,
      }))

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
        return
      }

      await pickingApi.dispatch(payload)
      toast.success('הליקוט בוצע בהצלחה!')
      reset()
      setSuggestions([])
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'שגיאה בביצוע ליקוט')
    } finally {
      setSubmitting(false)
    }
  }

  const selectedItem = items.find(i => i.id === selectedItemId)
  const totalPick = suggestions.reduce((sum, s) => sum + s.suggested_quantity, 0)
  const canFulfill = totalPick >= (requestedQuantity || 0)

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
                {selectedItem && (
                  <div className="p-3 rounded-lg bg-muted text-sm space-y-1">
                    <p><strong>ספק:</strong> {selectedItem.supplier}</p>
                    <p><strong>יח':</strong> {selectedItem.unit_of_measure}</p>
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
                  {...register('quantity', { valueAsNumber: true })}
                  placeholder="0"
                />
                {errors.quantity && (
                  <p className="text-sm text-destructive">{errors.quantity.message}</p>
                )}
              </div>

              <div className="space-y-2">
                <Label htmlFor="customer_id">לקוח *</Label>
                <select
                  id="customer_id"
                  {...register('customer_id')}
                  className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
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
                disabled={!canFulfill || submitting || suggestions.length === 0}
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

        {/* FEFO Suggestions */}
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">{t('picking.suggestedBatches')} (FEFO)</CardTitle>
          </CardHeader>
          <CardContent>
            <BatchSuggestionsList
              loading={loading}
              suggestions={suggestions}
              requestedQuantity={requestedQuantity || 0}
            />
          </CardContent>
        </Card>
      </div>
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
    if (selectedItemId && requestedQuantity > 0) {
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
      setItems(response.items)
    } catch (error) {
      console.error('Failed to fetch items:', error)
    }
  }

  async function fetchSuggestions() {
    if (!selectedItemId || !requestedQuantity) return
    setLoading(true)
    try {
      const response = await pickingApi.suggestBatches(selectedItemId, requestedQuantity)
      setSuggestions(response.suggestions || [])
    } catch (error: any) {
      if (error.response?.status === 400) {
        toast.error(error.response.data?.detail || 'כמות לא מספיקה במלאי')
      }
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
}: {
  loading: boolean
  suggestions: SuggestedBatch[]
  requestedQuantity: number
}) {
  const totalPick = suggestions.reduce((sum, s) => sum + s.suggested_quantity, 0)
  const canFulfill = totalPick >= requestedQuantity

  if (loading) {
    return (
      <div className="text-center py-8 text-muted-foreground">
        <Loader2 className="w-8 h-8 animate-spin mx-auto mb-2" />
        <p>מחפש אצוות...</p>
      </div>
    )
  }

  if (suggestions.length === 0) {
    return (
      <div className="text-center py-8 text-muted-foreground">
        <PackageMinus className="w-12 h-12 mx-auto mb-2 opacity-50" />
        <p>בחר פריט וכמות לקבלת הצעות</p>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {canFulfill ? (
        <div className="p-4 rounded-lg bg-status-safe/10 border border-status-safe/30">
          <div className="flex items-center gap-2 text-status-safe mb-1">
            <CheckCircle2 className="w-5 h-5" />
            <span className="font-medium">ניתן לספק</span>
          </div>
          <p className="text-sm">
            זמין: {totalPick.toFixed(2)} / מבוקש: {requestedQuantity.toFixed(2)}
          </p>
        </div>
      ) : (
        <div className="p-4 rounded-lg bg-status-critical/10 border border-status-critical/30">
          <div className="flex items-center gap-2 text-status-critical mb-1">
            <AlertCircle className="w-5 h-5" />
            <span className="font-medium">מלאי לא מספיק</span>
          </div>
          <p className="text-sm">
            זמין: {totalPick.toFixed(2)} / מבוקש: {requestedQuantity.toFixed(2)}
          </p>
        </div>
      )}

      <div className="space-y-2">
        <p className="text-sm font-medium">אצוות מוצעות (FEFO):</p>
        {suggestions.map((batch, index) => {
          const days = daysUntilExpiration(batch.expiration_date)
          const status = getExpirationStatus(days)
          return (
            <div key={batch.batch_id} className="p-3 rounded-lg border bg-card">
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  <Badge variant="secondary">#{index + 1}</Badge>
                  <span className="font-mono text-sm font-medium">
                    {batch.batch_number}
                  </span>
                </div>
                <Badge variant={status}>{days} ימים</Badge>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-muted-foreground">
                  תפוגה: {formatDate(batch.expiration_date)}
                </span>
                <span className="font-medium">
                  כמות: {batch.suggested_quantity}
                </span>
              </div>
            </div>
          )
        })}
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
