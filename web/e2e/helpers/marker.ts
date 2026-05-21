import { Page } from '@playwright/test';

export async function addMarkerViaKeyboard(page: Page, times: number = 1): Promise<void> {
  // 确保焦点不在 input/textarea 内
  await page.locator('video').first().focus();
  for (let i = 0; i < times; i++) {
    await page.keyboard.press('m');
    await page.waitForTimeout(200);
  }
}

export async function addMarkerViaButton(page: Page): Promise<void> {
  await page.getByRole('button', { name: /标记/ }).first().click();
  await page.waitForTimeout(200);
}

export async function getMarkerCount(page: Page): Promise<number> {
  // 标记面板中每个标记行都有颜色圆点，统计它们
  const dots = page.locator('.rounded-full, [class*="rounded-full"]').filter({ hasText: '' });
  // 更加精确：统计 MarkerPanel 中的标记（包含 timestamp 显示的元素）
  const markerElements = page.locator('[class*="font-mono"]').filter({ hasText: /^\d/ });
  return markerElements.count();
}

export async function seekToMarker(page: Page, index: number): Promise<void> {
  // 点击第 index 个标记的颜色圆点
  const markerRows = page.locator('.group').filter({ has: page.locator('[class*="font-mono"]') });
  await markerRows.nth(index).locator('.rounded-full, [class*="rounded-full"]').first().click();
}

export async function deleteMarker(page: Page, index: number): Promise<void> {
  const markerRows = page.locator('.group').filter({ has: page.locator('[class*="font-mono"]') });
  await markerRows.nth(index).hover();
  await markerRows.nth(index).getByRole('button').filter({ hasText: '' }).last().click();
}
