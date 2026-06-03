import { test, expect } from '@playwright/test'

// week 7 - end-to-end user-flow tests.
//
// these drive a real browser through the actual UI and hit the real backend,
// exercising a meaningful slice of both client and server code: auth
// (register), document creation (POST /api/documents), the dashboard listing
// (GET /api/documents), and the search feature.
//
// each test makes its own unique user + document titles so the tests are
// independent and repeatable (they don't depend on order or shared state).

const PASSWORD = 'TestPass1!'

function unique(prefix) {
  return `${prefix}_${Date.now()}_${Math.floor(Math.random() * 1e6)}`
}

async function registerNewUser(page) {
  const username = unique('e2e')
  await page.goto('/')
  // flip from the default Sign In view to the Create Account view
  await page.getByRole('button', { name: 'Sign Up' }).click()
  await expect(page.getByRole('heading', { name: 'Create Account' })).toBeVisible()
  await page.locator('#login-username').fill(username)
  await page.locator('#login-password').fill(PASSWORD)
  await page.locator('#login-submit').click()
  // a successful register logs us in and drops us on the dashboard
  await expect(page.getByRole('heading', { name: 'Documents' })).toBeVisible()
  return username
}

async function createDocument(page, title, content) {
  await page.getByRole('button', { name: 'New Document' }).click()
  await expect(page.getByRole('heading', { name: 'New Document' })).toBeVisible()
  await page.getByPlaceholder('e.g. Acme Services Agreement').fill(title)
  await page.getByPlaceholder('Start typing the document...').fill(content)
  await page.getByRole('button', { name: 'Save' }).click()
  // saving creates the doc and navigates into its Main-branch editor
  await expect(page).toHaveURL(/\/branches\//)
}

test('a user can register, create a document, and see it on the dashboard', async ({ page }) => {
  await registerNewUser(page)

  const title = unique('Acme Services Agreement')
  await createDocument(page, title, 'This agreement is made between the parties.')

  // navigate back to the dashboard - the new document should be listed
  await page.goto('/')
  await expect(page.getByRole('button', { name: title })).toBeVisible()
})

test('a user can search their documents by title', async ({ page }) => {
  await registerNewUser(page)

  const acme = unique('Acme Agreement')
  const globex = unique('Globex Lease')
  await createDocument(page, acme, 'alpha content')
  await page.goto('/')
  await createDocument(page, globex, 'beta content')
  await page.goto('/')

  // both documents are visible before searching
  await expect(page.getByRole('button', { name: acme })).toBeVisible()
  await expect(page.getByRole('button', { name: globex })).toBeVisible()

  // typing a query narrows the list to matching titles only
  await page.locator('#search-documents').fill('Globex')
  await expect(page.getByRole('button', { name: globex })).toBeVisible()
  await expect(page.getByRole('button', { name: acme })).toHaveCount(0)

  // a query that matches nothing shows the empty state
  await page.locator('#search-documents').fill('zzzz-no-such-document')
  await expect(page.getByText(/No documents matching/)).toBeVisible()
})
