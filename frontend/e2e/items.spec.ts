import { test, expect } from '@playwright/test'

test.describe('Items Management', () => {
  // Setup: Login before each test
  test.beforeEach(async ({ page }) => {
    await page.goto('/login')
    await page.getByLabel(/שם משתמש/i).fill('admin')
    await page.getByLabel(/סיסמה/i).fill('admin123456')
    await page.getByRole('button', { name: /התחבר/i }).click()
    await expect(page).toHaveURL('/')
    
    // Navigate to items page
    await page.getByRole('link', { name: /פריטים/i }).click()
    await expect(page).toHaveURL('/items')
  })

  test('should display items list', async ({ page }) => {
    // Wait for items to load
    await expect(page.getByRole('table')).toBeVisible({ timeout: 10000 })
    
    // Check for table headers
    await expect(page.getByText(/מק"ט/i)).toBeVisible()
    await expect(page.getByText(/שם/i)).toBeVisible()
    await expect(page.getByText(/ספק/i)).toBeVisible()
  })

  test('should open add item dialog', async ({ page }) => {
    // Click add button
    await page.getByRole('button', { name: /הוסף פריט/i }).click()
    
    // Dialog should be visible
    await expect(page.getByText(/פריט חדש|הוסף פריט/i)).toBeVisible({ timeout: 5000 })
    await expect(page.getByLabel(/מק"ט/i)).toBeVisible()
  })

  test('should create new item', async ({ page }) => {
    // Open dialog
    await page.getByRole('button', { name: /הוסף פריט/i }).click()
    await expect(page.getByLabel(/מק"ט/i)).toBeVisible({ timeout: 5000 })
    
    // Fill form
    const timestamp = Date.now()
    await page.getByLabel(/מק"ט/i).fill(`TEST-${timestamp}`)
    await page.getByLabel(/^שם/i).first().fill(`Test Item ${timestamp}`)
    await page.getByLabel(/ספק/i).fill('Test Supplier')
    await page.getByLabel(/יחידת מידה/i).fill('Liter')
    await page.getByLabel(/מחיר עלות/i).fill('100')
    
    // Submit
    await page.getByRole('button', { name: /שמור/i }).click()
    
    // Should show success (item in table)
    await expect(page.getByText(`TEST-${timestamp}`)).toBeVisible({ timeout: 10000 })
  })

  test('should search items', async ({ page }) => {
    // Wait for items to load
    await expect(page.getByRole('table')).toBeVisible({ timeout: 10000 })
    
    // Use search
    await page.getByPlaceholder(/חיפוש/i).fill('INK')
    
    // Results should update
    await page.waitForTimeout(1000) // Wait for debounce
    await expect(page.getByRole('table')).toBeVisible()
  })
})

