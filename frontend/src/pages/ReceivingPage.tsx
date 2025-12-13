import { useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { PackagePlus, Barcode, Plus, X, Loader2, Camera } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Textarea } from '@/components/ui/textarea'
import { Header } from '@/components/layout/Header'
import { BarcodeScanner } from '@/components/BarcodeScanner'
import { itemsApi, receivingApi, type Item } from '@/lib/api'
import { addPendingOperation, isOnline } from '@/lib/offline'

const receiveSchema = z.object({
  item_id: z.string().min(1, 'פריט נדרש'),
  quantity: z.number().min(0.01, 'כמות חייבת להיות חיובית'),
  expiration_date: z.string().min(1, 'תאריך תפוגה נדרש'),
  batch_number: z.string().optional(),
  notes: z.string().optional(),
})

const receiveSchemaTransform = receiveSchema.transform((data) => ({
  ...data,
  quantity: Number(data.quantity),
}))

type ReceiveFormData = z.infer<typeof receiveSchema>

interface ReceiveItem extends ReceiveFormData {
  id: string
  item_name?: string
  item_sku?: string
}

export function ReceivingPage() {
  const { t } = useTranslation()
  const [items, setItems] = useState<Item[]>([])
  const [receiveList, setReceiveList] = useState<ReceiveItem[]>([])
  const [barcode, setBarcode] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [showScanner, setShowScanner] = useState(false)

  const {
    register,
    handleSubmit,
    reset,
    setValue,
    watch,
    formState: { errors },
  } = useForm<ReceiveFormData>({
    resolver: zodResolver(receiveSchemaTransform) as any,
    defaultValues: {
      quantity: 1,
      expiration_date: new Date(Date.now() + 180 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
    },
  })

  const selectedItemId = watch('item_id')

  useEffect(() => {
    fetchItems()
  }, [])

  async function fetchItems() {
    try {
      const response = await itemsApi.list({ page_size: 100 })
      setItems(response.items)
    } catch (error) {
      console.error('Failed to fetch items:', error)
    }
  }

  const handleBarcodeScanned = async (code: string) => {
    setShowScanner(false)
    setBarcode(code)
    
    try {
      const result = await receivingApi.validateBarcode(code)
      if (result.valid && result.item) {
        setValue('item_id', result.item.id)
        setBarcode('')
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

  const handleBarcodeSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!barcode.trim()) return
    await handleBarcodeScanned(barcode)
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
    reset({
      item_id: '',
      quantity: 1,
      expiration_date: new Date(Date.now() + 180 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
      batch_number: '',
      notes: '',
    })
  }

  const handleRemoveFromList = (id: string) => {
    setReceiveList(receiveList.filter(item => item.id !== id))
  }

  const handleReceiveAll = async () => {
    if (receiveList.length === 0) return

    setSubmitting(true)
    try {
      const payload = receiveList.length === 1
        ? {
            item_id: receiveList[0].item_id,
            quantity: receiveList[0].quantity,
            expiration_date: receiveList[0].expiration_date,
            batch_number: receiveList[0].batch_number,
            notes: receiveList[0].notes,
          }
        : {
            items: receiveList.map(item => ({
              item_id: item.item_id,
              quantity: item.quantity,
              expiration_date: item.expiration_date,
              batch_number: item.batch_number,
              notes: item.notes,
            })),
          }

      // Check if online
      if (!isOnline()) {
        // Save for later sync
        await addPendingOperation(
          'receive',
          receiveList.length === 1 ? '/api/v1/receiving/' : '/api/v1/receiving/multiple',
          'POST',
          payload
        )
        alert('אתה במצב אופליין. הקליטה נשמרה ותסונכרן כשתחזור לרשת.')
        setReceiveList([])
        return
      }

      if (receiveList.length === 1) {
        await receivingApi.receive(payload as any)
      } else {
        await receivingApi.receiveMultiple(payload as any)
      }

      alert('הסחורה נקלטה בהצלחה!')
      setReceiveList([])
    } catch (error: any) {
      console.error('Failed to receive items:', error)
      alert(error.response?.data?.detail || 'שגיאה בקליטת סחורה')
    } finally {
      setSubmitting(false)
    }
  }

  const selectedItem = items.find(i => i.id === selectedItemId)

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

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mt-16">
        {/* Barcode Scanner */}
        <Card className="lg:col-span-1">
          <CardHeader>
            <CardTitle className="text-lg flex items-center gap-2">
              <Barcode className="w-5 h-5" />
              {t('receiving.scanBarcode')}
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {/* Camera scan button for mobile */}
            <Button
              type="button"
              variant="outline"
              className="w-full h-24 flex flex-col gap-2 border-dashed"
              onClick={() => setShowScanner(true)}
            >
              <Camera className="w-8 h-8 text-primary" />
              <span>סרוק עם המצלמה</span>
            </Button>

            <div className="relative">
              <div className="absolute inset-0 flex items-center">
                <span className="w-full border-t" />
              </div>
              <div className="relative flex justify-center text-xs uppercase">
                <span className="bg-card px-2 text-muted-foreground">או הזן ידנית</span>
              </div>
            </div>

            <form onSubmit={handleBarcodeSubmit} className="space-y-4">
              <div>
                <Input
                  placeholder="הזן ברקוד..."
                  value={barcode}
                  onChange={(e) => setBarcode(e.target.value)}
                  className="font-mono"
                />
              </div>
              <Button type="submit" className="w-full" disabled={!barcode}>
                בדוק ברקוד
              </Button>
            </form>
          </CardContent>
        </Card>

        {/* Receive Form */}
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle className="text-lg flex items-center gap-2">
              <PackagePlus className="w-5 h-5" />
              קבלת סחורה
            </CardTitle>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit(handleAddToList)} className="space-y-4">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="col-span-1 sm:col-span-2 space-y-2">
                  <Label htmlFor="item_id">{t('receiving.selectItem')} *</Label>
                  <select
                    id="item_id"
                    {...register('item_id')}
                    className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
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
                  <Label htmlFor="quantity">{t('receiving.quantity')} *</Label>
                  <Input
                    id="quantity"
                    type="number"
                    step="0.01"
                    inputMode="decimal"
                    {...register('quantity')}
                  />
                  {errors.quantity && (
                    <p className="text-sm text-destructive">{errors.quantity.message}</p>
                  )}
                </div>

                <div className="space-y-2">
                  <Label htmlFor="expiration_date">{t('receiving.expirationDate')} *</Label>
                  <Input
                    id="expiration_date"
                    type="date"
                    {...register('expiration_date')}
                  />
                  {errors.expiration_date && (
                    <p className="text-sm text-destructive">{errors.expiration_date.message}</p>
                  )}
                </div>

                <div className="col-span-1 sm:col-span-2 space-y-2">
                  <Label htmlFor="batch_number">{t('receiving.batchNumber')}</Label>
                  <Input
                    id="batch_number"
                    {...register('batch_number')}
                    placeholder="מספר אצווה (יווצר אוטומטית אם לא צוין)"
                  />
                </div>

                <div className="col-span-1 sm:col-span-2 space-y-2">
                  <Label htmlFor="notes">{t('receiving.notes')}</Label>
                  <Textarea
                    id="notes"
                    {...register('notes')}
                    placeholder="הערות..."
                    rows={2}
                  />
                </div>
              </div>

              <Button type="submit" className="w-full">
                <Plus className="w-4 h-4 ml-2" />
                הוסף לרשימה
              </Button>
            </form>
          </CardContent>
        </Card>
      </div>

      {/* Receive List */}
      {receiveList.length > 0 && (
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between flex-wrap gap-4">
              <CardTitle className="text-lg">רשימת קבלה ({receiveList.length} פריטים)</CardTitle>
              <Button
                onClick={handleReceiveAll}
                disabled={submitting}
                className="touch-manipulation"
              >
                {submitting ? (
                  <>
                    <Loader2 className="w-4 h-4 ml-2 animate-spin" />
                    מקליט...
                  </>
                ) : (
                  <>
                    <PackagePlus className="w-4 h-4 ml-2" />
                    קלוט הכל
                  </>
                )}
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {receiveList.map((item) => (
                <div
                  key={item.id}
                  className="flex items-center justify-between p-4 rounded-lg border bg-card"
                >
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-3 mb-2 flex-wrap">
                      <Badge variant="secondary" className="font-mono">
                        {item.item_sku}
                      </Badge>
                      <span className="font-medium truncate">{item.item_name}</span>
                    </div>
                    <div className="flex gap-4 flex-wrap text-sm text-muted-foreground">
                      <span>כמות: {item.quantity}</span>
                      <span>תפוגה: {new Date(item.expiration_date).toLocaleDateString('he-IL')}</span>
                      {item.batch_number && <span>אצווה: {item.batch_number}</span>}
                    </div>
                    {item.notes && (
                      <p className="text-sm text-muted-foreground mt-1 truncate">{item.notes}</p>
                    )}
                  </div>
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={() => handleRemoveFromList(item.id)}
                    className="text-destructive flex-shrink-0 touch-manipulation"
                  >
                    <X className="w-4 h-4" />
                  </Button>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
