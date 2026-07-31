import { useEffect } from 'react'
import { useForm, Controller } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { useTranslation } from 'react-i18next'
import { Loader2, HelpCircle } from 'lucide-react'
import { useUIStore } from '@/store/ui'

import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { QuantityInput } from '@/components/ui/quantity-input'
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
import type { Item, CreateItemData } from '@/lib/api'

// Validation messages are stored as i18n key paths and resolved
// at render time with `t()`, so they reflect the active language.
const itemSchema = z.object({
  sku: z.string().min(1, 'items.skuRequired'),
  barcode: z.string().max(50).optional().or(z.literal('')),
  name: z.string().min(1, 'items.nameRequired'),
  description: z.string().optional(),
  supplier: z.string().min(1, 'items.supplierRequired'),
  unit_of_measure: z.string().min(1, 'items.unitRequired'),
  color: z.enum(['cyan', 'magenta', 'yellow', 'black', 'white', 'other']),
  cost_price: z.number().min(0, 'items.costPriceInvalid'),
  currency: z.enum(['ILS', 'USD', 'EUR', 'TRY']),
  reorder_point: z.number().int('items.reorderPointInvalid').min(0).optional(),
  min_stock: z.number().int('items.minStockInvalid').min(0).optional(),
  max_stock: z.number().int('items.maxStockInvalid').min(0).optional(),
})

type ItemFormData = z.infer<typeof itemSchema>

interface ItemDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  item?: Item | null
  onSubmit: (data: CreateItemData) => Promise<void>
}

export function ItemDialog({ open, onOpenChange, item, onSubmit }: ItemDialogProps) {
  const { t } = useTranslation()
  const isEdit = !!item
  const { currency: defaultCurrency } = useUIStore()

  const {
    register,
    handleSubmit,
    reset,
    control,
    watch,
    formState: { errors, isSubmitting },
  } = useForm<ItemFormData>({
    resolver: zodResolver(itemSchema),
    defaultValues: item
      ? {
          ...item,
          barcode: item.barcode || '',
          currency: item.currency || defaultCurrency,
          color: item.color || 'other',
        }
      : {
          sku: '',
          barcode: '',
          name: '',
          description: '',
          supplier: '',
          unit_of_measure: '',
          color: 'other',
          cost_price: 0,
          currency: defaultCurrency,
          reorder_point: 10,
          min_stock: 5,
          max_stock: 100,
        },
  })

  useEffect(() => {
    if (item) {
      reset({
        ...item,
        barcode: item.barcode || '',
        currency: item.currency || defaultCurrency,
        color: item.color || 'other',
      })
    } else {
      reset({
        sku: '',
        barcode: '',
        name: '',
        description: '',
        supplier: '',
        unit_of_measure: '',
        color: 'other',
        cost_price: 0,
        currency: defaultCurrency,
        reorder_point: 10,
        min_stock: 5,
        max_stock: 100,
      })
    }
  }, [item, reset, defaultCurrency])

  const handleFormSubmit = async (data: ItemFormData) => {
    try {
      // Preprocess functions should have already converted strings to numbers,
      // but ensure type safety for CreateItemData
      const submitData: CreateItemData = {
        sku: data.sku,
        barcode: data.barcode || undefined,
        name: data.name,
        description: data.description,
        supplier: data.supplier,
        unit_of_measure: data.unit_of_measure,
        color: data.color,
        cost_price: data.cost_price,
        currency: data.currency,
        reorder_point: data.reorder_point,
        min_stock: data.min_stock,
        max_stock: data.max_stock,
      }
      
      await onSubmit(submitData)
      onOpenChange(false)
      reset()
    } catch (error) {
      console.error('Failed to save item:', error)
    }
  }

  // Block Escape/overlay-click dismissal while a save is in flight -
  // without this, closing mid-submit and reopening for a different item
  // could let this request's success callback (above) reset/close the
  // new, unrelated dialog instance once it eventually resolves.
  const handleOpenChange = (nextOpen: boolean) => {
    if (isSubmitting) return
    onOpenChange(nextOpen)
  }

  return (
    <TooltipProvider>
      <Dialog open={open} onOpenChange={handleOpenChange}>
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
                <p className="text-sm text-destructive">{t(errors.sku.message ?? '')}</p>
              )}
            </div>

            <div className="space-y-2">
              <Label htmlFor="barcode">{t('items.barcode')}</Label>
              <Input
                id="barcode"
                {...register('barcode')}
                placeholder="7290000000000"
                className="font-mono"
              />
            </div>
          </div>

          <div className="space-y-2">
            <Label htmlFor="name">{t('items.name')} *</Label>
            <Input
              id="name"
              {...register('name')}
              placeholder={t('items.namePlaceholder')}
            />
            {errors.name && (
              <p className="text-sm text-destructive">{t(errors.name.message ?? '')}</p>
            )}
          </div>

          <div className="space-y-2">
            <Label htmlFor="description">{t('items.description')}</Label>
            <Textarea
              id="description"
              {...register('description')}
              placeholder={t('items.descriptionPlaceholder')}
              rows={2}
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="supplier">{t('items.supplier')} *</Label>
              <Input
                id="supplier"
                {...register('supplier')}
                placeholder={t('items.supplierPlaceholder')}
              />
              {errors.supplier && (
                <p className="text-sm text-destructive">{t(errors.supplier.message ?? '')}</p>
              )}
            </div>

            <div className="space-y-2">
              <Label htmlFor="unit_of_measure">{t('items.unit')} *</Label>
              <Input
                id="unit_of_measure"
                {...register('unit_of_measure')}
                placeholder={t('items.unitDefault')}
              />
              {errors.unit_of_measure && (
                <p className="text-sm text-destructive">{t(errors.unit_of_measure.message ?? '')}</p>
              )}
            </div>
          </div>

          <div className="space-y-2">
            <Label htmlFor="color">{t('items.color')}</Label>
            <Controller
              name="color"
              control={control}
              render={({ field }) => (
                <Select value={field.value} onValueChange={field.onChange}>
                  <SelectTrigger id="color">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="cyan">{t('items.colorCyan')}</SelectItem>
                    <SelectItem value="magenta">{t('items.colorMagenta')}</SelectItem>
                    <SelectItem value="yellow">{t('items.colorYellow')}</SelectItem>
                    <SelectItem value="black">{t('items.colorBlack')}</SelectItem>
                    <SelectItem value="white">{t('items.colorWhite')}</SelectItem>
                    <SelectItem value="other">{t('items.colorOther')}</SelectItem>
                  </SelectContent>
                </Select>
              )}
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="cost_price">{t('items.costPrice')} *</Label>
              <div className="flex gap-2">
                <QuantityInput
                  id="cost_price"
                  {...register('cost_price', { valueAsNumber: true })}
                  step={0.01}
                  min={0}
                  placeholder="0.00"
                  className="flex-1"
                />
                <Controller
                  name="currency"
                  control={control}
                  render={({ field }) => (
                    <Select
                      value={field.value}
                      onValueChange={field.onChange}
                    >
                      <SelectTrigger className="w-[120px]">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="ILS">{t('currency.ils')}</SelectItem>
                        <SelectItem value="USD">{t('currency.usd')}</SelectItem>
                        <SelectItem value="EUR">{t('currency.eur')}</SelectItem>
                        <SelectItem value="TRY">{t('currency.try')}</SelectItem>
                      </SelectContent>
                    </Select>
                  )}
                />
              </div>
              {errors.cost_price && (
                <p className="text-sm text-destructive">{t(errors.cost_price.message ?? '')}</p>
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
                      <p>{t('items.reorderPointHelp')}</p>
                    </TooltipContent>
                  </Tooltip>
                </TooltipProvider>
              </div>
              <QuantityInput
                id="reorder_point"
                {...register('reorder_point', { valueAsNumber: true })}
                step={1}
                min={0}
                unit={watch('unit_of_measure')}
                inputMode="numeric"
                placeholder="10"
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="min_stock">{t('items.minStock')}</Label>
              <QuantityInput
                id="min_stock"
                {...register('min_stock', { valueAsNumber: true })}
                step={1}
                min={0}
                unit={watch('unit_of_measure')}
                inputMode="numeric"
                placeholder="5"
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="max_stock">{t('items.maxStock')}</Label>
              <QuantityInput
                id="max_stock"
                {...register('max_stock', { valueAsNumber: true })}
                step={1}
                min={0}
                unit={watch('unit_of_measure')}
                inputMode="numeric"
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
                  <Loader2 className="w-4 h-4 me-2 animate-spin" />
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

