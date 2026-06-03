import { test, expect } from '@playwright/test'

// basic check: load the app in a browser and make sure the login page shows.
test('app loads and shows the login page', async ({ page }) => {
  await page.goto('/')

  // header is always there whether you're logged in or not
  await expect(page.getByRole('heading', { name: 'DocuCommit' })).toBeVisible()

  // an unauthenticated visitor lands on the sign-in form
  await expect(page.getByRole('heading', { name: 'Sign In' })).toBeVisible()
  await expect(page.locator('#login-username')).toBeVisible()
  await expect(page.locator('#login-password')).toBeVisible()
  await expect(page.locator('#login-submit')).toBeVisible()
})
