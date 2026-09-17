import { test, expect } from '@playwright/test';

test.describe('Full User Journey', () => {
  const testEmail = `journey-${Date.now()}@example.com`;
  const testPassword = 'TestPassword123!';

  test('Register → Login → Create todo → Toggle completion → Verify → Logout', async ({ page }) => {
    // Navigate to register page
    await page.goto('/register');

    // Register
    await page.fill('input[type="email"]', testEmail);
    await page.fill('input[type="password"]', testPassword);
    await page.fill('input[id="confirmPassword"]', testPassword);
    await page.click('button[type="submit"]');

    // Should redirect to dashboard after successful registration
    await expect(page).toHaveURL('/');
    await expect(page.locator(`text=${testEmail}`)).toBeVisible();

    // Create a todo - click "Add Todo" button
    await page.click('button:has-text("Add Todo")');

    // Fill the form in the dialog
    await page.fill('input[placeholder="What needs to be done?"]', 'E2E Test Todo');
    await page.click('button:has-text("Create")');

    // Verify todo appears in list
    await expect(page.locator('text=E2E Test Todo')).toBeVisible();

    // Toggle completion - click on the checkbox (radix-ui renders as div with role=checkbox)
    await page.locator('[role="checkbox"]').first().click();

    // Verify todo is marked as completed (strikethrough)
    await expect(page.locator('text=E2E Test Todo').first()).toHaveClass(/line-through/);

    // Toggle back to incomplete
    await page.locator('[role="checkbox"]').first().click();

    // Verify todo is no longer strikethrough
    await expect(page.locator('text=E2E Test Todo').first()).not.toHaveClass(/line-through/);

    // Logout
    await page.click('button:has-text("Logout")');

    // Should redirect to login page
    await expect(page).toHaveURL(/\/login/);
    await expect(page.locator('text=Welcome Back')).toBeVisible();
  });
});

test.describe('Cross-User Data Isolation', () => {
  test('User A creates todo, User B cannot see it', async ({ browser }) => {
    const userAEmail = `usera-${Date.now()}@example.com`;
    const userBEmail = `userb-${Date.now()}@example.com`;
    const password = 'TestPassword123!';
    const todoTitle = 'User A Private Todo';

    // Create first browser context for User A
    const contextA = await browser.newContext();
    const pageA = await contextA.newPage();

    // User A registers
    await pageA.goto('/register');
    await pageA.fill('input[type="email"]', userAEmail);
    await pageA.fill('input[type="password"]', password);
    await pageA.fill('input[id="confirmPassword"]', password);
    await pageA.click('button[type="submit"]');
    await expect(pageA).toHaveURL('/');

    // User A creates a todo - click "Add Todo" button
    await pageA.click('button:has-text("Add Todo")');
    await pageA.fill('input[placeholder="What needs to be done?"]', todoTitle);
    await pageA.click('button:has-text("Create")');
    await expect(pageA.locator(`text=${todoTitle}`)).toBeVisible();

    // Create second browser context for User B (simulates different session/browser)
    const contextB = await browser.newContext();
    const pageB = await contextB.newPage();

    // User B registers
    await pageB.goto('/register');
    await pageB.fill('input[type="email"]', userBEmail);
    await pageB.fill('input[type="password"]', password);
    await pageB.fill('input[id="confirmPassword"]', password);
    await pageB.click('button[type="submit"]');
    await expect(pageB).toHaveURL('/');

    // User B should NOT see User A's todo
    await expect(pageB.locator(`text=${todoTitle}`)).not.toBeVisible();

    // User B creates their own todo
    await pageB.click('button:has-text("Add Todo")');
    await pageB.fill('input[placeholder="What needs to be done?"]', 'User B Todo');
    await pageB.click('button:has-text("Create")');
    await expect(pageB.locator('text=User B Todo')).toBeVisible();

    // User A should NOT see User B's todo
    await expect(pageA.locator('text=User B Todo')).not.toBeVisible();

    // Cleanup
    await contextA.close();
    await contextB.close();
  });
});

test.describe('Session Switch Cache Isolation', () => {
  test('User B logging in the SAME browser must not see User A cached data', async ({ page }) => {
    const userAEmail = `switcha-${Date.now()}@example.com`;
    const userBEmail = `switchb-${Date.now()}@example.com`;
    const password = 'TestPassword123!';
    const userATodo = 'User A Private Todo (P1)';

    // User A registers and creates a todo
    await page.goto('/register');
    await page.fill('input[type="email"]', userAEmail);
    await page.fill('input[type="password"]', password);
    await page.fill('input[id="confirmPassword"]', password);
    await page.click('button[type="submit"]');
    await expect(page).toHaveURL('/');
    await page.click('button:has-text("Add Todo")');
    await page.fill('input[placeholder="What needs to be done?"]', userATodo);
    await page.click('button:has-text("Create")');
    await expect(page.locator(`text=${userATodo}`)).toBeVisible();

    // Logout
    await page.click('button:has-text("Logout")');
    await expect(page).toHaveURL(/\/login/);

    // User B registers in the SAME browser/tab (same React cache would persist)
    await page.goto('/register');
    await page.fill('input[type="email"]', userBEmail);
    await page.fill('input[type="password"]', password);
    await page.fill('input[id="confirmPassword"]', password);
    await page.click('button[type="submit"]');
    await expect(page).toHaveURL('/');

    // User B must NOT see User A's todo (cache cleared), and must see own email
    await expect(page.locator(`text=${userATodo}`)).not.toBeVisible();
    await expect(page.locator(`text=${userBEmail}`)).toBeVisible();
  });
});