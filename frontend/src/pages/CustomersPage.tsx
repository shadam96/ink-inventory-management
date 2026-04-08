import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Users, Plus, Pencil, Trash2, Mail, Phone, MapPin, ChevronLeft, ChevronRight, Wrench } from 'lucide-react'
import { toast } from 'sonner'

import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Header } from '@/components/layout/Header'
import { SearchInput } from '@/components/SearchInput'
import { CustomerDialog } from '@/components/CustomerDialog'
import { customersApi, type Customer, type CreateCustomerData } from '@/lib/api'
import { formatDate } from '@/lib/utils'

export function CustomersPage() {
  const { t } = useTranslation()
  const [customers, setCustomers] = useState<Customer[]>([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [page, setPage] = useState(1)
  const [total, setTotal] = useState(0)
  const [dialogOpen, setDialogOpen] = useState(false)
  const [editingCustomer, setEditingCustomer] = useState<Customer | null>(null)
  const pageSize = 20

  useEffect(() => {
    fetchCustomers()
  }, [page, search])

  async function fetchCustomers() {
    try {
      setLoading(true)
      const response = await customersApi.list({
        page,
        page_size: pageSize,
        search: search || undefined,
        is_active: undefined,
      })
      setCustomers(response.items || [])
      setTotal(response.total)
    } catch (error) {
      console.error('Failed to fetch customers:', error)
      toast.error('שגיאה בטעינת לקוחות')
    } finally {
      setLoading(false)
    }
  }

  const handleSearch = (value: string) => {
    setSearch(value)
    setPage(1)
  }

  const handleAdd = () => {
    setEditingCustomer(null)
    setDialogOpen(true)
  }

  const handleEdit = (customer: Customer) => {
    setEditingCustomer(customer)
    setDialogOpen(true)
  }

  const handleDelete = async (customer: Customer) => {
    if (!confirm(`האם להשבית את "${customer.name}"?`)) return

    try {
      await customersApi.delete(customer.id)
      toast.success(`${customer.name} הושבת בהצלחה`)
      fetchCustomers()
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'שגיאה בהשבתת הלקוח')
    }
  }

  const handleSubmit = async (data: CreateCustomerData) => {
    try {
      if (editingCustomer) {
        await customersApi.update(editingCustomer.id, data)
        toast.success('לקוח עודכן בהצלחה')
      } else {
        await customersApi.create(data)
        toast.success('לקוח נוסף בהצלחה')
      }
      fetchCustomers()
    } catch (error: any) {
      const message = error.response?.data?.detail || 'שגיאה בשמירת הלקוח'
      toast.error(message)
      throw error
    }
  }

  const totalPages = Math.ceil(total / pageSize)

  return (
    <div className="space-y-6">
      <Header title={t('nav.customers')} />

      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 relative z-10 -mt-2">
        <div className="flex items-center gap-2">
          <Users className="w-5 h-5 text-muted-foreground" />
          <span className="text-muted-foreground">
            {total} לקוחות
          </span>
        </div>
        <div className="flex items-center gap-3 w-full sm:w-auto">
          <SearchInput
            value={search}
            onChange={handleSearch}
            placeholder="חיפוש לפי שם או אימייל..."
            className="w-full sm:w-64"
          />
          <Button onClick={handleAdd} className="shrink-0">
            <Plus className="w-4 h-4 me-2" />
            הוסף לקוח
          </Button>
        </div>
      </div>

      {loading ? (
        <Card>
          <CardContent className="p-8 text-center text-muted-foreground">
            {t('common.loading')}
          </CardContent>
        </Card>
      ) : customers.length === 0 ? (
        <Card>
          <CardContent className="p-8 text-center text-muted-foreground">
            <Users className="w-12 h-12 mx-auto mb-2 opacity-50" />
            <p>{search ? 'לא נמצאו לקוחות תואמים' : t('common.noData')}</p>
          </CardContent>
        </Card>
      ) : (
        <>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {customers.map((customer) => (
              <Card key={customer.id} className="card-hover">
                <CardContent className="p-5">
                  <div className="flex items-start justify-between mb-3">
                    <div className="flex-1 min-w-0">
                      <h3 className="font-semibold text-lg truncate">{customer.name}</h3>
                      <div className="flex flex-wrap gap-1.5 mt-1.5">
                        {customer.is_active ? (
                          <Badge variant="safe">פעיל</Badge>
                        ) : (
                          <Badge variant="secondary">לא פעיל</Badge>
                        )}
                        {customer.is_vmi_customer && (
                          <Badge variant="outline">VMI</Badge>
                        )}
                      </div>
                    </div>
                    <div className="flex items-center gap-1 shrink-0 ms-2">
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-8 w-8"
                        onClick={() => handleEdit(customer)}
                      >
                        <Pencil className="w-4 h-4" />
                      </Button>
                      {customer.is_active && (
                        <Button
                          variant="ghost"
                          size="icon"
                          className="h-8 w-8 text-destructive hover:text-destructive"
                          onClick={() => handleDelete(customer)}
                        >
                          <Trash2 className="w-4 h-4" />
                        </Button>
                      )}
                    </div>
                  </div>

                  <div className="space-y-1.5 text-sm">
                    {customer.contact_person && (
                      <div className="flex items-center gap-2 text-muted-foreground">
                        <Users className="w-3.5 h-3.5 shrink-0" />
                        <span className="truncate">{customer.contact_person}</span>
                      </div>
                    )}
                    {customer.email && (
                      <div className="flex items-center gap-2 text-muted-foreground">
                        <Mail className="w-3.5 h-3.5 shrink-0" />
                        <span className="truncate" dir="ltr">{customer.email}</span>
                      </div>
                    )}
                    {customer.phone_primary && (
                      <div className="flex items-center gap-2 text-muted-foreground">
                        <Phone className="w-3.5 h-3.5 shrink-0" />
                        <span dir="ltr">{customer.phone_primary}</span>
                      </div>
                    )}
                    {customer.phone_secondary && (
                      <div className="flex items-center gap-2 text-muted-foreground">
                        <Phone className="w-3.5 h-3.5 shrink-0 opacity-60" />
                        <span dir="ltr">{customer.phone_secondary}</span>
                      </div>
                    )}
                    {customer.address && (
                      <div className="flex items-center gap-2 text-muted-foreground">
                        <MapPin className="w-3.5 h-3.5 shrink-0" />
                        <span className="truncate">{customer.address}</span>
                      </div>
                    )}
                    {customer.machines && customer.machines.length > 0 && (
                      <div className="pt-2 mt-2 border-t border-border/60 space-y-1">
                        <div className="flex items-center gap-1.5 text-muted-foreground">
                          <Wrench className="w-3.5 h-3.5 shrink-0" />
                          <span className="text-xs font-medium">
                            {t('customers.machines.countSuffix', { count: customer.machines.length })}
                          </span>
                        </div>
                        <ul className="space-y-0.5 ps-5">
                          {customer.machines.map((machine) => (
                            <li
                              key={machine.id}
                              className="text-xs text-muted-foreground flex items-center gap-2"
                            >
                              <span className="font-medium text-foreground/80 truncate">
                                {machine.machine_type}
                              </span>
                              {machine.installation_date && (
                                <span className="text-muted-foreground/70">
                                  ({formatDate(machine.installation_date)})
                                </span>
                              )}
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}
                    {customer.notes && (
                      <p className="text-muted-foreground/70 text-xs mt-2 line-clamp-2 italic">
                        {customer.notes}
                      </p>
                    )}
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>

          {totalPages > 1 && (
            <div className="flex items-center justify-center gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page === 1}
              >
                <ChevronRight className="w-4 h-4" />
              </Button>
              <span className="text-sm text-muted-foreground px-2">
                {page} / {totalPages}
              </span>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                disabled={page === totalPages}
              >
                <ChevronLeft className="w-4 h-4" />
              </Button>
            </div>
          )}
        </>
      )}

      <CustomerDialog
        open={dialogOpen}
        onOpenChange={setDialogOpen}
        customer={editingCustomer}
        onSubmit={handleSubmit}
      />
    </div>
  )
}
