import { useEffect } from 'react'
import { useForm, Controller } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { useTranslation } from 'react-i18next'
import { Loader2, HelpCircle } from 'lucide-react'

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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip'
import type { Item } from '@/lib/api'

const itemSchema = z.object({
  sku: z.string().min(1, 'מק"ט נדרש'),
  name: z.string().min(1, 'שם נדרש'),
  description: z.string().optional(),
  supplier: z.string().min(1, 'ספק נדרש'),
  unit_of_measure: z.string().min(1, 'יחידת מידה נדרשת'),
  cost_price: z.preprocess(
    (val) => {
      if (typeof val === 'string') {
        const num = parseFloat(val)
        return isNaN(num) ? 0 : num
      }
      return typeof val === 'number' ? val : 0
    },
    z.number().min(0, 'מחיר חייב להיות חיובי')
  ),
  currency: z.enum(['ILS', 'USD', 'EUR']).default('ILS'),
  reorder_point: z.preprocess(
    (val) => {
      if (val === '' || val === null || val === undefined) return undefined
      if (typeof val === 'string') {
        const num = parseInt(val, 10)
        return isNaN(num) ? undefined : num
      }
      return typeof val === 'number' ? val : undefined
    },
    z.number().min(0).optional()
  ),
  min_stock: z.preprocess(
    (val) => {
      if (val === '' || val === null || val === undefined) return undefined
      if (typeof val === 'string') {
        const num = parseInt(val, 10)
        return isNaN(num) ? undefined : num
      }
      return typeof val === 'number' ? val : undefined
    },
    z.number().min(0).optional()
  ),
  max_stock: z.preprocess(
    (val) => {
      if (val === '' || val === null || val === undefined) return undefined
      if (typeof val === 'string') {
        const num = parseInt(val, 10)
        return isNaN(num) ? undefined : num
      }
      return typeof val === 'number' ? val : undefined
    },
    z.number().min(0).optional()
  ),
})

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
    control,
    formState: { errors, isSubmitting },
  } = useForm<ItemFormData>({
    resolver: zodResolver(itemSchema),
    defaultValues: item
      ? {
          ...item,
          currency: 'ILS', // Default currency, can be extracted from item if stored
        }
      : {
          sku: '',
          name: '',
          description: '',
          supplier: '',
          unit_of_measure: 'ליטר',
          cost_price: 0,
          currency: 'ILS',
          reorder_point: 10,
          min_stock: 5,
          max_stock: 100,
        },
  })

  useEffect(() => {
    if (item) {
      reset({
        ...item,
        currency: 'ILS', // Default currency
      })
    } else {
      reset({
        sku: '',
        name: '',
        description: '',
        supplier: '',
        unit_of_measure: 'ליטר',
        cost_price: 0,
        currency: 'ILS',
        reorder_point: 10,
        min_stock: 5,
        max_stock: 100,
      })
    }
  }, [item, reset])

  const handleFormSubmit = async (data: ItemFormData) => {
    try {
      // Extract currency - backend doesn't have currency field yet
      // We'll store it in localStorage or handle it separately in the future
      const { currency, ...itemData } = data
      
      // Ensure cost_price is a number
      const submitData = {
        ...itemData,
        cost_price: typeof itemData.cost_price === 'string' 
          ? parseFloat(itemData.cost_price) 
          : itemData.cost_price,
      }
      
      await onSubmit(submitData as any)
      onOpenChange(false)
      reset()
    } catch (error) {
      console.error('Failed to save item:', error)
    }
  }

  return (
    <TooltipProvider>
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
              <div className="flex gap-2">
                <Input
                  id="cost_price"
                  type="number"
                  step="0.01"
                  {...register('cost_price', { valueAsNumber: false })}
                  placeholder="0.00"
                  className="flex-1"
                />
                <Controller
                  name="currency"
                  control={control}
                  render={({ field }) => (
                    <Select value={field.value} onValueChange={field.onChange}>
                      <SelectTrigger className="w-[120px]">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="ILS">₪ שקל</SelectItem>
                        <SelectItem value="USD">$ דולר</SelectItem>
                        <SelectItem value="EUR">€ אירו</SelectItem>
                      </SelectContent>
                    </Select>
                  )}
                />
              </div>
              {errors.cost_price && (
                <p className="text-sm text-destructive">{errors.cost_price.message}</p>
              )}
            </div>

            <div className="space-y-2">
              <div className="flex items-center gap-2">
                <Label htmlFor="reorder_point">{t('items.reorderPoint')}</Label>
                <TooltipProvider>
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <HelpCircle className="h-4 w-4 text-muted-foreground cursor-help" />
                    </TooltipTrigger>
                    <TooltipContent className="max-w-xs">
                      <p>
                        נקודת הזמנה היא הכמות המינימלית של הפריט במלאי. כאשר המלאי יורד מתחת לנקודה זו, המערכת תציג התראה כי יש להזמין עוד מהפריט.
                      </p>
                    </TooltipContent>
                  </Tooltip>
                </TooltipProvider>
              </div>
              <Input
                id="reorder_point"
                type="number"
                {...register('reorder_point', { valueAsNumber: false })}
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
    </TooltipProvider>
  )
}

