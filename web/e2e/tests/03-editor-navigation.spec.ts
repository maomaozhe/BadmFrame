import { test, expect } from '@playwright/test';
import { clearIndexedDB, expectEditorPage, expectProjectListPage, takeScreenshot } from '../helpers';

test.describe('Editor Navigation', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await clearIndexedDB(page);

    // Seed a project and navigate to editor
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
            id: 'nav-test-project',
            name: '测试导航项目',
            sourceVideo: null,
            markers: [
              { id: 'm1', timestampSec: 1.5, label: '测试标记', color: 'yellow', createdAt: new Date().toISOString() },
            ],
            clips: [
              { id: 'c1', startTimeSec: 0, endTimeSec: 5, label: '测试片段', notes: '', anchorMarkerId: 'm1', exportStatus: 'none', createdAt: new Date().toISOString() },
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
  });

  async function navigateToEditor(page) {
    await page.getByText('测试导航项目').click();
    await expectEditorPage(page);
  }

  test('TC-ED01: editor header shows project name and back button', async ({ page }) => {
    await navigateToEditor(page);

    // Header elements
    await expect(page.getByRole('button', { name: /返回/ })).toBeVisible();
    await expect(page.getByText('测试导航项目')).toBeVisible();

    await takeScreenshot(page, '03-editor-navigation/TC-ED01-header');
  });

  test('TC-ED02: three tabs render, markers selected by default', async ({ page }) => {
    await navigateToEditor(page);

    // Three tab buttons should exist
    await expect(page.getByRole('button', { name: '标记', exact: true })).toBeVisible();
    await expect(page.getByRole('button', { name: '片段', exact: true })).toBeVisible();
    await expect(page.getByRole('button', { name: '信息', exact: true })).toBeVisible();

    // Markers tab should show marker content
    await expect(page.getByText('测试标记')).toBeVisible();

    await takeScreenshot(page, '03-editor-navigation/TC-ED02-markers-tab');
  });

  test('TC-ED03: clicking clips tab shows clip content', async ({ page }) => {
    await navigateToEditor(page);

    // Click clips tab
    await page.getByText('片段').click();

    // Clip content should be visible
    await expect(page.getByText('测试片段')).toBeVisible();

    await takeScreenshot(page, '03-editor-navigation/TC-ED03-clips-tab');
  });

  test('TC-ED04: clicking info tab shows project metadata', async ({ page }) => {
    await navigateToEditor(page);

    // Click info tab
    await page.getByText('信息').click();

    // Info tab content
    await expect(page.getByText('测试导航项目')).toBeVisible();
    await expect(page.getByText('标记数量')).toBeVisible();

    await takeScreenshot(page, '03-editor-navigation/TC-ED04-info-tab');
  });

  test('TC-ED05: export button disabled when no clips', async ({ page }) => {
    // Create a project with NO clips
    await page.evaluate(() => {
      return new Promise<void>((resolve) => {
        const req = indexedDB.open('badmframe', 1);
        req.onsuccess = () => {
          const db = req.result;
          const tx = db.transaction('projects', 'readwrite');
          const store = tx.objectStore('projects');
          store.put({
            id: 'no-clips-project',
            name: '无片段项目',
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
    await page.getByText('无片段项目').click();
    await expectEditorPage(page);

    // Export button should be disabled
    const exportBtn = page.getByRole('button', { name: '导出' });
    await expect(exportBtn).toBeDisabled();
  });

  test('TC-ED06: back button returns to project list', async ({ page }) => {
    await navigateToEditor(page);

    // Click back
    await page.getByRole('button', { name: /返回/ }).click();

    // Should be back at project list
    await expectProjectListPage(page);

    await takeScreenshot(page, '03-editor-navigation/TC-ED06-back-to-list');
  });

  test('TC-ED07: re-entering project restores state', async ({ page }) => {
    await navigateToEditor(page);

    // Verify markers exist
    await expect(page.getByText('测试标记')).toBeVisible();

    // Go back
    await page.getByRole('button', { name: /返回/ }).click();
    await expectProjectListPage(page);

    // Re-enter the same project
    await page.getByText('测试导航项目').click();
    await expectEditorPage(page);

    // Markers should still be there
    await expect(page.getByText('测试标记')).toBeVisible();
  });
});
