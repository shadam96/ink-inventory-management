import { useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { useUIStore } from '@/store/ui'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Label } from '@/components/ui/label'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group'
import { Droplets, Package, Boxes, Warehouse, Mail, Send } from 'lucide-react'
import { toast } from 'sonner'
import { api } from '@/lib/api'

const iconMap = {
  droplets: Droplets,
  package: Package,
  boxes: Boxes,
  warehouse: Warehouse,
}

export function SettingsPage() {
  const { t } = useTranslation()
  const { 
    theme, 
    currency, 
    appName, 
    appIcon,
    setTheme, 
    setCurrency,
    setAppName,
    setAppIcon 
  } = useUIStore()

  const [localAppName, setLocalAppName] = useState(appName)
  const [localAppIcon, setLocalAppIcon] = useState(appIcon)
  const [localTheme, setLocalTheme] = useState(theme)
  const [localCurrency, setLocalCurrency] = useState(currency)
  
  // Email settings
  const [emailConfigured, setEmailConfigured] = useState(false)
  const [testEmail, setTestEmail] = useState('')
  const [sendingTest, setSendingTest] = useState(false)
  const [loadingEmail, setLoadingEmail] = useState(true)

  useEffect(() => {
    fetchEmailSettings()
  }, [])

  const fetchEmailSettings = async () => {
    try {
      const response = await api.get('/settings/email')
      setEmailConfigured(response.data.email_configured)
    } catch (error) {
      console.error('Failed to fetch email settings:', error)
    } finally {
      setLoadingEmail(false)
    }
  }

  const sendTestEmail = async () => {
    if (!testEmail) {
      toast.error('אנא הזן כתובת אימייל')
      return
    }

    setSendingTest(true)
    try {
      await api.post('/settings/email/test', { email: testEmail })
      toast.success('אימייל נשלח בהצלחה! בדוק את תיבת הדואר שלך')
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'שליחת האימייל נכשלה')
    } finally {
      setSendingTest(false)
    }
  }

  const handleSave = () => {
    setAppName(localAppName)
    setAppIcon(localAppIcon)
    setTheme(localTheme)
    setCurrency(localCurrency)
    
    // Apply theme immediately
    applyTheme(localTheme)
    
    toast.success(t('settings.saved'))
  }

  const applyTheme = (themeValue: 'light' | 'dark' | 'system') => {
    const root = document.documentElement
    
    if (themeValue === 'system') {
      const systemTheme = window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
      root.classList.toggle('dark', systemTheme === 'dark')
    } else {
      root.classList.toggle('dark', themeValue === 'dark')
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
            התאמה אישית של שם האפליקציה והסמל
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* App Name */}
          <div className="space-y-2">
            <Label htmlFor="appName">{t('settings.appName')}</Label>
            <Input
              id="appName"
              value={localAppName}
              onChange={(e) => setLocalAppName(e.target.value)}
              placeholder={t('settings.appNamePlaceholder')}
            />
          </div>

          {/* App Icon */}
          <div className="space-y-3">
            <Label>{t('settings.appIcon')}</Label>
            <RadioGroup value={localAppIcon} onValueChange={(value: any) => setLocalAppIcon(value)}>
              <div className="grid grid-cols-2 gap-4">
                {(Object.keys(iconMap) as Array<keyof typeof iconMap>).map((iconKey) => {
                  const Icon = iconMap[iconKey]
                  return (
                    <div
                      key={iconKey}
                      className={`flex items-center space-x-3 space-x-reverse border rounded-lg p-4 cursor-pointer transition-all ${
                        localAppIcon === iconKey
                          ? 'border-primary bg-primary/5'
                          : 'border-border hover:border-primary/50'
                      }`}
                      onClick={() => setLocalAppIcon(iconKey)}
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
            התאמה אישית של נושא המערכת והמטבע המוצג
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Theme */}
          <div className="space-y-3">
            <Label>{t('settings.theme')}</Label>
            <RadioGroup value={localTheme} onValueChange={(value: any) => setLocalTheme(value)}>
              <div className="space-y-2">
                <div className="flex items-center space-x-3 space-x-reverse">
                  <RadioGroupItem value="light" id="light" />
                  <Label htmlFor="light" className="cursor-pointer">
                    {t('settings.themeLight')}
                  </Label>
                </div>
                <div className="flex items-center space-x-3 space-x-reverse">
                  <RadioGroupItem value="dark" id="dark" />
                  <Label htmlFor="dark" className="cursor-pointer">
                    {t('settings.themeDark')}
                  </Label>
                </div>
                <div className="flex items-center space-x-3 space-x-reverse">
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
            <RadioGroup value={localCurrency} onValueChange={(value: any) => setLocalCurrency(value)}>
              <div className="space-y-2">
                <div className="flex items-center space-x-3 space-x-reverse">
                  <RadioGroupItem value="ILS" id="ILS" />
                  <Label htmlFor="ILS" className="cursor-pointer">
                    {t('settings.currencyILS')}
                  </Label>
                </div>
                <div className="flex items-center space-x-3 space-x-reverse">
                  <RadioGroupItem value="USD" id="USD" />
                  <Label htmlFor="USD" className="cursor-pointer">
                    {t('settings.currencyUSD')}
                  </Label>
                </div>
                <div className="flex items-center space-x-3 space-x-reverse">
                  <RadioGroupItem value="EUR" id="EUR" />
                  <Label htmlFor="EUR" className="cursor-pointer">
                    {t('settings.currencyEUR')}
                  </Label>
                </div>
              </div>
            </RadioGroup>
          </div>
        </CardContent>
      </Card>

      {/* Email Settings */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Mail className="w-5 h-5" />
            הגדרות דוא"ל
          </CardTitle>
          <CardDescription>
            בדיקת חיבור ושליחת אימייל בדיקה
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {loadingEmail ? (
            <div className="text-center py-4">טוען...</div>
          ) : (
            <>
              <div className="flex items-center gap-2 p-4 rounded-lg bg-muted">
                <div className={`w-3 h-3 rounded-full ${emailConfigured ? 'bg-green-500' : 'bg-red-500'}`} />
                <span className="text-sm">
                  {emailConfigured 
                    ? '✅ שרת דוא"ל מוגדר ופעיל' 
                    : '⚠️ שרת דוא"ל לא מוגדר - עדכן משתני סביבה'}
                </span>
              </div>

              {emailConfigured && (
                <div className="space-y-4">
                  <div className="space-y-2">
                    <Label htmlFor="testEmail">שלח אימייל בדיקה</Label>
                    <div className="flex gap-2">
                      <Input
                        id="testEmail"
                        type="email"
                        placeholder="your@email.com"
                        value={testEmail}
                        onChange={(e) => setTestEmail(e.target.value)}
                        disabled={sendingTest}
                      />
                      <Button 
                        onClick={sendTestEmail} 
                        disabled={sendingTest}
                        className="gap-2"
                      >
                        <Send className="w-4 h-4" />
                        {sendingTest ? 'שולח...' : 'שלח'}
                      </Button>
                    </div>
                    <p className="text-xs text-muted-foreground">
                      אימייל בדיקה יישלח לכתובת שהזנת כדי לבדוק את החיבור
                    </p>
                  </div>

                  <div className="p-4 bg-blue-50 border border-blue-200 rounded-lg">
                    <h4 className="font-medium text-sm mb-2">📧 אימיילים אוטומטיים מופעלים</h4>
                    <ul className="text-xs space-y-1 text-muted-foreground">
                      <li>✓ התראות על תוקף מתקרב (30, 60, 90, 120 ימים)</li>
                      <li>✓ התראות על מלאי נמוך</li>
                      <li>✓ תעודות משלוח ללקוחות</li>
                      <li>✓ דוחות שבועיים (בעתיד)</li>
                    </ul>
                  </div>
                </div>
              )}
            </>
          )}
        </CardContent>
      </Card>

      {/* Save Button */}
      <div className="flex justify-end">
        <Button onClick={handleSave} size="lg">
          {t('common.save')}
        </Button>
      </div>
    </div>
  )
}
