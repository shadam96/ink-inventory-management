import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Loader2, Plus, X } from 'lucide-react'
import { toast } from 'sonner'

import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Badge } from '@/components/ui/badge'
import { customersApi, itemsApi, pickingApi, deliveryNotesApi, type Customer, type Item } from '@/lib/api'

interface BatchOption {
  batch_id: string
  batch_number: string
  quantity_available: number
  expiration_date: string
}

interface LineItem {
  id: string
  item_id: string
  item_name: string
  item_sku: string
  batch_id: string
  batch_number: string
  quantity: number
}

interface CreateDeliveryNoteDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  onCreated: () => void
}

export function CreateDeliveryNoteDialog({ open, onOpenChange, onCreated }: CreateDeliveryNoteDialogProps) {
  const { t } = useTranslation()
  const [customers, setCustomers] = useState<Customer[]>([])
  const [items, setItems] = useState<Item[]>([])
  const [customerId, setCustomerId] = useState('')
  const [itemId, setItemId] = useState('')
  const [batchId, setBatchId] = useState('')
  const [batchOptions, setBatchOptions] = useState<BatchOption[]>([])
  const [quantity, setQuantity] = useState<number | ''>('')
  const [notes, setNotes] = useState('')
  const [lines, setLines] = useState<LineItem[]>([])
  const [submitting, setSubmitting] = useState(false)

  useEffect(() => {
    if (!open) return
    customersApi.list({ page_size: 100, is_active: true }).then((res) => {
      setCustomers(res.items || [])
    }).catch((error) => {
      console.error('Failed to fetch customers:', error)
    })
    itemsApi.list({ page_size: 100 }).then((res) => {
      setItems(res.items || [])
    }).catch((error) => {
      console.error('Failed to fetch items:', error)
    })
  }, [open])

  useEffect(() => {
    if (!itemId) {
      setBatchOptions([])
      setBatchId('')
      return
    }
    pickingApi.suggestBatches(itemId).then((res) => {
      const options: BatchOption[] = (res.suggestions || []).map((s: any) => ({
        batch_id: s.batch_id,
        batch_number: s.batch_number,
        quantity_available: s.quantity_available,
        expiration_date: s.expiration_date,
      }))
      setBatchOptions(options)
      setBatchId('')
    }).catch((error) => {
      console.error('Failed to fetch batches:', error)
      setBatchOptions([])
    })
  }, [itemId])

  const resetForm = () => {
    setCustomerId('')
    setItemId('')
    setBatchId('')
    setBatchOptions([])
    setQuantity('')
    setNotes('')
    setLines([])
  }

  const handleOpenChange = (nextOpen: boolean) => {
    if (submitting) return
    if (!nextOpen) resetForm()
    onOpenChange(nextOpen)
  }

  const handleAddLine = () => {
    const item = items.find(i => i.id === itemId)
    const batch = batchOptions.find(b => b.batch_id === batchId)
    if (!item || !batch || !quantity || quantity <= 0) return

    setLines([...lines, {
      id: `${batch.batch_id}-${Date.now()}`,
      item_id: item.id,
      item_name: item.name,
      item_sku: item.sku,
      batch_id: batch.batch_id,
      batch_number: batch.batch_number,
      quantity,
    }])
    setItemId('')
    setBatchId('')
    setQuantity('')
  }

  const handleRemoveLine = (id: string) => {
    setLines(lines.filter(l => l.id !== id))
  }

  const handleSubmit = async () => {
    if (!customerId || lines.length === 0) return
    setSubmitting(true)
    try {
      await deliveryNotesApi.create({
        customer_id: customerId,
        items: lines.map(l => ({ batch_id: l.batch_id, quantity: l.quantity })),
        notes: notes || undefined,
      })
      toast.success(t('deliveryNotes.createSuccess'))
      resetForm()
      onOpenChange(false)
      onCreated()
    } catch (error: any) {
      console.error('Failed to create delivery note:', error)
      toast.error(error?.response?.data?.detail || t('deliveryNotes.createError'))
    } finally {
      setSubmitting(false)
    }
  }

  const selectedBatch = batchOptions.find(b => b.batch_id === batchId)

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>{t('deliveryNotes.create')}</DialogTitle>
        </DialogHeader>

        <div className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="dn_customer">{t('deliveryNotes.customer')} *</Label>
            <select
              id="dn_customer"
              value={customerId}
              onChange={(e) => setCustomerId(e.target.value)}
              className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
            >
              <option value="">{t('picking.selectCustomerPlaceholder')}</option>
              {customers.map((c) => (
                <option key={c.id} value={c.id}>{c.name}</option>
              ))}
            </select>
          </div>

          <div className="rounded-lg border p-3 space-y-3">
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              <div className="space-y-2 sm:col-span-2">
                <Label htmlFor="dn_item">{t('picking.selectItem')}</Label>
                <select
                  id="dn_item"
                  value={itemId}
                  onChange={(e) => setItemId(e.target.value)}
                  className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
                >
                  <option value="">{t('picking.selectItemPlaceholder')}</option>
                  {items.map((i) => (
                    <option key={i.id} value={i.id}>{i.sku} - {i.name}</option>
                  ))}
                </select>
              </div>

              <div className="space-y-2">
                <Label htmlFor="dn_quantity">{t('receiving.quantity')}</Label>
                <Input
                  id="dn_quantity"
                  type="number"
                  step="0.001"
                  min={0.001}
                  max={selectedBatch?.quantity_available}
                  value={quantity}
                  onChange={(e) => setQuantity(e.target.value === '' ? '' : Number(e.target.value))}
                  disabled={!itemId}
                />
              </div>
            </div>

            <div className="space-y-2">
              <Label htmlFor="dn_batch">{t('deliveryNotes.batch')}</Label>
              <select
                id="dn_batch"
                value={batchId}
                onChange={(e) => setBatchId(e.target.value)}
                disabled={batchOptions.length === 0}
                className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
              >
                <option value="">{t('picking.noBatchesForItem')}</option>
                {batchOptions.map((b) => (
                  <option key={b.batch_id} value={b.batch_id}>
                    {b.batch_number} — {t('picking.availableLabel')}: {b.quantity_available}
                  </option>
                ))}
              </select>
            </div>

            <Button
              type="button"
              variant="outline"
              className="w-full"
              onClick={handleAddLine}
              disabled={!batchId || !quantity || quantity <= 0 || (selectedBatch ? quantity > selectedBatch.quantity_available : false)}
            >
              <Plus className="w-4 h-4 me-2" />
              {t('receiving.addToList')}
            </Button>
          </div>

          {lines.length > 0 && (
            <div className="space-y-2">
              {lines.map((line) => (
                <div key={line.id} className="flex items-center justify-between p-3 rounded-lg border bg-card">
                  <div className="flex items-center gap-3">
                    <Badge variant="secondary" className="font-mono">{line.item_sku}</Badge>
                    <span className="font-medium">{line.item_name}</span>
                    <span className="text-sm text-muted-foreground">{line.batch_number} · {line.quantity}</span>
                  </div>
                  <Button variant="ghost" size="icon" onClick={() => handleRemoveLine(line.id)} className="text-destructive">
                    <X className="w-4 h-4" />
                  </Button>
                </div>
              ))}
            </div>
          )}

          <div className="space-y-2">
            <Label htmlFor="dn_notes">{t('common.notes')}</Label>
            <Textarea
              id="dn_notes"
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              rows={2}
            />
          </div>
        </div>

        <DialogFooter>
          <Button type="button" variant="outline" onClick={() => handleOpenChange(false)} disabled={submitting}>
            {t('common.cancel')}
          </Button>
          <Button
            type="button"
            onClick={handleSubmit}
            disabled={submitting || !customerId || lines.length === 0}
          >
            {submitting ? (
              <>
                <Loader2 className="w-4 h-4 me-2 animate-spin" />
                {t('common.loading')}
              </>
            ) : (
              t('common.save')
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
