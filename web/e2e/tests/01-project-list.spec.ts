import { test, expect } from '@playwright/test';
import { clearIndexedDB, expectProjectListPage, takeScreenshot } from '../helpers';

test.describe('Project List Page', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await clearIndexedDB(page);
    await page.reload();
    await page.waitForLoadState('networkidle');
  });

  test('TC-PL01: empty state renders correctly', async ({ page }) => {
    await expectProjectListPage(page);

    await expect(page.getByText('还没有打球记录')).toBeVisible();
    await expect(page.getByText('导入一段羽毛球视频，开始标记精彩瞬间')).toBeVisible();
    await expect(page.getByRole('button', { name: '导入视频' })).toBeVisible();

    await takeScreenshot(page, '01-project-list/TC-PL01-empty-state');
  });

  test('TC-PL02: import button opens import dialog', async ({ page }) => {
    await page.getByRole('button', { name: '导入视频' }).click();

    // Dialog content should be visible
    await expect(page.getByText('支持 MP4、MOV 等常见视频格式')).toBeVisible();
    await expect(page.getByRole('button', { name: '选择视频文件' })).toBeVisible();

    await takeScreenshot(page, '01-project-list/TC-PL02-import-dialog');

    // Close via Escape
    await page.keyboard.press('Escape');
    await expect(page.getByText('选择视频文件')).not.toBeVisible();
  });

  test('TC-PL03: import dialog closes on overlay click', async ({ page }) => {
    await page.getByRole('button', { name: '导入视频' }).click();
    await expect(page.getByText('选择视频文件')).toBeVisible();

    // Click the overlay (first fixed inset-0 div)
    await page.locator('.fixed.inset-0').first().click({ position: { x: 10, y: 10 } });

    await expect(page.getByText('选择视频文件')).not.toBeVisible();
  });

  test('TC-PL04: escape closes import dialog', async ({ page }) => {
    await page.getByRole('button', { name: '导入视频' }).click();
    await expect(page.getByText('选择视频文件')).toBeVisible();

    await page.keyboard.press('Escape');
    await expect(page.getByText('选择视频文件')).not.toBeVisible();
  });

  test('TC-PL05: project appears in list after creation', async ({ page }) => {
    await expect(page.getByText('还没有打球记录')).toBeVisible();

    // Import a video to create a project
    await page.getByRole('button', { name: '导入视频' }).click();
    await expect(page.getByText('选择视频文件')).toBeVisible();

    const fileInput = page.locator('input[type="file"]');
    await fileInput.setInputFiles('e2e/fixtures/test-video-5s.mp4');
    await page.waitForSelector('button:has-text("创建项目")', { timeout: 10000 });

    // Change project name
    const nameInput = page.locator('input[value]').first();
    await nameInput.fill('我的第一场球局');
    await page.getByRole('button', { name: '创建项目' }).click();

    // Wait for editor
    await expect(page.getByRole('button', { name: /返回/ })).toBeVisible();

    // Go back to project list
    await page.getByRole('button', { name: /返回/ }).click();
    await page.waitForLoadState('networkidle');

    // Project should appear in list
    await expect(page.getByText('我的第一场球局')).toBeVisible();
    await expect(page.getByText('还没有打球记录')).not.toBeVisible();

    await takeScreenshot(page, '01-project-list/TC-PL05-project-in-list');
  });

  test('TC-PL06: clicking project card navigates to editor', async ({ page }) => {
    // First create a project via seeding
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
            id: 'test-project-1',
            name: '测试打球记录',
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

    // Click the project card
    await page.getByText('测试打球记录').click();

    // Should be in editor
    await expect(page.getByRole('button', { name: /返回/ })).toBeVisible();

    await takeScreenshot(page, '01-project-list/TC-PL06-editor-navigation');
  });

  test('TC-PL07: hovering project reveals delete button, accepting deletes', async ({ page }) => {
    // Seed a project
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
            id: 'test-project-2',
            name: '待删除项目',
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

    await expect(page.getByText('待删除项目')).toBeVisible();

    // Handle the confirm dialog
    page.on('dialog', async (dialog) => {
      expect(dialog.message()).toContain('确定删除');
      await dialog.accept();
    });

    // Hover over project card to reveal delete button
    const projectCard = page.locator('.group').filter({ has: page.getByText('待删除项目') }).first();
    await projectCard.hover();

    // Click delete button
    await projectCard.getByRole('button', { name: '删除' }).click();

    // Wait for the deletion
    await page.waitForTimeout(500);
    await expect(page.getByText('待删除项目')).not.toBeVisible();
    await expect(page.getByText('还没有打球记录')).toBeVisible();

    await takeScreenshot(page, '01-project-list/TC-PL07-after-delete');
  });

  test('TC-PL08: rejecting delete confirm keeps project', async ({ page }) => {
    // Seed a project
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
            id: 'test-project-3',
            name: '不会删除的项目',
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

    await expect(page.getByText('不会删除的项目')).toBeVisible();

    // Handle the confirm dialog - dismiss
    page.on('dialog', async (dialog) => {
      await dialog.dismiss();
    });

    const projectCard = page.locator('.group').filter({ has: page.getByText('不会删除的项目') }).first();
    await projectCard.hover();
    await projectCard.getByRole('button', { name: '删除' }).click();

    await page.waitForTimeout(500);
    // Project should still exist
    await expect(page.getByText('不会删除的项目')).toBeVisible();
  });
});
