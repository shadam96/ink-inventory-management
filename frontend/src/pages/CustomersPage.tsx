import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Users, Plus, Pencil, Mail, Phone } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Header } from '@/components/layout/Header'
import { customersApi } from '@/lib/api'

interface Customer {
  id: string
  name: string
  email?: string
  phone?: string
  address?: string
  contact_person?: string
  is_active: boolean
  is_vmi_customer: boolean
}

export function CustomersPage() {
  const { t } = useTranslation()
  const [customers, setCustomers] = useState<Customer[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchCustomers()
  }, [])

  async function fetchCustomers() {
    try {
      setLoading(true)
      const response = await customersApi.list()
      setCustomers(response.items || [])
    } catch (error) {
      console.error('Failed to fetch customers:', error)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-6">
      <Header title={t('nav.customers')} />

      <div className="flex items-center justify-between mt-16">
        <div className="flex items-center gap-2">
          <Users className="w-5 h-5 text-muted-foreground" />
          <span className="text-muted-foreground">
            {customers.length} לקוחות
          </span>
        </div>
        <Button>
          <Plus className="w-4 h-4 ml-2" />
          הוסף לקוח
        </Button>
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
            <p>{t('common.noData')}</p>
          </CardContent>
        </Card>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {customers.map((customer) => (
            <Card key={customer.id} className="card-hover">
              <CardContent className="p-6">
                <div className="flex items-start justify-between mb-4">
                  <div className="flex-1">
                    <h3 className="font-semibold text-lg mb-2">{customer.name}</h3>
                    <div className="flex flex-wrap gap-2">
                      {customer.is_active ? (
                        <Badge variant="safe">פעיל</Badge>
                      ) : (
                        <Badge variant="secondary">לא פעיל</Badge>
                      )}
                      {customer.is_vmi_customer && (
                        <Badge variant="secondary">VMI</Badge>
                      )}
                    </div>
                  </div>
                  <Button variant="ghost" size="icon" className="h-8 w-8">
                    <Pencil className="w-4 h-4" />
                  </Button>
                </div>

                <div className="space-y-2 text-sm">
                  {customer.contact_person && (
                    <div className="flex items-center gap-2 text-muted-foreground">
                      <Users className="w-4 h-4" />
                      <span>{customer.contact_person}</span>
                    </div>
                  )}
                  {customer.email && (
                    <div className="flex items-center gap-2 text-muted-foreground">
                      <Mail className="w-4 h-4" />
                      <span>{customer.email}</span>
                    </div>
                  )}
                  {customer.phone && (
                    <div className="flex items-center gap-2 text-muted-foreground">
                      <Phone className="w-4 h-4" />
                      <span>{customer.phone}</span>
                    </div>
                  )}
                  {customer.address && (
                    <p className="text-muted-foreground mt-2 line-clamp-2">
                      {customer.address}
                    </p>
                  )}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}

