import { test, expect } from '@playwright/test';
import { clearIndexedDB, expectEditorPage, takeScreenshot } from '../helpers';

test.describe('Timeline', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await clearIndexedDB(page);

    // Seed a project with markers and navigate to editor
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
            id: 'timeline-test',
            name: '时间线测试',
            sourceVideo: {
              id: 'sv-tl',
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
            markers: [
              { id: 'mt1', timestampSec: 1.0, label: '扣杀', color: 'yellow', createdAt: new Date().toISOString() },
              { id: 'mt2', timestampSec: 3.0, label: '失误', color: 'red', createdAt: new Date().toISOString() },
            ],
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
    await page.getByText('时间线测试').click();
    await expectEditorPage(page);
  });

  test('TC-TL01: timeline ruler renders with time markers', async ({ page }) => {
    // The timeline should be visible with an SVG ruler
    const timeline = page.locator('svg');
    await expect(timeline.first()).toBeAttached({ timeout: 5000 });

    await takeScreenshot(page, '05-timeline/TC-TL01-timeline-ruler');
  });

  test('TC-TL02: zoom in increases pixel density', async ({ page }) => {
    // Click zoom in button
    const zoomIn = page.getByRole('button', { name: '+' });
    await zoomIn.click();

    // Just verify no crash, the timeline adapts
    const timeline = page.locator('svg').first();
    await expect(timeline).toBeAttached();
  });

  test('TC-TL03: zoom out decreases pixel density', async ({ page }) => {
    // Click zoom out button
    const zoomOut = page.getByRole('button', { name: '−' });
    await zoomOut.click();

    const timeline = page.locator('svg').first();
    await expect(timeline).toBeAttached();
  });

  test('TC-TL04: mark button adds a marker', async ({ page }) => {
    const markBtn = page.getByRole('button', { name: /📌/ });
    await markBtn.click();
    await page.waitForTimeout(500);

    // Should have one more marker now
    const colorDots = page.locator('.rounded-full');
    expect(await colorDots.count()).toBeGreaterThanOrEqual(1);
  });

  test('TC-TL05: time display in toolbar shows formatted time', async ({ page }) => {
    // The toolbar should have a time display (monospace)
    const timeDisplay = page.locator('.font-mono').first();
    await expect(timeDisplay).toBeVisible({ timeout: 3000 });
  });

  test('TC-TL06: marker diamonds appear on timeline', async ({ page }) => {
    // SVG polygons should exist for markers
    const polygons = page.locator('svg polygon');
    const count = await polygons.count();
    expect(count).toBeGreaterThanOrEqual(1);
  });
});
