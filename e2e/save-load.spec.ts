import { test, expect } from '@playwright/test';

// This E2E test assumes the frontend dev server is running (npm start)
// and the backend API is reachable at http://localhost:8000

const API_URL = process.env.API_URL || 'http://localhost:8000';

test('save -> load -> refresh portfolio flow', async ({ page }) => {
  // Open frontend
  await page.goto('/');

  // Create a small mock portfolio programmatically by uploading CSV via import
  const csv = `Symbol,Quantity,Price ($),Value ($),Principal ($)*,Principal G/L ($)*\nAAPL,10,150,1500,1200,300`;
  const tmpFile = 'e2e/tmp_portfolio.csv';

  // Expose a file via input by writing to the test's working directory
  const fs = require('fs');
  fs.mkdirSync('e2e', { recursive: true });
  fs.writeFileSync(tmpFile, csv, 'utf8');

  // Click Upload area to reveal file input or use file chooser on hidden input
  const [fileChooser] = await Promise.all([
    page.waitForEvent('filechooser'),
    page.locator('#dropArea').click()
  ]);

  await fileChooser.setFiles(tmpFile);

  // Wait for dashboard to appear
  await page.waitForSelector('#dashboardSection', { state: 'visible', timeout: 10000 });

  // Open Save modal
  await page.click('#savePortfolioBtn');
  await page.waitForSelector('#saveModal', { state: 'visible' });

  // Enter name and confirm save
  await page.fill('#saveNameInput', 'E2E Test Portfolio');
  await page.click('#confirmSaveBtn');

  // Wait for modal to close and portfolios to be saved
  await page.waitForSelector('#saveModal', { state: 'hidden' });

  // Open Load modal and load the saved portfolio
  await page.click('#loadPortfolioBtn');
  await page.waitForSelector('#portfolioModal', { state: 'visible' });

  // Wait for list and click the Load button for the portfolio
  await page.waitForSelector('#portfolioList .load-portfolio', { timeout: 10000 });
  await page.click('#portfolioList .load-portfolio');

  // Dashboard should be visible and holdings table populated
  await page.waitForSelector('#holdingsTableBody tr', { timeout: 10000 });
  const firstSymbol = await page.textContent('#holdingsTableBody tr:first-child td:first-child');
  expect(firstSymbol).toContain('AAPL');

  // Click Refresh Prices
  await page.click('#refreshPricesBtn');

  // Expect lastRefreshed to update
  await expect(page.locator('#lastRefreshed')).not.toHaveText('Last refreshed: —');
});
