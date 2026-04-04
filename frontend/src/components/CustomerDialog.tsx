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
import type { Customer, CreateCustomerData } from '@/lib/api'

const customerSchema = z.object({
  name: z.string().min(1, 'שם לקוח נדרש'),
  email: z.string().email('כתובת אימייל לא תקינה').or(z.literal('')).optional(),
  phone: z.string().max(50).optional().or(z.literal('')),
  address: z.string().optional().or(z.literal('')),
  contact_person: z.string().max(100).optional().or(z.literal('')),
  is_vmi_customer: z.boolean(),
  notes: z.string().optional().or(z.literal('')),
})

type CustomerFormData = z.infer<typeof customerSchema>

interface CustomerDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  customer?: Customer | null
  onSubmit: (data: CreateCustomerData) => Promise<void>
}

export function CustomerDialog({ open, onOpenChange, customer, onSubmit }: CustomerDialogProps) {
  const { t } = useTranslation()
  const isEdit = !!customer

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<CustomerFormData>({
    resolver: zodResolver(customerSchema),
    defaultValues: customer
      ? {
          name: customer.name,
          email: customer.email || '',
          phone: customer.phone || '',
          address: customer.address || '',
          contact_person: customer.contact_person || '',
          is_vmi_customer: customer.is_vmi_customer,
          notes: customer.notes || '',
        }
      : {
          name: '',
          email: '',
          phone: '',
          address: '',
          contact_person: '',
          is_vmi_customer: false,
          notes: '',
        },
  })

  useEffect(() => {
    if (customer) {
      reset({
        name: customer.name,
        email: customer.email || '',
        phone: customer.phone || '',
        address: customer.address || '',
        contact_person: customer.contact_person || '',
        is_vmi_customer: customer.is_vmi_customer,
        notes: customer.notes || '',
      })
    } else {
      reset({
        name: '',
        email: '',
        phone: '',
        address: '',
        contact_person: '',
        is_vmi_customer: false,
        notes: '',
      })
    }
  }, [customer, reset])

  const handleFormSubmit = async (data: CustomerFormData) => {
    try {
      const submitData: CreateCustomerData = {
        name: data.name,
        email: data.email || undefined,
        phone: data.phone || undefined,
        address: data.address || undefined,
        contact_person: data.contact_person || undefined,
        is_vmi_customer: data.is_vmi_customer,
        notes: data.notes || undefined,
      }
      await onSubmit(submitData)
      onOpenChange(false)
      reset()
    } catch (error) {
      console.error('Failed to save customer:', error)
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>
            {isEdit ? 'עריכת לקוח' : 'הוספת לקוח'}
          </DialogTitle>
        </DialogHeader>

        <form onSubmit={handleSubmit(handleFormSubmit)} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="name">שם לקוח *</Label>
            <Input
              id="name"
              {...register('name')}
              placeholder="שם החברה או הלקוח"
            />
            {errors.name && (
              <p className="text-sm text-destructive">{errors.name.message}</p>
            )}
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="contact_person">איש קשר</Label>
              <Input
                id="contact_person"
                {...register('contact_person')}
                placeholder="שם איש קשר"
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="phone">טלפון</Label>
              <Input
                id="phone"
                {...register('phone')}
                placeholder="050-0000000"
                dir="ltr"
                className="text-right"
              />
            </div>
          </div>

          <div className="space-y-2">
            <Label htmlFor="email">אימייל</Label>
            <Input
              id="email"
              type="email"
              {...register('email')}
              placeholder="email@example.com"
              dir="ltr"
              className="text-right"
            />
            {errors.email && (
              <p className="text-sm text-destructive">{errors.email.message}</p>
            )}
          </div>

          <div className="space-y-2">
            <Label htmlFor="address">כתובת</Label>
            <Input
              id="address"
              {...register('address')}
              placeholder="רחוב, עיר"
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="notes">הערות</Label>
            <Textarea
              id="notes"
              {...register('notes')}
              placeholder="הערות נוספות..."
              rows={2}
            />
          </div>

          <div className="flex items-center gap-3">
            <input
              type="checkbox"
              id="is_vmi_customer"
              {...register('is_vmi_customer')}
              className="h-4 w-4 rounded border-input accent-primary"
            />
            <Label htmlFor="is_vmi_customer" className="cursor-pointer">
              לקוח VMI (ניהול מלאי אצל לקוח)
            </Label>
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
