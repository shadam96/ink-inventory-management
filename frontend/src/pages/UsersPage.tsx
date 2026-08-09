import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Users as UsersIcon, Plus, Pencil, MapPin } from 'lucide-react'
import { ChevronStart, ChevronEnd } from '@/components/ui/DirectionalIcon'
import { toast } from 'sonner'

import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Header } from '@/components/layout/Header'
import { SearchInput } from '@/components/SearchInput'
import { UserDialog, type UserFormSubmitData } from '@/components/UserDialog'
import { usersApi, authApi, type ManagedUser, type CreateUserData } from '@/lib/api'

export function UsersPage() {
  const { t } = useTranslation()
  const [users, setUsers] = useState<ManagedUser[]>([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [page, setPage] = useState(1)
  const [total, setTotal] = useState(0)
  const [dialogOpen, setDialogOpen] = useState(false)
  const [editingUser, setEditingUser] = useState<ManagedUser | null>(null)
  const pageSize = 20

  useEffect(() => {
    fetchUsers()
  }, [page, search])

  async function fetchUsers() {
    try {
      setLoading(true)
      const response = await usersApi.list({
        page,
        page_size: pageSize,
        search: search || undefined,
      })
      setUsers(response.items || [])
      setTotal(response.total)
    } catch (error) {
      console.error('Failed to fetch users:', error)
      toast.error(t('users.fetchError'))
    } finally {
      setLoading(false)
    }
  }

  const handleSearch = (value: string) => {
    setSearch(value)
    setPage(1)
  }

  const handleAdd = () => {
    setEditingUser(null)
    setDialogOpen(true)
  }

  const handleEdit = (user: ManagedUser) => {
    setEditingUser(user)
    setDialogOpen(true)
  }

  const handleSubmit = async (data: UserFormSubmitData) => {
    try {
      if (editingUser) {
        await usersApi.update(editingUser.id, data.profile)
        if (data.locationIds !== null) {
          await usersApi.updateLocations(editingUser.id, data.locationIds)
        }
        toast.success(t('users.updated'))
      } else {
        await authApi.register(data.profile as CreateUserData)
        toast.success(t('users.added'))
      }
      fetchUsers()
    } catch (error: any) {
      const message = error.response?.data?.detail || t('users.saveError')
      toast.error(message)
      throw error
    }
  }

  const roleLabel = (role: ManagedUser['role']) => {
    const map: Record<ManagedUser['role'], string> = {
      admin: t('users.roles.admin'),
      manager: t('users.roles.manager'),
      warehouse_worker: t('users.roles.warehouseWorker'),
      viewer: t('users.roles.viewer'),
      customer: t('users.roles.customer'),
    }
    return map[role]
  }

  const totalPages = Math.ceil(total / pageSize)

  return (
    <div className="space-y-6">
      <Header title={t('nav.users')} />

      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 relative z-10 -mt-2">
        <div className="flex items-center gap-2">
          <UsersIcon className="w-5 h-5 text-muted-foreground" />
          <span className="text-muted-foreground">
            {t('users.countLabel', { count: total })}
          </span>
        </div>
        <div className="flex items-center gap-3 w-full sm:w-auto">
          <SearchInput
            value={search}
            onChange={handleSearch}
            placeholder={t('users.searchPlaceholder')}
            className="w-full sm:w-64"
          />
          <Button onClick={handleAdd} className="shrink-0">
            <Plus className="w-4 h-4 me-2" />
            {t('users.add')}
          </Button>
        </div>
      </div>

      {loading ? (
        <Card>
          <CardContent className="p-8 text-center text-muted-foreground">
            {t('common.loading')}
          </CardContent>
        </Card>
      ) : users.length === 0 ? (
        <Card>
          <CardContent className="p-8 text-center text-muted-foreground">
            <UsersIcon className="w-12 h-12 mx-auto mb-2 opacity-50" />
            <p>{search ? t('users.noResults') : t('common.noData')}</p>
          </CardContent>
        </Card>
      ) : (
        <>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {users.map((user) => (
              <Card key={user.id} className="card-hover">
                <CardContent className="p-5">
                  <div className="flex items-start justify-between mb-3">
                    <div className="flex-1 min-w-0">
                      <h3 className="font-semibold text-lg truncate">{user.full_name}</h3>
                      <p className="text-sm text-muted-foreground truncate" dir="ltr">
                        {user.username}
                      </p>
                      <div className="flex flex-wrap gap-1.5 mt-1.5">
                        <Badge variant="outline">{roleLabel(user.role)}</Badge>
                        {user.is_active ? (
                          <Badge variant="safe">{t('users.statusActive')}</Badge>
                        ) : (
                          <Badge variant="secondary">{t('users.statusInactive')}</Badge>
                        )}
                      </div>
                    </div>
                    <div className="flex items-center gap-1 shrink-0 ms-2">
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-8 w-8"
                        onClick={() => handleEdit(user)}
                      >
                        <Pencil className="w-4 h-4" />
                      </Button>
                    </div>
                  </div>

                  <div className="space-y-1.5 text-sm">
                    <div className="flex items-center gap-2 text-muted-foreground">
                      <span className="truncate" dir="ltr">{user.email}</span>
                    </div>
                    {user.location_ids.length > 0 && (
                      <div className="flex items-center gap-2 text-muted-foreground">
                        <MapPin className="w-3.5 h-3.5 shrink-0" />
                        <span className="text-xs">
                          {t('users.locationsCount', { count: user.location_ids.length })}
                        </span>
                      </div>
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
                aria-label="Previous page"
              >
                <ChevronStart className="w-4 h-4" />
              </Button>
              <span className="text-sm text-muted-foreground px-2">
                {page} / {totalPages}
              </span>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                disabled={page === totalPages}
                aria-label="Next page"
              >
                <ChevronEnd className="w-4 h-4" />
              </Button>
            </div>
          )}
        </>
      )}

      <UserDialog
        open={dialogOpen}
        onOpenChange={setDialogOpen}
        user={editingUser}
        onSubmit={handleSubmit}
      />
    </div>
  )
}
