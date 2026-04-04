#!/usr/bin/env node
/**
 * Take screenshots of each Web UI tab for the walkthrough video.
 * Uses Playwright to navigate localhost:8000 with self-signed cert handling.
 */
import { chromium } from 'playwright';
import { resolve } from 'path';

const BASE_URL = 'https://localhost:8000';
const OUTPUT_DIR = resolve(import.meta.dirname, '../public/walkthrough');

const TABS = [
  { name: '01-dashboard', path: '/', waitFor: '.welcome-section, .dashboard-stats, h2' },
  { name: '02-search', path: '/#search', searchQuery: 'Azure DevOps', waitFor: '.search-results, .memory-card' },
  { name: '03-browse', path: '/#browse', waitFor: '.tag-cloud, .browse-tags' },
  { name: '04-documents', path: '/#documents', waitFor: '.document-ingestion, .upload-area' },
  { name: '05-manage', path: '/#manage', waitFor: '.bulk-operations, .tag-management' },
  { name: '06-analytics', path: '/#analytics', waitFor: '.key-metrics, .trends-charts' },
  { name: '07-quality', path: '/#quality', waitFor: '.quality-analytics, .quality-score' },
  { name: '08-api-docs', path: '/#api-docs', waitFor: '.api-documentation, .api-docs' },
];

async function main() {
  console.log('Launching browser...');
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    viewport: { width: 1920, height: 1080 },
    ignoreHTTPSErrors: true,
  });

  const page = await context.newPage();

  for (const tab of TABS) {
    const url = `${BASE_URL}${tab.path}`;
    console.log(`Navigating to ${tab.name}: ${url}`);

    await page.goto(url, { waitUntil: 'networkidle', timeout: 15000 });
    await page.waitForTimeout(1500);

    // If search tab, type a query
    if (tab.searchQuery) {
      try {
        const searchInput = await page.$('input[type="search"], input[placeholder*="Search"], .search-input input');
        if (searchInput) {
          await searchInput.fill(tab.searchQuery);
          await page.keyboard.press('Enter');
          await page.waitForTimeout(2000);
        }
      } catch (e) {
        console.log(`  Search input not found, continuing...`);
      }
    }

    // Try to wait for specific content, fall back to timeout
    try {
      await page.waitForSelector(tab.waitFor, { timeout: 5000 });
    } catch (e) {
      console.log(`  Selector "${tab.waitFor}" not found, using timeout fallback`);
      await page.waitForTimeout(2000);
    }

    const screenshotPath = `${OUTPUT_DIR}/${tab.name}.png`;
    await page.screenshot({ path: screenshotPath, fullPage: false });
    console.log(`  Saved: ${screenshotPath}`);
  }

  await browser.close();
  console.log('\nDone! All screenshots saved to:', OUTPUT_DIR);
}

main().catch(console.error);
