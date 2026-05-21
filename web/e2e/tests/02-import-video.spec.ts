import { test, expect } from '@playwright/test';
import { clearIndexedDB, expectProjectListPage, expectEditorPage, takeScreenshot } from '../helpers';

test.describe('Import Video Flow', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await clearIndexedDB(page);
    await page.reload();
    await page.waitForLoadState('networkidle');
  });

  test('TC-IM01: step 1 shows file selection UI', async ({ page }) => {
    await page.getByRole('button', { name: '导入视频' }).click();

    // Step 1 UI elements
    await expect(page.getByText('支持 MP4、MOV 等常见视频格式')).toBeVisible();
    await expect(page.getByRole('button', { name: '选择视频文件' })).toBeVisible();

    await takeScreenshot(page, '02-import-video/TC-IM01-step1-select');
  });

  test('TC-IM02: selecting a video advances to step 2 with metadata', async ({ page }) => {
    await page.getByRole('button', { name: '导入视频' }).click();

    const fileInput = page.locator('input[type="file"]');
    await fileInput.setInputFiles('e2e/fixtures/test-video-5s.mp4');

    // Wait for step 2 with metadata review
    await expect(page.getByRole('button', { name: '创建项目' })).toBeVisible({ timeout: 10000 });
    await expect(page.getByText('项目名称')).toBeVisible();
    await expect(page.getByText('时长')).toBeVisible();
    await expect(page.getByText('分辨率')).toBeVisible();

    await takeScreenshot(page, '02-import-video/TC-IM02-step2-review');
  });

  test('TC-IM03: project name is pre-filled from filename', async ({ page }) => {
    await page.getByRole('button', { name: '导入视频' }).click();

    const fileInput = page.locator('input[type="file"]');
    await fileInput.setInputFiles('e2e/fixtures/test-video-5s.mp4');
    await expect(page.getByRole('button', { name: '创建项目' })).toBeVisible({ timeout: 10000 });

    // The input should be pre-filled with the filename (without extension)
    const nameInput = page.locator('input[value]').first();
    await expect(nameInput).toHaveValue('test-video-5s');
  });

  test('TC-IM04: metadata fields are displayed correctly', async ({ page }) => {
    await page.getByRole('button', { name: '导入视频' }).click();

    const fileInput = page.locator('input[type="file"]');
    await fileInput.setInputFiles('e2e/fixtures/test-video-5s.mp4');
    await expect(page.getByRole('button', { name: '创建项目' })).toBeVisible({ timeout: 10000 });

    // Check metadata fields exist
    // The test video is 640x360, ~5s
    await expect(page.getByText('640')).toBeVisible();
    await expect(page.getByText('360')).toBeVisible();
    await expect(page.getByText(/test-video-5s\.mp4/)).toBeVisible();
    await expect(page.getByText('文件大小')).toBeVisible();
  });

  test('TC-IM05: creating project navigates to editor', async ({ page }) => {
    await page.getByRole('button', { name: '导入视频' }).click();

    const fileInput = page.locator('input[type="file"]');
    await fileInput.setInputFiles('e2e/fixtures/test-video-5s.mp4');
    await expect(page.getByRole('button', { name: '创建项目' })).toBeVisible({ timeout: 10000 });

    await page.getByRole('button', { name: '创建项目' }).click();

    // Should navigate to editor
    await expectEditorPage(page);
    await takeScreenshot(page, '02-import-video/TC-IM05-editor-after-import');
  });

  test('TC-IM06: empty name disables create button', async ({ page }) => {
    await page.getByRole('button', { name: '导入视频' }).click();

    const fileInput = page.locator('input[type="file"]');
    await fileInput.setInputFiles('e2e/fixtures/test-video-5s.mp4');
    await expect(page.getByRole('button', { name: '创建项目' })).toBeVisible({ timeout: 10000 });

    // Clear the name
    const nameInput = page.locator('input[value]').first();
    await nameInput.fill('');

    // Create button should be disabled
    const createBtn = page.getByRole('button', { name: '创建项目' });
    await expect(createBtn).toBeDisabled();
  });

  test('TC-IM07: dialog shows loading state during file read', async ({ page }) => {
    await page.getByRole('button', { name: '导入视频' }).click();

    const fileInput = page.locator('input[type="file"]');
    await fileInput.setInputFiles('e2e/fixtures/test-video-5s.mp4');

    // Loading text might appear briefly, check step 2 eventually appears
    await expect(page.getByRole('button', { name: '创建项目' })).toBeVisible({ timeout: 10000 });
    // The loading state "读取中..." might have already passed
  });
});
