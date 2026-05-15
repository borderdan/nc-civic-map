import { test, expect } from '@playwright/test';

test('mecknc.gov key user flows', async ({ page }) => {
  // Page Navigation / Load
  await page.goto('https://www.mecknc.gov/');

  // Data Rendering
  // Verify that the footer sign-up form rendered correctly
  const footerSignUpForm = page.locator('.webform-submission-footer-sign-up-form').first();
  await expect(footerSignUpForm).toBeAttached();

  // Form Interactions
  // Fill in the search form and submit
  const searchInput = page.locator('#edit-keyword');
  await expect(searchInput).toBeVisible();
  await searchInput.fill('parks');

  const searchForm = page.locator('#views-exposed-form-search-page-1');
  await expect(searchForm).toBeVisible();

  // Submit the form (simulate pressing Enter)
  await searchInput.press('Enter');

  // Verify Page Navigation / Results
  // Wait for the URL to change to the search results page
  await page.waitForURL('**/search?keyword=parks**');

  // Verify we are on the search page by checking the URL
  expect(page.url()).toContain('/search');
});
