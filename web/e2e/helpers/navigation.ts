import { Page, expect } from '@playwright/test';

export async function expectProjectListPage(page: Page): Promise<void> {
  // 检查导入视频按钮存在（项目列表页的标志）
  await expect(page.getByRole('button', { name: '导入视频' })).toBeVisible({ timeout: 5000 });
}

export async function expectEditorPage(page: Page): Promise<void> {
  // 检查返回按钮存在（编辑器页的标志）
  await expect(page.getByRole('button', { name: /返回/ })).toBeVisible({ timeout: 5000 });
}

export async function goBackToProjectList(page: Page): Promise<void> {
  await page.getByRole('button', { name: /返回/ }).click();
  await expectProjectListPage(page);
}
