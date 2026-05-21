import { test, expect } from '@playwright/test';
import { clearIndexedDB, expectProjectListPage, expectEditorPage, takeScreenshot } from '../helpers';

test.describe('Real Video Full Flow', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await clearIndexedDB(page);
    await page.reload();
    await page.waitForLoadState('networkidle');
  });

  test('TC-RV01: import real badminton video and verify metadata', async ({ page }) => {
    await expectProjectListPage(page);

    // Open import dialog
    await page.getByRole('button', { name: '导入视频' }).click();
    await expect(page.getByText('选择视频文件')).toBeVisible();

    // Select the real badminton video
    const fileInput = page.locator('input[type="file"]');
    await fileInput.setInputFiles('e2e/fixtures/140.mp4');

    // Wait for step 2 - metadata extraction from 94MB file may take a moment
    await expect(page.getByRole('button', { name: '创建项目' })).toBeVisible({ timeout: 30000 });

    // Verify metadata fields
    await expect(page.getByText('项目名称')).toBeVisible();
    await expect(page.getByText('时长')).toBeVisible();
    await expect(page.getByText('分辨率')).toBeVisible();
    await expect(page.getByText('文件大小')).toBeVisible();
    await expect(page.getByText(/140\.mp4/)).toBeVisible();

    // Screenshot of step 2
    await takeScreenshot(page, '10-real-video/TC-RV01-metadata-review');

    // Change project name
    const nameInput = page.locator('input[value]').first();
    await nameInput.fill('真实羽毛球比赛');

    // Create project
    await page.getByRole('button', { name: '创建项目' }).click();

    // Should navigate to editor
    await expectEditorPage(page);

    // Verify video element is present
    const video = page.locator('video');
    await expect(video).toBeAttached({ timeout: 10000 });

    await takeScreenshot(page, '10-real-video/TC-RV01-editor-with-video');
  });

  test('TC-RV02: play video and add markers', async ({ page }) => {
    // First import the video
    await page.getByRole('button', { name: '导入视频' }).click();
    await page.locator('input[type="file"]').setInputFiles('e2e/fixtures/140.mp4');
    await expect(page.getByRole('button', { name: '创建项目' })).toBeVisible({ timeout: 30000 });
    await page.getByRole('button', { name: '创建项目' }).click();
    await expectEditorPage(page);

    // Wait for video to load (metadata + first frames)
    // The loading overlay should disappear once loadedmetadata fires
    await page.waitForFunction(() => {
      const video = document.querySelector('video');
      return video && video.readyState >= 1;
    }, { timeout: 15000 });
    await page.waitForTimeout(500);

    // Take screenshot of initial editor state
    await takeScreenshot(page, '10-real-video/TC-RV02-editor-initial');

    // Add markers at different positions using M key
    // First, focus the video element
    await page.locator('video').first().focus();
    await page.waitForTimeout(500);

    // Add marker at beginning
    await page.keyboard.press('m');
    await page.waitForTimeout(300);

    // Try to play the video briefly (click video to start, force click past loading overlay)
    await page.locator('video').first().click({ force: true });
    await page.waitForTimeout(5000); // Let it play for 5 seconds

    // Add another marker
    await page.keyboard.press('m');
    await page.waitForTimeout(300);

    await takeScreenshot(page, '10-real-video/TC-RV02-markers-added');

    // Pause the video
    await page.locator('video').first().click();
    await page.waitForTimeout(300);

    // Verify at least 2 markers were added
    const markerElements = page.locator('.hover\\:bg-accent\\/50');
    const count = await markerElements.count();
    expect(count).toBeGreaterThanOrEqual(2);
  });

  test('TC-RV03: create clip from marker and check export', async ({ page }) => {
    // Import the video
    await page.getByRole('button', { name: '导入视频' }).click();
    await page.locator('input[type="file"]').setInputFiles('e2e/fixtures/140.mp4');
    await expect(page.getByRole('button', { name: '创建项目' })).toBeVisible({ timeout: 30000 });
    await page.getByRole('button', { name: '创建项目' }).click();
    await expectEditorPage(page);
    await page.waitForTimeout(1000);

    // Add a marker first
    await page.locator('video').first().focus();
    await page.waitForTimeout(300);
    await page.keyboard.press('m');
    await page.waitForTimeout(500);

    // Create clip from the marker using store operation
    await page.evaluate(() => {
      return new Promise<void>((resolve) => {
        const req = indexedDB.open('badmframe', 1);
        req.onsuccess = () => {
          const db = req.result;
          const tx = db.transaction('projects', 'readwrite');
          const store = tx.objectStore('projects');
          const getAllReq = store.getAll();
          getAllReq.onsuccess = () => {
            const projects = getAllReq.result;
            if (projects.length > 0) {
              const project = projects[0];
              const marker = project.markers[0];
              if (marker) {
                project.clips.push({
                  id: crypto.randomUUID(),
                  startTimeSec: Math.max(0, marker.timestampSec - 3),
                  endTimeSec: marker.timestampSec + 7,
                  label: '精彩回合',
                  notes: '真实比赛片段',
                  anchorMarkerId: marker.id,
                  exportStatus: 'none',
                  createdAt: new Date().toISOString(),
                });
              }
              project.updatedAt = new Date().toISOString();
              store.put(project);
            }
            tx.oncomplete = () => resolve();
          };
        };
      });
    });

    // Reload
    await page.reload();
    await page.waitForLoadState('networkidle');
    // Find the project and enter
    const projectCard = page.locator('.group').filter({ hasText: /140/ });
    if (await projectCard.count() > 0) {
      await projectCard.first().click();
    } else {
      await page.locator('.group').first().click();
    }
    await expectEditorPage(page);

    // Switch to clips tab
    await page.getByRole('button', { name: '片段', exact: true }).click();
    await page.waitForTimeout(500);

    // Should have the clip
    await expect(page.getByText('精彩回合').first()).toBeVisible({ timeout: 5000 });

    await takeScreenshot(page, '10-real-video/TC-RV03-clip-created');

    // Export button should be enabled
    const exportBtn = page.getByRole('button', { name: '导出' });
    await expect(exportBtn).toBeEnabled();

    // Open export dialog
    await exportBtn.click();
    await expect(page.getByText('导出片段')).toBeVisible();
    // In dialog, the clip label appears inside the export dialog
    await expect(page.locator('.max-w-lg').getByText('精彩回合')).toBeVisible();

    await takeScreenshot(page, '10-real-video/TC-RV03-export-dialog');
  });

  test('TC-RV04: project persists after returning to list', async ({ page }) => {
    // Import the video
    await page.getByRole('button', { name: '导入视频' }).click();
    await page.locator('input[type="file"]').setInputFiles('e2e/fixtures/140.mp4');
    await expect(page.getByRole('button', { name: '创建项目' })).toBeVisible({ timeout: 30000 });

    const nameInput = page.locator('input[value]').first();
    await nameInput.fill('持久化测试');
    await page.getByRole('button', { name: '创建项目' }).click();
    await expectEditorPage(page);

    // Add a marker
    await page.locator('video').first().focus();
    await page.waitForTimeout(300);
    await page.keyboard.press('m');
    await page.waitForTimeout(500);

    // Go back to project list
    await page.getByRole('button', { name: /返回/ }).click();
    await expectProjectListPage(page);

    // Project should be in list
    await expect(page.getByText('持久化测试')).toBeVisible();

    await takeScreenshot(page, '10-real-video/TC-RV04-project-list');

    // Re-enter the project
    await page.getByText('持久化测试').click();
    await expectEditorPage(page);

    // Marker should still be there
    await page.waitForTimeout(1000);
    await expect(page.locator('.hover\\:bg-accent\\/50').first()).toBeVisible({ timeout: 5000 });

    await takeScreenshot(page, '10-real-video/TC-RV04-reopened-editor');
  });
});
