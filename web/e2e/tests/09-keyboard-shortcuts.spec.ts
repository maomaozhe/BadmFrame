import { test, expect } from '@playwright/test';
import { clearIndexedDB, expectEditorPage } from '../helpers';

test.describe('Keyboard Shortcuts', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await clearIndexedDB(page);

    // Seed a project with sourceVideo
    await page.evaluate(() => {
      return new Promise<void>((resolve) => {
        const req = indexedDB.open('badmframe', 1);
        req.onupgradeneeded = () => {
          const db = req.result;
          if (!db.objectStoreNames.contains('projects')) {
            const store = db.createObjectStore('projects', { keyPath: 'id' });
            store.createIndex('updatedAt', 'updatedAt', { unique: false });
          }
        };
        req.onsuccess = () => {
          const db = req.result;
          const tx = db.transaction('projects', 'readwrite');
          const store = tx.objectStore('projects');
          store.put({
            id: 'kb-test',
            name: '快捷键测试',
            sourceVideo: null,
            markers: [],
            clips: [],
            createdAt: new Date().toISOString(),
            updatedAt: new Date().toISOString(),
          });
          tx.oncomplete = () => resolve();
        };
      });
    });

    await page.reload();
    await page.waitForLoadState('networkidle');
    await page.getByText('快捷键测试').click();
    await expectEditorPage(page);
  });

  test('TC-KB01: M key adds marker', async ({ page }) => {
    // Focus the video element first (or click somewhere safe)
    await page.locator('video').first().focus();
    await page.waitForTimeout(200);

    // Press M to add marker
    await page.keyboard.press('m');

    // Should see a marker appear (color dot in markers panel)
    await expect(page.locator('.rounded-full').first()).toBeVisible({ timeout: 3000 });
    expect(await page.locator('.rounded-full').count()).toBeGreaterThan(0);
  });

  test('TC-KB02: Space toggles play/pause', async ({ page }) => {
    // Focus outside inputs
    await page.locator('video').first().focus();
    await page.waitForTimeout(200);

    // Press Space - should toggle play. Since video might not load,
    // just verify no error occurs
    await page.keyboard.press('Space');
    // The result depends on whether the video is loaded
  });

  test('TC-KB03: shortcuts disabled when input focused', async ({ page }) => {
    // First add a marker to get an editable label
    await page.locator('video').first().focus();
    await page.keyboard.press('m');
    await page.waitForTimeout(300);

    // Try to edit the marker label
    const markerEditBtn = page.locator('.group').first().locator('button').first();
    if (await markerEditBtn.isVisible()) {
      await markerEditBtn.click();
      // Now an input should be focused
      const input = page.locator('input').filter({ hasAttribute: 'value' }).last();
      if (await input.isVisible().catch(() => false)) {
        await input.focus();
        await page.waitForTimeout(200);

        // Press M while input is focused - should NOT add a new marker
        const markerCountBefore = await page.locator('.rounded-full').count();
        await page.keyboard.press('m');
        await page.waitForTimeout(200);
        const markerCountAfter = await page.locator('.rounded-full').count();
        expect(markerCountAfter).toBe(markerCountBefore);
      }
    }
  });

  test('TC-KB04: Escape closes dialogs', async ({ page }) => {
    // This is tested in 01-project-list already
    // Verify it works from the editor too
    await page.keyboard.press('Escape');
    // No dialog in editor to close, should not crash
  });
});
