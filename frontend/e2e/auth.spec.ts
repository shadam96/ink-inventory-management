import { test, expect } from '@playwright/test'

test.describe('Authentication', () => {
  test('should display login page', async ({ page }) => {
    await page.goto('/')
    
    // Should redirect to login
    await expect(page).toHaveURL(/\/login/)
    await expect(page.getByRole('heading', { name: /מערכת ניהול מלאי דיו/i })).toBeVisible()
  })

  test('should login successfully', async ({ page }) => {
    await page.goto('/login')
    
    // Fill login form
    await page.getByLabel(/שם משתמש/i).fill('admin')
    await page.getByLabel(/סיסמה/i).fill('admin123456')
    await page.getByRole('button', { name: /התחבר/i }).click()
    
    // Should redirect to dashboard
    await expect(page).toHaveURL('/')
    await expect(page.getByText(/לוח בקרה/i)).toBeVisible({ timeout: 10000 })
  })

  test('should show error on invalid credentials', async ({ page }) => {
    await page.goto('/login')
    
    // Try invalid credentials
    await page.getByLabel(/שם משתמש/i).fill('invalid')
    await page.getByLabel(/סיסמה/i).fill('wrong')
    await page.getByRole('button', { name: /התחבר/i }).click()
    
    // Should show error (may need to adjust based on your error display)
    await expect(page.getByText(/שגיאה|נכשל/i)).toBeVisible({ timeout: 5000 })
  })

  test('should logout successfully', async ({ page }) => {
    // Login first
    await page.goto('/login')
    await page.getByLabel(/שם משתמש/i).fill('admin')
    await page.getByLabel(/סיסמה/i).fill('admin123456')
    await page.getByRole('button', { name: /התחבר/i }).click()
    await expect(page).toHaveURL('/')
    
    // Click logout (adjust selector based on your UI)
    await page.getByRole('button', { name: /התנתק/i }).click()
    
    // Should redirect to login
    await expect(page).toHaveURL(/\/login/)
  })
})

