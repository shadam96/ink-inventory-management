import { useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { PackageMinus, AlertCircle, CheckCircle2, Loader2, Camera } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Textarea } from '@/components/ui/textarea'
import { Header } from '@/components/layout/Header'
import { BarcodeScanner } from '@/components/BarcodeScanner'
import { formatDate, daysUntilExpiration, getExpirationStatus } from '@/lib/utils'
import { itemsApi, customersApi, pickingApi, receivingApi, type Item } from '@/lib/api'
import { addPendingOperation, isOnline } from '@/lib/offline'

const pickSchema = z.object({
  item_id: z.string().min(1, 'פריט נדרש'),
  quantity: z.number().min(0.01, 'כמות חייבת להיות חיובית'),
  customer_id: z.string().min(1, 'לקוח נדרש'),
  reference_number: z.string().optional(),
  notes: z.string().optional(),
})

const pickSchemaTransform = pickSchema.transform((data) => ({
  ...data,
  quantity: Number(data.quantity),
}))

type PickFormData = z.infer<typeof pickSchema>

interface SuggestedBatch {
  batch_id: string
  batch_number: string
  quantity_to_pick: number
  expiration_date: string
  days_until_expiration: number
  warning_level: string
}

interface Customer {
  id: string
  name: string
}

export function PickingPage() {
  const { t } = useTranslation()
  const [items, setItems] = useState<Item[]>([])
  const [customers, setCustomers] = useState<Customer[]>([])
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
  } = useForm<PickFormData>({
    resolver: zodResolver(pickSchemaTransform) as any,
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
      setSuggestions(response.suggested_batches || [])
    } catch (error) {
      console.error('Failed to fetch suggestions:', error)
      setSuggestions([])
    } finally {
      setLoading(false)
    }
  }

  const handleBarcodeScanned = async (code: string) => {
    setShowScanner(false)
    
    try {
      const result = await receivingApi.validateBarcode(code)
      if (result.valid && result.item) {
        setValue('item_id', result.item.id)
        // Vibrate on success
        if (navigator.vibrate) {
          navigator.vibrate([100, 50, 100])
        }
      } else {
        alert('ברקוד לא נמצא')
      }
    } catch (error) {
      console.error('Failed to validate barcode:', error)
      alert('שגיאה בסריקת ברקוד')
    }
  }

  const handleDispatch = async (data: PickFormData) => {
    if (suggestions.length === 0) {
      alert('אין אצוות זמינות לליקוט')
      return
    }

    setSubmitting(true)
    try {
      const picks = suggestions.map(s => ({
        batch_id: s.batch_id,
        quantity: s.quantity_to_pick,
      }))

      const payload = {
        customer_id: data.customer_id,
        picks,
        reference_number: data.reference_number,
        notes: data.notes,
      }

      // Check if online
      if (!isOnline()) {
        await addPendingOperation('pick', '/api/v1/picking/dispatch', 'POST', payload)
        alert('אתה במצב אופליין. הליקוט נשמר ויסונכרן כשתחזור לרשת.')
        reset()
        setSuggestions([])
        return
      }

      await pickingApi.dispatch(payload)

      alert('הליקוט בוצע בהצלחה!')
      reset()
      setSuggestions([])
    } catch (error: any) {
      console.error('Failed to dispatch:', error)
      alert(error.response?.data?.detail || 'שגיאה בביצוע ליקוט')
    } finally {
      setSubmitting(false)
    }
  }

  const selectedItem = items.find(i => i.id === selectedItemId)
  const totalAvailable = suggestions.reduce((sum, s) => sum + s.quantity_to_pick, 0)
  const canFulfill = totalAvailable >= (requestedQuantity || 0)

  return (
    <div className="space-y-6">
      <Header title={t('picking.title')} />

      {/* Camera Scanner Modal */}
      {showScanner && (
        <BarcodeScanner
          onScan={handleBarcodeScanned}
          onClose={() => setShowScanner(false)}
        />
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mt-16">
        {/* Pick Form */}
        <Card>
          <CardHeader>
            <CardTitle className="text-lg flex items-center gap-2">
              <PackageMinus className="w-5 h-5" />
              פרטי ליקוט
            </CardTitle>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit(handleDispatch)} className="space-y-4">
              {/* Quick scan button */}
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
                  step="0.01"
                  inputMode="decimal"
                  {...register('quantity')}
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
            {loading ? (
              <div className="text-center py-8 text-muted-foreground">
                <Loader2 className="w-8 h-8 animate-spin mx-auto mb-2" />
                <p>מחפש אצוות...</p>
              </div>
            ) : suggestions.length === 0 ? (
              <div className="text-center py-8 text-muted-foreground">
                <PackageMinus className="w-12 h-12 mx-auto mb-2 opacity-50" />
                <p>בחר פריט וכמות לקבלת הצעות</p>
              </div>
            ) : (
              <div className="space-y-4">
                {/* Availability Status */}
                {canFulfill ? (
                  <div className="p-4 rounded-lg bg-status-safe/10 border border-status-safe/30">
                    <div className="flex items-center gap-2 text-status-safe mb-1">
                      <CheckCircle2 className="w-5 h-5" />
                      <span className="font-medium">ניתן לספק</span>
                    </div>
                    <p className="text-sm">
                      זמין: {totalAvailable.toFixed(2)} / מבוקש: {(requestedQuantity || 0).toFixed(2)}
                    </p>
                  </div>
                ) : (
                  <div className="p-4 rounded-lg bg-status-critical/10 border border-status-critical/30">
                    <div className="flex items-center gap-2 text-status-critical mb-1">
                      <AlertCircle className="w-5 h-5" />
                      <span className="font-medium">מלאי לא מספיק</span>
                    </div>
                    <p className="text-sm">
                      זמין: {totalAvailable.toFixed(2)} / מבוקש: {(requestedQuantity || 0).toFixed(2)}
                    </p>
                  </div>
                )}

                {/* Batch List */}
                <div className="space-y-2">
                  <p className="text-sm font-medium">אצוות מוצעות (FEFO):</p>
                  {suggestions.map((batch, index) => {
                    const days = daysUntilExpiration(batch.expiration_date)
                    const status = getExpirationStatus(days)
                    
                    return (
                      <div
                        key={batch.batch_id}
                        className="p-3 rounded-lg border bg-card"
                      >
                        <div className="flex items-center justify-between mb-2">
                          <div className="flex items-center gap-2">
                            <Badge variant="secondary">#{index + 1}</Badge>
                            <span className="font-mono text-sm font-medium">
                              {batch.batch_number}
                            </span>
                          </div>
                          <Badge variant={status}>
                            {days} ימים
                          </Badge>
                        </div>
                        <div className="flex justify-between text-sm">
                          <span className="text-muted-foreground">
                            תפוגה: {formatDate(batch.expiration_date)}
                          </span>
                          <span className="font-medium">
                            כמות: {batch.quantity_to_pick.toFixed(2)}
                          </span>
                        </div>
                      </div>
                    )
                  })}
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
