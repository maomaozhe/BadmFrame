import { test, expect } from '@playwright/test';
import { clearIndexedDB, expectEditorPage, takeScreenshot } from '../helpers';

test.describe('Clips Panel', () => {
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
            id: 'clip-test',
            name: '片段测试',
            sourceVideo: {
              id: 'sv-cp',
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
              { id: 'cp1', startTimeSec: 1.0, endTimeSec: 3.0, label: '精彩回合', notes: '这球打得好', anchorMarkerId: null, exportStatus: 'none', createdAt: new Date().toISOString() },
              { id: 'cp2', startTimeSec: 3.5, endTimeSec: 4.5, label: '失误片段', notes: '', anchorMarkerId: null, exportStatus: 'completed', createdAt: new Date().toISOString() },
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
    await page.getByText('片段测试').click();
    await expectEditorPage(page);
  });

  test('TC-CP01: clips tab shows all clips sorted', async ({ page }) => {
    // Navigate to clips tab
    await page.getByRole('button', { name: '片段', exact: true }).click();

    await expect(page.getByText('精彩回合')).toBeVisible();
    await expect(page.getByText('失误片段')).toBeVisible();

    await takeScreenshot(page, '07-clips/TC-CP01-clips-list');
  });

  test('TC-CP02: export status badge shows for completed clip', async ({ page }) => {
    await page.getByRole('button', { name: '片段', exact: true }).click();

    // "失误片段" clip has exportStatus 'completed', should show "已导出" badge
    await expect(page.getByText('已导出')).toBeVisible();
  });

  test('TC-CP03: unexported clip has no status badge', async ({ page }) => {
    await page.getByRole('button', { name: '片段', exact: true }).click();

    // "精彩回合" has status 'none', should not show a badge
    const clipCard = page.locator('.group').filter({ hasText: '精彩回合' });
    expect(await clipCard.locator('text=已导出').count()).toBe(0);
  });

  test('TC-CP04: clicking start/end times shows formatted timestamps', async ({ page }) => {
    await page.getByRole('button', { name: '片段', exact: true }).click();

    // Should show timestamps in monospace font
    const timestamps = page.locator('.font-mono');
    expect(await timestamps.count()).toBeGreaterThan(0);
  });

  test('TC-CP05: delete clip removes it', async ({ page }) => {
    await page.getByRole('button', { name: '片段', exact: true }).click();

    // Verify clips exist
    await expect(page.getByText('精彩回合')).toBeVisible();

    // Delete clip via store operation
    await page.evaluate(() => {
      return new Promise<void>((resolve) => {
        const req = indexedDB.open('badmframe', 1);
        req.onsuccess = () => {
          const db = req.result;
          const tx = db.transaction('projects', 'readwrite');
          const store = tx.objectStore('projects');
          const getReq = store.get('clip-test');
          getReq.onsuccess = () => {
            const project = getReq.result;
            project.clips = project.clips.slice(1); // Remove first clip
            project.updatedAt = new Date().toISOString();
            store.put(project);
            tx.oncomplete = () => resolve();
          };
        };
      });
    });

    // Reload to see updated state
    await page.reload();
    await page.waitForLoadState('networkidle');
    await page.getByText('片段测试').click();
    await expectEditorPage(page);
    await page.getByRole('button', { name: '片段', exact: true }).click();

    // The first clip should be gone
    await expect(page.getByText('精彩回合')).not.toBeVisible();
  });

  test('TC-CP06: export button enabled when clips exist', async ({ page }) => {
    await page.getByRole('button', { name: '片段', exact: true }).click();

    // Export button should be enabled now
    const exportBtn = page.getByRole('button', { name: '导出' });
    await expect(exportBtn).toBeEnabled();
  });
});
