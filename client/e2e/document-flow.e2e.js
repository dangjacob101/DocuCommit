import { test, expect } from '@playwright/test'

const PASSWORD = 'TestPass1!'

function unique(prefix) {
  return `${prefix}_${Date.now()}_${Math.floor(Math.random() * 1e6)}`
}

async function registerNewUser(page) {
  const email = `${unique('e2e')}@example.com`
  await page.goto('/')
  // flip from the default Sign In view to the Create Account view
  await page.getByRole('button', { name: 'Sign Up' }).click()
  await expect(page.getByRole('heading', { name: 'Create Account' })).toBeVisible()
  await page.locator('#login-email').fill(email)
  await page.locator('#login-first-name').fill('Test')
  await page.locator('#login-last-name').fill('User')
  await page.locator('#login-password').fill(PASSWORD)
  await page.locator('#login-submit').click()
  await expect(page.getByRole('heading', { name: 'Projects' })).toBeVisible()
  return email
}

async function createProject(page, name) {
  await page.getByRole('button', { name: 'New Project' }).click()
  await expect(page.getByRole('heading', { name: 'New Project' })).toBeVisible()
  await page.getByPlaceholder('e.g. Acme Engagement').fill(name)
  await page.getByRole('button', { name: 'Create' }).click()
  await expect(page.getByRole('heading', { name })).toBeVisible()
}

async function createDocument(page, title) {
  await page.getByRole('button', { name: 'New Document' }).click()
  await expect(page.getByRole('heading', { name: 'New Document' })).toBeVisible()
  await page.getByPlaceholder('e.g. Acme Services Agreement').fill(title)
  await page.getByRole('button', { name: 'Save' }).click()
  await expect(page).toHaveURL(/\/branches\//)
}

test('a user can register, create a project, and add a document to it', async ({ page }) => {
  await registerNewUser(page)

  const projectName = unique('Acme Engagement')
  await createProject(page, projectName)

  const docTitle = unique('Acme Services Agreement')
  await createDocument(page, docTitle)

  await page.goto('/')
  await page.getByRole('button', { name: projectName }).click()
  await expect(page.getByRole('button', { name: docTitle })).toBeVisible()
})

test('documents created in one project do not show up in another', async ({ page }) => {
  await registerNewUser(page)

  const acme = unique('Acme')
  const globex = unique('Globex')

  await createProject(page, acme)
  const docTitle = unique('Engagement Letter')
  await createDocument(page, docTitle)

  await page.goto('/')
  await createProject(page, globex)

  await expect(page.getByRole('button', { name: docTitle })).toHaveCount(0)

  await page.goto('/')
  await page.getByRole('button', { name: acme }).click()
  await expect(page.getByRole('button', { name: docTitle })).toBeVisible()
})
