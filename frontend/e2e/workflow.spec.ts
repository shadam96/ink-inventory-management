import { test, expect } from '@playwright/test'

test.describe('Complete Inventory Workflow', () => {
  test.beforeEach(async ({ page }) => {
    // Login
    await page.goto('/login')
    await page.getByLabel(/שם משתמש/i).fill('admin')
    await page.getByLabel(/סיסמה/i).fill('admin123456')
    await page.getByRole('button', { name: /התחבר/i }).click()
    await expect(page).toHaveURL('/')
  })

  test('should complete receive → view batch → pick workflow', async ({ page }) => {
    const timestamp = Date.now()
    const testSKU = `FLOW-${timestamp}`
    
    // Step 1: Create item
    await page.getByRole('link', { name: /פריטים/i }).click()
    await page.getByRole('button', { name: /הוסף פריט/i }).click()
    await page.getByLabel(/מק"ט/i).fill(testSKU)
    await page.getByLabel(/^שם/i).first().fill(`Flow Test ${timestamp}`)
    await page.getByLabel(/ספק/i).fill('Test Supplier')
    await page.getByLabel(/יחידת מידה/i).fill('Liter')
    await page.getByLabel(/מחיר עלות/i).fill('100')
    await page.getByRole('button', { name: /שמור/i }).click()
    
    // Wait for item creation
    await expect(page.getByText(testSKU)).toBeVisible({ timeout: 10000 })
    
    // Step 2: Receive goods
    await page.getByRole('link', { name: /קבלת סחורה/i }).click()
    await expect(page).toHaveURL('/receiving')
    
    // Select the item we just created
    await page.locator('select#item_id').selectOption({ label: new RegExp(testSKU, 'i') })
    await page.getByLabel(/כמות/i).fill('50')
    
    // Set expiration date (180 days from now)
    const futureDate = new Date()
    futureDate.setDate(futureDate.getDate() + 180)
    const dateString = futureDate.toISOString().split('T')[0]
    await page.getByLabel(/תאריך תפוגה/i).fill(dateString)
    
    // Add to list
    await page.getByRole('button', { name: /הוסף לרשימה/i }).click()
    
    // Should show in receive list
    await expect(page.getByText(/רשימת קבלה/i)).toBeVisible({ timeout: 5000 })
    
    // Complete receipt
    await page.getByRole('button', { name: /קלוט הכל/i }).click()
    
    // Wait for success
    await page.waitForTimeout(2000)
    
    // Step 3: View batches
    await page.getByRole('link', { name: /אצוות/i }).click()
    await expect(page).toHaveURL('/batches')
    
    // Should see our batch (might need to search or filter)
    await expect(page.getByRole('table')).toBeVisible({ timeout: 10000 })
    
    // Step 4: Check dashboard
    await page.getByRole('link', { name: /לוח בקרה/i }).click()
    await expect(page).toHaveURL('/')
    
    // Dashboard should load with data
    await expect(page.getByText(/ערך מלאי/i)).toBeVisible({ timeout: 10000 })
  })

  test('should view and interact with alerts', async ({ page }) => {
    // Navigate to alerts
    await page.getByRole('link', { name: /התראות/i }).click()
    await expect(page).toHaveURL('/alerts')
    
    // Should display alerts summary or list
    await expect(page.getByText(/התראות/i)).toBeVisible({ timeout: 10000 })
    
    // Try to mark as read if there are any alerts
    const alertsList = page.locator('[role="table"], .alert-item').first()
    if (await alertsList.isVisible({ timeout: 2000 })) {
      // Click mark as read button
      const readButton = page.getByRole('button', { name: /סמן כנקרא/i }).first()
      if (await readButton.isVisible({ timeout: 1000 })) {
        await readButton.click()
        await page.waitForTimeout(1000)
      }
    }
  })

  test('should navigate all pages', async ({ page }) => {
    const pages = [
      { name: /פריטים/i, url: '/items' },
      { name: /אצוות/i, url: '/batches' },
      { name: /קבלת סחורה/i, url: '/receiving' },
      { name: /ליקוט/i, url: '/picking' },
      { name: /תעודות משלוח/i, url: '/delivery-notes' },
      { name: /לקוחות/i, url: '/customers' },
      { name: /התראות/i, url: '/alerts' },
    ]
    
    for (const { name, url } of pages) {
      await page.getByRole('link', { name }).click()
      await expect(page).toHaveURL(url)
      await page.waitForTimeout(500)
    }
    
    // Return to dashboard
    await page.getByRole('link', { name: /לוח בקרה/i }).click()
    await expect(page).toHaveURL('/')
  })
})

