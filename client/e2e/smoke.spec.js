import { test, expect } from '@playwright/test'

// week 7 - first end-to-end smoke test.
//
// the simplest possible full-stack check: drive a real browser to the app
// and confirm it boots and renders the login page. if this passes, the
// frontend builds, serves, and mounts, and the backend is reachable enough
// for the app shell to come up.
test('app loads and shows the login page', async ({ page }) => {
  await page.goto('/')

  // the app header is always present, logged in or not
  await expect(page.getByRole('heading', { name: 'DocuCommit' })).toBeVisible()

  // an unauthenticated visitor lands on the sign-in form
  await expect(page.getByRole('heading', { name: 'Sign In' })).toBeVisible()
  await expect(page.locator('#login-username')).toBeVisible()
  await expect(page.locator('#login-password')).toBeVisible()
  await expect(page.locator('#login-submit')).toBeVisible()
})
