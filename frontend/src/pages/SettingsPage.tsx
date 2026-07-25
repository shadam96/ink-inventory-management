import { useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { useUIStore } from '@/store/ui'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Label } from '@/components/ui/label'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group'
import { Droplets, Package, Boxes, Warehouse, Mail, Plus, X, Send, Languages } from 'lucide-react'
import { toast } from 'sonner'
import api from '@/lib/api'
import { SUPPORTED_LANGUAGES, resolveLanguage } from '@/i18n/config'

const iconMap = {
  droplets: Droplets,
  package: Package,
  boxes: Boxes,
  warehouse: Warehouse,
}

export function SettingsPage() {
  const { t, i18n } = useTranslation()
  const currentLanguage = resolveLanguage(i18n.language).code
  const {
    theme,
    currency,
    appName,
    appIcon,
    setTheme,
    setCurrency,
    setAppName,
    setAppIcon,
  } = useUIStore()

  // Notification emails — persisted to the server immediately on add/remove
  // (optimistic update + revert on failure). No explicit save button.
  const [notificationEmails, setNotificationEmails] = useState<string[]>([])
  const [newEmail, setNewEmail] = useState('')
  const [loadingEmail, setLoadingEmail] = useState(true)

  // Test email is an action, not a setting — kept as a one-shot button.
  const [testEmail, setTestEmail] = useState('')
  const [sendingTest, setSendingTest] = useState(false)

  useEffect(() => {
    fetchNotificationSettings()
  }, [])

  const fetchNotificationSettings = async () => {
    try {
      const response = await api.get('/settings/notifications')
      setNotificationEmails(response.data.notification_emails || [])
    } catch (error) {
      console.error('Failed to fetch notification settings:', error)
    } finally {
      setLoadingEmail(false)
    }
  }

  const isValidEmail = (email: string) => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)

  const persistEmails = async (next: string[], previous: string[]) => {
    try {
      await api.put('/settings/notifications', {
        email_notifications_enabled: next.length > 0,
        notification_emails: next,
      })
    } catch (error: any) {
      setNotificationEmails(previous)
      toast.error(error.response?.data?.detail || t('settings.notificationEmailsSaveFailed'))
    }
  }

  const addEmail = () => {
    const trimmed = newEmail.trim()
    if (!trimmed || !isValidEmail(trimmed)) {
      toast.error(t('settings.emailInvalid'))
      return
    }
    if (notificationEmails.includes(trimmed)) {
      toast.error(t('settings.emailDuplicate'))
      return
    }
    const previous = notificationEmails
    const next = [...notificationEmails, trimmed]
    setNotificationEmails(next)
    setNewEmail('')
    void persistEmails(next, previous)
  }

  const removeEmail = (email: string) => {
    const previous = notificationEmails
    const next = notificationEmails.filter(e => e !== email)
    setNotificationEmails(next)
    void persistEmails(next, previous)
  }

  const sendTestEmail = async () => {
    const recipient = testEmail.trim()
    if (!recipient || !isValidEmail(recipient)) {
      toast.error(t('settings.emailInvalid'))
      return
    }
    setSendingTest(true)
    try {
      await api.post('/settings/email/test', { email: recipient })
      toast.success(t('settings.testEmailSent', { recipient }))
    } catch (error: any) {
      toast.error(error.response?.data?.detail || t('settings.testEmailFailed'))
    } finally {
      setSendingTest(false)
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">{t('settings.title')}</h1>
      </div>

      {/* General Settings */}
      <Card>
        <CardHeader>
          <CardTitle>{t('settings.general')}</CardTitle>
          <CardDescription>
            {t('settings.generalDescription')}
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* App Name */}
          <div className="space-y-2">
            <Label htmlFor="appName">{t('settings.appName')}</Label>
            <Input
              id="appName"
              value={appName}
              onChange={(e) => setAppName(e.target.value)}
              placeholder={t('settings.appNamePlaceholder')}
            />
          </div>

          {/* App Icon */}
          <div className="space-y-3">
            <Label>{t('settings.appIcon')}</Label>
            <RadioGroup value={appIcon} onValueChange={(value: any) => setAppIcon(value)}>
              <div className="grid grid-cols-2 gap-4">
                {(Object.keys(iconMap) as Array<keyof typeof iconMap>).map((iconKey) => {
                  const Icon = iconMap[iconKey]
                  return (
                    <div
                      key={iconKey}
                      className={`flex items-center gap-3 border rounded-lg p-4 cursor-pointer transition-all ${
                        appIcon === iconKey
                          ? 'border-primary bg-primary/5'
                          : 'border-border hover:border-primary/50'
                      }`}
                      onClick={() => setAppIcon(iconKey)}
                    >
                      <RadioGroupItem value={iconKey} id={iconKey} />
                      <div className="flex items-center gap-3">
                        <div className="flex items-center justify-center w-10 h-10 rounded-lg gradient-ink">
                          <Icon className="w-6 h-6 text-white" />
                        </div>
                        <Label htmlFor={iconKey} className="cursor-pointer">
                          {t(`settings.icon${iconKey.charAt(0).toUpperCase() + iconKey.slice(1)}`)}
                        </Label>
                      </div>
                    </div>
                  )
                })}
              </div>
            </RadioGroup>
          </div>
        </CardContent>
      </Card>

      {/* Appearance Settings */}
      <Card>
        <CardHeader>
          <CardTitle>{t('settings.appearance')}</CardTitle>
          <CardDescription>
            {t('settings.appearanceDescription')}
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Theme */}
          <div className="space-y-3">
            <Label>{t('settings.theme')}</Label>
            <RadioGroup value={theme} onValueChange={(value: any) => setTheme(value)}>
              <div className="space-y-2">
                <div className="flex items-center gap-3">
                  <RadioGroupItem value="light" id="light" />
                  <Label htmlFor="light" className="cursor-pointer">
                    {t('settings.themeLight')}
                  </Label>
                </div>
                <div className="flex items-center gap-3">
                  <RadioGroupItem value="dark" id="dark" />
                  <Label htmlFor="dark" className="cursor-pointer">
                    {t('settings.themeDark')}
                  </Label>
                </div>
                <div className="flex items-center gap-3">
                  <RadioGroupItem value="system" id="system" />
                  <Label htmlFor="system" className="cursor-pointer">
                    {t('settings.themeSystem')}
                  </Label>
                </div>
              </div>
            </RadioGroup>
          </div>

          {/* Currency */}
          <div className="space-y-3">
            <Label>{t('settings.currency')}</Label>
            <RadioGroup value={currency} onValueChange={(value: any) => setCurrency(value)}>
              <div className="space-y-2">
                <div className="flex items-center gap-3">
                  <RadioGroupItem value="ILS" id="ILS" />
                  <Label htmlFor="ILS" className="cursor-pointer">
                    {t('settings.currencyILS')}
                  </Label>
                </div>
                <div className="flex items-center gap-3">
                  <RadioGroupItem value="USD" id="USD" />
                  <Label htmlFor="USD" className="cursor-pointer">
                    {t('settings.currencyUSD')}
                  </Label>
                </div>
                <div className="flex items-center gap-3">
                  <RadioGroupItem value="EUR" id="EUR" />
                  <Label htmlFor="EUR" className="cursor-pointer">
                    {t('settings.currencyEUR')}
                  </Label>
                </div>
                <div className="flex items-center gap-3">
                  <RadioGroupItem value="TRY" id="TRY" />
                  <Label htmlFor="TRY" className="cursor-pointer">
                    {t('settings.currencyTRY')}
                  </Label>
                </div>
              </div>
            </RadioGroup>
          </div>
        </CardContent>
      </Card>

      {/* Language */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Languages className="w-5 h-5" />
            {t('settings.language')}
          </CardTitle>
          <CardDescription>{t('settings.languageDescription')}</CardDescription>
        </CardHeader>
        <CardContent>
          <RadioGroup
            value={currentLanguage}
            onValueChange={(value) => i18n.changeLanguage(value)}
          >
            <div className="space-y-2">
              {SUPPORTED_LANGUAGES.map((lang) => (
                <div key={lang.code} className="flex items-center gap-3">
                  <RadioGroupItem value={lang.code} id={`lang-${lang.code}`} />
                  <Label htmlFor={`lang-${lang.code}`} className="cursor-pointer">
                    {lang.label}
                  </Label>
                </div>
              ))}
            </div>
          </RadioGroup>
        </CardContent>
      </Card>

      {/* Email Notifications */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Mail className="w-5 h-5" />
            {t('settings.emailNotifications')}
          </CardTitle>
          <CardDescription>
            {t('settings.emailNotificationsDescription')}
          </CardDescription>
        </CardHeader>
        <CardContent>
          {loadingEmail ? (
            <div className="text-center py-4">{t('common.loading')}</div>
          ) : (
            <div className="space-y-3">
              {/* Existing emails */}
              {notificationEmails.length > 0 && (
                <div className="flex flex-wrap gap-2">
                  {notificationEmails.map((email) => (
                    <div
                      key={email}
                      className="flex items-center gap-1.5 bg-muted px-3 py-1.5 rounded-full text-sm"
                    >
                      <span dir="ltr">{email}</span>
                      <button
                        onClick={() => removeEmail(email)}
                        className="text-muted-foreground hover:text-destructive transition-colors"
                      >
                        <X className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  ))}
                </div>
              )}

              {/* Add new email */}
              <div className="flex gap-2">
                <Input
                  type="email"
                  dir="ltr"
                  placeholder="your@email.com"
                  value={newEmail}
                  onChange={(e) => setNewEmail(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && (e.preventDefault(), addEmail())}
                />
                <Button variant="outline" onClick={addEmail} disabled={!newEmail.trim()}>
                  <Plus className="w-4 h-4" />
                </Button>
              </div>

              {/* Test email */}
              <div className="pt-4 mt-2 border-t space-y-2">
                <Label className="text-sm">{t('settings.testEmailTitle')}</Label>
                <p className="text-xs text-muted-foreground">
                  {t('settings.testEmailHelp')}
                </p>
                <div className="flex gap-2">
                  <Input
                    type="email"
                    dir="ltr"
                    placeholder="recipient@example.com"
                    value={testEmail}
                    onChange={(e) => setTestEmail(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && (e.preventDefault(), sendTestEmail())}
                  />
                  <Button
                    variant="outline"
                    onClick={sendTestEmail}
                    disabled={sendingTest || !testEmail.trim()}
                  >
                    <Send className="w-4 h-4 me-2" />
                    {sendingTest ? t('common.sending') : t('settings.sendTestEmail')}
                  </Button>
                </div>
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
