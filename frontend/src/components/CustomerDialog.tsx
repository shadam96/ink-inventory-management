import { useEffect } from 'react'
import { useForm, useFieldArray } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { useTranslation } from 'react-i18next'
import { Loader2, Plus, Trash2 } from 'lucide-react'

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

import i18n from '@/i18n'

const machineSchema = z.object({
  machine_type: z.string().min(1, i18n.t('customers.machines.typeRequired')),
  installation_date: z.string().optional().or(z.literal('')),
})

const customerSchema = z.object({
  name: z.string().min(1, 'customers.nameRequired'),
  email: z.string().email('customers.emailInvalid').or(z.literal('')).optional(),
  phone_primary: z.string().max(50).optional().or(z.literal('')),
  phone_secondary: z.string().max(50).optional().or(z.literal('')),
  address: z.string().optional().or(z.literal('')),
  contact_person: z.string().max(100).optional().or(z.literal('')),
  is_vmi_customer: z.boolean(),
  notes: z.string().optional().or(z.literal('')),
  machines: z.array(machineSchema),
})

type CustomerFormData = z.infer<typeof customerSchema>

interface CustomerDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  customer?: Customer | null
  onSubmit: (data: CreateCustomerData) => Promise<void>
}

function buildDefaults(customer?: Customer | null): CustomerFormData {
  if (!customer) {
    return {
      name: '',
      email: '',
      phone_primary: '',
      phone_secondary: '',
      address: '',
      contact_person: '',
      is_vmi_customer: false,
      notes: '',
      machines: [],
    }
  }
  return {
    name: customer.name,
    email: customer.email || '',
    phone_primary: customer.phone_primary || '',
    phone_secondary: customer.phone_secondary || '',
    address: customer.address || '',
    contact_person: customer.contact_person || '',
    is_vmi_customer: customer.is_vmi_customer,
    notes: customer.notes || '',
    machines: (customer.machines || []).map((m) => ({
      machine_type: m.machine_type,
      installation_date: m.installation_date || '',
    })),
  }
}

export function CustomerDialog({ open, onOpenChange, customer, onSubmit }: CustomerDialogProps) {
  const { t } = useTranslation()
  const isEdit = !!customer

  const {
    register,
    handleSubmit,
    reset,
    control,
    formState: { errors, isSubmitting },
  } = useForm<CustomerFormData>({
    resolver: zodResolver(customerSchema),
    defaultValues: buildDefaults(customer),
  })

  const { fields, append, remove } = useFieldArray({
    control,
    name: 'machines',
  })

  useEffect(() => {
    reset(buildDefaults(customer))
  }, [customer, reset])

  const handleFormSubmit = async (data: CustomerFormData) => {
    try {
      const submitData: CreateCustomerData = {
        name: data.name,
        email: data.email || undefined,
        phone_primary: data.phone_primary || undefined,
        phone_secondary: data.phone_secondary || undefined,
        address: data.address || undefined,
        contact_person: data.contact_person || undefined,
        is_vmi_customer: data.is_vmi_customer,
        notes: data.notes || undefined,
        machines: data.machines.map((m) => ({
          machine_type: m.machine_type,
          installation_date: m.installation_date ? m.installation_date : null,
        })),
      }
      await onSubmit(submitData)
      onOpenChange(false)
      reset(buildDefaults(null))
    } catch (error) {
      console.error('Failed to save customer:', error)
    }
  }

  // Block Escape/overlay-click dismissal while a save is in flight - see
  // the matching comment in ItemDialog.tsx.
  const handleOpenChange = (nextOpen: boolean) => {
    if (isSubmitting) return
    onOpenChange(nextOpen)
  }

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="max-w-lg max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>
            {isEdit ? t('customers.edit') : t('customers.add')}
          </DialogTitle>
        </DialogHeader>

        <form onSubmit={handleSubmit(handleFormSubmit)} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="name">{t('customers.name')} *</Label>
            <Input
              id="name"
              {...register('name')}
              placeholder={t('customers.namePlaceholder')}
            />
            {errors.name && (
              <p className="text-sm text-destructive">{t(errors.name.message ?? '')}</p>
            )}
          </div>

          <div className="space-y-2">
            <Label htmlFor="contact_person">{t('customers.contactPerson')}</Label>
            <Input
              id="contact_person"
              {...register('contact_person')}
              placeholder={t('customers.contactPersonPlaceholder')}
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="phone_primary">{t('customers.phonePrimary')}</Label>
              <Input
                id="phone_primary"
                {...register('phone_primary')}
                placeholder="050-0000000"
                dir="ltr"
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="phone_secondary">{t('customers.phoneSecondary')}</Label>
              <Input
                id="phone_secondary"
                {...register('phone_secondary')}
                placeholder="050-0000000"
                dir="ltr"
              />
            </div>
          </div>

          <div className="space-y-2">
            <Label htmlFor="email">{t('customers.email')}</Label>
            <Input
              id="email"
              type="email"
              {...register('email')}
              placeholder="email@example.com"
              dir="ltr"
            />
            {errors.email && (
              <p className="text-sm text-destructive">{t(errors.email.message ?? '')}</p>
            )}
          </div>

          <div className="space-y-2">
            <Label htmlFor="address">{t('customers.address')}</Label>
            <Input
              id="address"
              {...register('address')}
              placeholder={t('customers.addressPlaceholder')}
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="notes">{t('customers.notes')}</Label>
            <Textarea
              id="notes"
              {...register('notes')}
              placeholder={t('customers.notesPlaceholder')}
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
              {t('customers.vmiLabel')}
            </Label>
          </div>

          <div className="space-y-3 border-t pt-4">
            <div className="flex items-center justify-between">
              <Label className="text-base font-semibold">
                {t('customers.machines.sectionTitle')}
              </Label>
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() =>
                  append({ machine_type: '', installation_date: '' })
                }
              >
                <Plus className="w-4 h-4 me-1" />
                {t('customers.machines.add')}
              </Button>
            </div>

            {fields.length === 0 ? (
              <p className="text-sm text-muted-foreground">
                {t('customers.machines.empty')}
              </p>
            ) : (
              <div className="space-y-3">
                {fields.map((field, index) => (
                  <div
                    key={field.id}
                    className="border rounded-md p-3 space-y-2 bg-muted/30"
                  >
                    <div className="flex items-start justify-between gap-2">
                      <Label className="text-sm font-medium">
                        {t('customers.machines.itemLabel', { index: index + 1 })}
                      </Label>
                      <Button
                        type="button"
                        variant="ghost"
                        size="icon"
                        className="h-7 w-7 text-destructive hover:text-destructive"
                        onClick={() => remove(index)}
                      >
                        <Trash2 className="w-4 h-4" />
                      </Button>
                    </div>

                    <div className="grid grid-cols-2 gap-3">
                      <div className="space-y-1">
                        <Label
                          htmlFor={`machines.${index}.machine_type`}
                          className="text-xs"
                        >
                          {t('customers.machines.typeLabel')}
                        </Label>
                        <Input
                          id={`machines.${index}.machine_type`}
                          {...register(`machines.${index}.machine_type`)}
                          placeholder={t('customers.machines.typePlaceholder')}
                        />
                        {errors.machines?.[index]?.machine_type && (
                          <p className="text-xs text-destructive">
                            {errors.machines[index]?.machine_type?.message}
                          </p>
                        )}
                      </div>

                      <div className="space-y-1">
                        <Label
                          htmlFor={`machines.${index}.installation_date`}
                          className="text-xs"
                        >
                          {t('customers.machines.installationDate')}
                        </Label>
                        <Input
                          id={`machines.${index}.installation_date`}
                          type="date"
                          {...register(`machines.${index}.installation_date`)}
                        />
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
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
  )
}
