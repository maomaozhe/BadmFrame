import { Page } from '@playwright/test';
import path from 'path';

const FIXTURES_DIR = path.resolve(process.cwd(), 'e2e', 'fixtures');

export async function importVideoAndCreateProject(
  page: Page,
  videoFileName: string = 'test-video-5s.mp4',
  projectName?: string,
): Promise<void> {
  // 打开导入对话框
  await page.getByRole('button', { name: '导入视频' }).click();

  // 等待对话框出现
  await page.waitForSelector('text=支持 MP4、MOV 等常见视频格式', { timeout: 3000 });

  // 步骤1: 选择视频文件
  const fileInput = page.locator('input[type="file"]');
  const videoPath = path.join(FIXTURES_DIR, videoFileName);
  await fileInput.setInputFiles(videoPath);

  // 等待进入步骤2（review），有"创建项目"按钮出现
  await page.waitForSelector('button:has-text("创建项目")', { timeout: 10000 });

  // 步骤2: 如果需要，修改项目名称
  if (projectName) {
    const nameInput = page.locator('input[value]').first();
    await nameInput.fill(projectName);
  }

  // 点击创建项目
  await page.getByRole('button', { name: /创建项目/ }).click();

  // 等待进入编辑器
  await page.waitForSelector('video', { timeout: 5000 });
}

export async function openImportDialog(page: Page): Promise<void> {
  await page.getByRole('button', { name: '导入视频' }).click();
  await page.waitForSelector('text=支持 MP4、MOV 等常见视频格式', { timeout: 3000 });
}

export async function closeImportDialog(page: Page): Promise<void> {
  // In step 1 there's no cancel button, close via Escape
  await page.keyboard.press('Escape');
  await page.waitForSelector('text=支持 MP4、MOV 等常见视频格式', { state: 'detached', timeout: 3000 }).catch(() => {});
}
