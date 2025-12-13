import { useEffect } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { useTranslation } from 'react-i18next'
import { Loader2 } from 'lucide-react'

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
import type { Item } from '@/lib/api'

const itemSchema = z.object({
  sku: z.string().min(1, 'מק"ט נדרש'),
  name: z.string().min(1, 'שם נדרש'),
  description: z.string().optional(),
  supplier: z.string().min(1, 'ספק נדרש'),
  unit_of_measure: z.string().min(1, 'יחידת מידה נדרשת'),
  cost_price: z.number().min(0, 'מחיר חייב להיות חיובי'),
  reorder_point: z.number().min(0).optional(),
  min_stock: z.number().min(0).optional(),
  max_stock: z.number().min(0).optional(),
})

const itemSchemaTransform = itemSchema.transform((data) => ({
  ...data,
  cost_price: Number(data.cost_price),
  reorder_point: data.reorder_point ? Number(data.reorder_point) : undefined,
  min_stock: data.min_stock ? Number(data.min_stock) : undefined,
  max_stock: data.max_stock ? Number(data.max_stock) : undefined,
}))

type ItemFormData = z.infer<typeof itemSchema>

interface ItemDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  item?: Item | null
  onSubmit: (data: ItemFormData) => Promise<void>
}

export function ItemDialog({ open, onOpenChange, item, onSubmit }: ItemDialogProps) {
  const { t } = useTranslation()
  const isEdit = !!item

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<ItemFormData>({
    resolver: zodResolver(itemSchemaTransform) as any,
    defaultValues: item || {
      sku: '',
      name: '',
      description: '',
      supplier: '',
      unit_of_measure: 'ליטר',
      cost_price: 0,
      reorder_point: 10,
      min_stock: 5,
      max_stock: 100,
    },
  })

  useEffect(() => {
    if (item) {
      reset(item)
    } else {
      reset({
        sku: '',
        name: '',
        description: '',
        supplier: '',
        unit_of_measure: 'ליטר',
        cost_price: 0,
        reorder_point: 10,
        min_stock: 5,
        max_stock: 100,
      })
    }
  }, [item, reset])

  const handleFormSubmit = async (data: ItemFormData) => {
    try {
      await onSubmit(data)
      onOpenChange(false)
      reset()
    } catch (error) {
      console.error('Failed to save item:', error)
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>
            {isEdit ? t('items.edit') : t('items.add')}
          </DialogTitle>
        </DialogHeader>

        <form onSubmit={handleSubmit(handleFormSubmit)} className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="sku">{t('items.sku')} *</Label>
              <Input
                id="sku"
                {...register('sku')}
                placeholder="INK-001"
                disabled={isEdit}
              />
              {errors.sku && (
                <p className="text-sm text-destructive">{errors.sku.message}</p>
              )}
            </div>

            <div className="space-y-2">
              <Label htmlFor="name">{t('items.name')} *</Label>
              <Input
                id="name"
                {...register('name')}
                placeholder="דיו שחור"
              />
              {errors.name && (
                <p className="text-sm text-destructive">{errors.name.message}</p>
              )}
            </div>
          </div>

          <div className="space-y-2">
            <Label htmlFor="description">{t('items.description')}</Label>
            <Textarea
              id="description"
              {...register('description')}
              placeholder="תיאור הפריט..."
              rows={2}
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="supplier">{t('items.supplier')} *</Label>
              <Input
                id="supplier"
                {...register('supplier')}
                placeholder="ספק דיו"
              />
              {errors.supplier && (
                <p className="text-sm text-destructive">{errors.supplier.message}</p>
              )}
            </div>

            <div className="space-y-2">
              <Label htmlFor="unit_of_measure">{t('items.unit')} *</Label>
              <Input
                id="unit_of_measure"
                {...register('unit_of_measure')}
                placeholder="ליטר"
              />
              {errors.unit_of_measure && (
                <p className="text-sm text-destructive">{errors.unit_of_measure.message}</p>
              )}
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="cost_price">{t('items.costPrice')} *</Label>
              <Input
                id="cost_price"
                type="number"
                step="0.01"
                {...register('cost_price')}
                placeholder="0.00"
              />
              {errors.cost_price && (
                <p className="text-sm text-destructive">{errors.cost_price.message}</p>
              )}
            </div>

            <div className="space-y-2">
              <Label htmlFor="reorder_point">{t('items.reorderPoint')}</Label>
              <Input
                id="reorder_point"
                type="number"
                {...register('reorder_point')}
                placeholder="10"
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="min_stock">{t('items.minStock')}</Label>
              <Input
                id="min_stock"
                type="number"
                {...register('min_stock')}
                placeholder="5"
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="max_stock">{t('items.maxStock')}</Label>
              <Input
                id="max_stock"
                type="number"
                {...register('max_stock')}
                placeholder="100"
              />
            </div>
          </div>

          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={() => onOpenChange(false)}
              disabled={isSubmitting}
            >
              {t('common.cancel')}
            </Button>
            <Button type="submit" disabled={isSubmitting}>
              {isSubmitting ? (
                <>
                  <Loader2 className="w-4 h-4 ml-2 animate-spin" />
                  {t('common.loading')}
                </>
              ) : (
                t('common.save')
              )}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}

