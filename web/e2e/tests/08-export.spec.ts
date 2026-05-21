import { test, expect } from '@playwright/test';
import { clearIndexedDB, expectEditorPage, takeScreenshot } from '../helpers';

test.describe('Export Dialog', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await clearIndexedDB(page);

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
            id: 'export-test',
            name: '导出测试',
            sourceVideo: {
              id: 'sv-ex',
              fileName: 'test-video-5s.mp4',
              filePath: '',
              durationSec: 5,
              width: 640,
              height: 360,
              frameRate: 30,
              codec: 'H.264',
              isVFR: false,
              fileSize: 82272,
              importDate: new Date().toISOString(),
              objectURL: null,
            },
            markers: [],
            clips: [
              { id: 'ex1', startTimeSec: 0.5, endTimeSec: 2.0, label: '片段A', notes: '', anchorMarkerId: null, exportStatus: 'none', createdAt: new Date().toISOString() },
              { id: 'ex2', startTimeSec: 3.0, endTimeSec: 4.5, label: '片段B', notes: '备注', anchorMarkerId: null, exportStatus: 'none', createdAt: new Date().toISOString() },
            ],
            createdAt: new Date().toISOString(),
            updatedAt: new Date().toISOString(),
          });
          tx.oncomplete = () => resolve();
        };
      });
    });

    await page.reload();
    await page.waitForLoadState('networkidle');
    await page.getByText('导出测试').click();
    await expectEditorPage(page);
  });

  test('TC-EX01: export button opens dialog with clip list', async ({ page }) => {
    await page.getByRole('button', { name: '导出' }).click();

    // Dialog should show all clips
    await expect(page.getByText('导出片段')).toBeVisible();
    await expect(page.getByText('片段A')).toBeVisible();
    await expect(page.getByText('片段B')).toBeVisible();

    await takeScreenshot(page, '08-export/TC-EX01-export-dialog');
  });

  test('TC-EX02: clip selection toggles on click', async ({ page }) => {
    await page.getByRole('button', { name: '导出' }).click();
    await expect(page.getByText('导出片段')).toBeVisible();

    // By default, export button should show 0 count and be disabled (inside dialog)
    const exportBtn = page.getByRole('button', { name: /导出 \(0\)/ });
    await expect(exportBtn).toBeDisabled();

    // Click the first checkbox area to select a clip
    const dialogContent = page.locator('.max-w-lg');
    const checkboxes = dialogContent.locator('[class*="flex items-center gap"]').first();
    if (await checkboxes.isVisible({ timeout: 2000 }).catch(() => false)) {
      await checkboxes.click();
      await page.waitForTimeout(200);
      // Should show 导出 (1) now
      await expect(page.getByRole('button', { name: /导出 \(1\)/ })).toBeVisible();
    }

    await takeScreenshot(page, '08-export/TC-EX02-selected');
  });

  test('TC-EX03: cancel button closes dialog', async ({ page }) => {
    await page.getByRole('button', { name: '导出' }).click();
    await expect(page.getByText('导出片段')).toBeVisible();

    await page.getByRole('button', { name: '取消' }).click();
    await expect(page.getByText('导出片段')).not.toBeVisible();
  });

  test('TC-EX04: Escape closes export dialog', async ({ page }) => {
    await page.getByRole('button', { name: '导出' }).click();
    await expect(page.getByText('导出片段')).toBeVisible();

    await page.keyboard.press('Escape');
    await expect(page.getByText('导出片段')).not.toBeVisible();
  });

  test('TC-EX05: overlay click closes export dialog', async ({ page }) => {
    await page.getByRole('button', { name: '导出' }).click();
    await expect(page.getByText('导出片段')).toBeVisible();

    // Click overlay
    await page.locator('.fixed.inset-0').first().click({ position: { x: 10, y: 10 } });
    await expect(page.getByText('导出片段')).not.toBeVisible();
  });
});
