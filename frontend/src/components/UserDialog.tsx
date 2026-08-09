import { useEffect, useState } from 'react'
import { useForm, Controller } from 'react-hook-form'
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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  customersApi,
  locationsApi,
  type ManagedUser,
  type ManagedUserRole,
  type CreateUserData,
  type UpdateUserData,
  type Location,
} from '@/lib/api'

const STAFF_ROLES: ManagedUserRole[] = ['manager', 'warehouse_worker', 'viewer']

const userSchema = z
  .object({
    username: z.string().min(3, 'users.usernameRequired'),
    email: z.string().email('users.emailInvalid'),
    full_name: z.string().min(1, 'users.fullNameRequired'),
    password: z.string().optional().or(z.literal('')),
    role: z.enum(['admin', 'manager', 'warehouse_worker', 'viewer', 'customer']),
    is_active: z.boolean(),
    customer_id: z.string().optional().or(z.literal('')),
  })
  .refine((data) => data.role !== 'customer' || !!data.customer_id, {
    message: 'users.customerRequired',
    path: ['customer_id'],
  })

type UserFormData = z.infer<typeof userSchema>

export interface UserFormSubmitData {
  profile: CreateUserData | UpdateUserData
  locationIds: string[] | null
}

interface UserDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  user?: ManagedUser | null
  onSubmit: (data: UserFormSubmitData) => Promise<void>
}

function buildDefaults(user?: ManagedUser | null): UserFormData {
  if (!user) {
    return {
      username: '',
      email: '',
      full_name: '',
      password: '',
      role: 'viewer',
      is_active: true,
      customer_id: '',
    }
  }
  return {
    username: user.username,
    email: user.email,
    full_name: user.full_name,
    password: '',
    role: user.role,
    is_active: user.is_active,
    customer_id: user.customer_id || '',
  }
}

export function UserDialog({ open, onOpenChange, user, onSubmit }: UserDialogProps) {
  const { t } = useTranslation()
  const isEdit = !!user
  const [customers, setCustomers] = useState<{ id: string; name: string }[]>([])
  const [locations, setLocations] = useState<Location[]>([])
  const [selectedLocationIds, setSelectedLocationIds] = useState<string[]>(
    user?.location_ids || []
  )

  const {
    register,
    handleSubmit,
    reset,
    control,
    watch,
    setError,
    formState: { errors, isSubmitting },
  } = useForm<UserFormData>({
    resolver: zodResolver(userSchema),
    defaultValues: buildDefaults(user),
  })

  const role = watch('role')
  const showCustomerPicker = role === 'customer'
  const showLocationPicker = isEdit && STAFF_ROLES.includes(role)

  useEffect(() => {
    reset(buildDefaults(user))
    setSelectedLocationIds(user?.location_ids || [])
  }, [user, reset])

  useEffect(() => {
    if (!open) return
    customersApi.list({ page: 1, page_size: 100 }).then((res) => {
      setCustomers(res.items.map((c) => ({ id: c.id, name: c.name })))
    })
    locationsApi.list({ page: 1, page_size: 100 }).then((res) => {
      setLocations(res.items)
    })
  }, [open])

  const toggleLocation = (locationId: string) => {
    setSelectedLocationIds((prev) =>
      prev.includes(locationId)
        ? prev.filter((id) => id !== locationId)
        : [...prev, locationId]
    )
  }

  const handleFormSubmit = async (data: UserFormData) => {
    if (!isEdit && (!data.password || data.password.length < 8)) {
      setError('password', { message: 'users.passwordRequired' })
      return
    }

    try {
      if (isEdit) {
        const profile: UpdateUserData = {
          username: data.username,
          email: data.email,
          full_name: data.full_name,
          role: data.role,
          is_active: data.is_active,
        }
        if (data.password) {
          profile.password = data.password
        }
        await onSubmit({
          profile,
          locationIds: showLocationPicker ? selectedLocationIds : null,
        })
      } else {
        const profile: CreateUserData = {
          username: data.username,
          email: data.email,
          full_name: data.full_name,
          password: data.password || '',
          role: data.role,
          customer_id: data.customer_id || undefined,
        }
        await onSubmit({ profile, locationIds: null })
      }
      onOpenChange(false)
      reset(buildDefaults(null))
    } catch (error) {
      console.error('Failed to save user:', error)
    }
  }

  const handleOpenChange = (nextOpen: boolean) => {
    if (isSubmitting) return
    onOpenChange(nextOpen)
  }

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="max-w-lg max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>{isEdit ? t('users.edit') : t('users.add')}</DialogTitle>
        </DialogHeader>

        <form onSubmit={handleSubmit(handleFormSubmit)} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="username">{t('users.username')} *</Label>
            <Input id="username" {...register('username')} dir="ltr" />
            {errors.username && (
              <p className="text-sm text-destructive">{t(errors.username.message ?? '')}</p>
            )}
          </div>

          <div className="space-y-2">
            <Label htmlFor="full_name">{t('users.fullName')} *</Label>
            <Input id="full_name" {...register('full_name')} />
            {errors.full_name && (
              <p className="text-sm text-destructive">{t(errors.full_name.message ?? '')}</p>
            )}
          </div>

          <div className="space-y-2">
            <Label htmlFor="email">{t('users.email')} *</Label>
            <Input id="email" type="email" {...register('email')} dir="ltr" />
            {errors.email && (
              <p className="text-sm text-destructive">{t(errors.email.message ?? '')}</p>
            )}
          </div>

          <div className="space-y-2">
            <Label htmlFor="password">
              {isEdit ? t('users.passwordOptional') : t('users.password')} {!isEdit && '*'}
            </Label>
            <Input id="password" type="password" {...register('password')} dir="ltr" />
            {errors.password && (
              <p className="text-sm text-destructive">{t(errors.password.message ?? '')}</p>
            )}
          </div>

          <div className="space-y-2">
            <Label htmlFor="role">{t('users.role')}</Label>
            <Controller
              name="role"
              control={control}
              render={({ field }) => (
                <Select value={field.value} onValueChange={field.onChange}>
                  <SelectTrigger id="role">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="admin">{t('users.roles.admin')}</SelectItem>
                    <SelectItem value="manager">{t('users.roles.manager')}</SelectItem>
                    <SelectItem value="warehouse_worker">{t('users.roles.warehouseWorker')}</SelectItem>
                    <SelectItem value="viewer">{t('users.roles.viewer')}</SelectItem>
                    <SelectItem value="customer">{t('users.roles.customer')}</SelectItem>
                  </SelectContent>
                </Select>
              )}
            />
          </div>

          {showCustomerPicker && (
            <div className="space-y-2">
              <Label htmlFor="customer_id">{t('users.linkedCustomer')} *</Label>
              <Controller
                name="customer_id"
                control={control}
                render={({ field }) => (
                  <Select value={field.value || ''} onValueChange={field.onChange}>
                    <SelectTrigger id="customer_id">
                      <SelectValue placeholder={t('users.selectCustomer')} />
                    </SelectTrigger>
                    <SelectContent>
                      {customers.map((c) => (
                        <SelectItem key={c.id} value={c.id}>
                          {c.name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                )}
              />
              {errors.customer_id && (
                <p className="text-sm text-destructive">{t(errors.customer_id.message ?? '')}</p>
              )}
            </div>
          )}

          {isEdit && (
            <div className="flex items-center gap-3">
              <input
                type="checkbox"
                id="is_active"
                {...register('is_active')}
                className="h-4 w-4 rounded border-input accent-primary"
              />
              <Label htmlFor="is_active" className="cursor-pointer">
                {t('users.isActive')}
              </Label>
            </div>
          )}

          {showLocationPicker && (
            <div className="space-y-2 border-t pt-4">
              <Label className="text-base font-semibold">{t('users.assignedLocations')}</Label>
              <p className="text-xs text-muted-foreground">{t('users.assignedLocationsHint')}</p>
              {locations.length === 0 ? (
                <p className="text-sm text-muted-foreground">{t('users.noLocations')}</p>
              ) : (
                <div className="grid grid-cols-2 gap-2 max-h-40 overflow-y-auto">
                  {locations.map((loc) => (
                    <label
                      key={loc.id}
                      className="flex items-center gap-2 text-sm cursor-pointer"
                    >
                      <input
                        type="checkbox"
                        checked={selectedLocationIds.includes(loc.id)}
                        onChange={() => toggleLocation(loc.id)}
                        className="h-4 w-4 rounded border-input accent-primary"
                      />
                      <span className="truncate">{loc.location_code}</span>
                    </label>
                  ))}
                </div>
              )}
            </div>
          )}

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
