/** Verify the actual Dispatcher prediction/forecast UI against a running local stack. */
import { chromium, expect } from '../../../frontend/node_modules/@playwright/test/index.mjs'
const frontend = process.env.FRONTEND_BASE_URL ?? 'http://localhost:5173'
const api = process.env.API_BASE_URL ?? 'http://localhost:8000'
for (const address of [frontend, api]) if (!['localhost', '127.0.0.1'].includes(new URL(address).hostname)) throw new Error('Local acceptance stack required')
const browser = await chromium.launch({ headless: true, ...(process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE ? { executablePath: process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE } : {}) })
try {
  const page = await browser.newPage()
  const errors = []
  page.on('pageerror', (error) => errors.push(error.message))
  await page.goto(frontend + '/login')
  await page.getByLabel('Email or employee ID').fill('dispatcher')
  await page.getByLabel('Password', { exact: true }).fill(process.env.DEMO_PASSWORD)
  await page.getByRole('button', { name: 'Sign in', exact: true }).click()
  await page.waitForURL('**/dispatcher/orders')
  await page.goto(frontend + '/dispatcher/planning')
  const response = page.waitForResponse((r) => r.url().includes('/analytics/plan-predictions'))
  await page.getByRole('button', { name: 'Estimate saved plan', exact: true }).click()
  const result = await response
  if (!result.ok()) throw new Error(await result.text())
  const predictions = (await result.json()).predictions
  if (!predictions.length) throw new Error('Expected real saved-plan predictions')
  await expect(page.getByRole('cell', { name: predictions[0].delivery_id, exact: true })).toBeVisible()
  await page.goto(frontend + '/dispatcher/analytics')
  await expect(page.getByRole('heading', { name: 'Demand forecast', exact: true })).toBeVisible()
  await expect(page.getByText(/Saved datathon Ridge ensemble/)).toBeVisible()
  if (errors.length) throw new Error(JSON.stringify(errors))
  console.log(JSON.stringify({ real_dispatcher_plan_predictions: predictions.length, learned_forecast_ui: 'passed', javascript_errors: errors.length }))
} finally {
  await browser.close()
}
