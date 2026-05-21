import { Page } from '@playwright/test';
import fs from 'fs';
import path from 'path';

const SCREENSHOTS_DIR = path.resolve(process.cwd(), 'e2e', 'screenshots');

let runDir: string | null = null;

function getRunDir(): string {
  if (!runDir) {
    const now = new Date();
    const ts = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}-${String(now.getHours()).padStart(2, '0')}${String(now.getMinutes()).padStart(2, '0')}${String(now.getSeconds()).padStart(2, '0')}`;
    runDir = path.join(SCREENSHOTS_DIR, ts);
    fs.mkdirSync(runDir, { recursive: true });
  }
  return runDir;
}

export async function takeScreenshot(page: Page, name: string): Promise<string> {
  const dir = getRunDir();
  const suiteDir = path.dirname(name);
  const fullDir = path.join(dir, suiteDir);
  fs.mkdirSync(fullDir, { recursive: true });

  const filePath = path.join(dir, `${name}.png`);
  await page.screenshot({ path: filePath, fullPage: true });
  return filePath;
}

export async function takeElementScreenshot(page: Page, selector: string, name: string): Promise<string> {
  const dir = getRunDir();
  const suiteDir = path.dirname(name);
  const fullDir = path.join(dir, suiteDir);
  fs.mkdirSync(fullDir, { recursive: true });

  const filePath = path.join(dir, `${name}.png`);
  const el = page.locator(selector).first();
  await el.screenshot({ path: filePath });
  return filePath;
}

export function getScreenshotDir(): string {
  return getRunDir();
}

export function generateGallery(): string {
  const dir = getRunDir();

  function collectImages(dirPath: string, base: string): { path: string; label: string }[] {
    const entries = fs.readdirSync(dirPath, { withFileTypes: true });
    const images: { path: string; label: string }[] = [];

    for (const entry of entries) {
      const full = path.join(dirPath, entry.name);
      if (entry.isDirectory() && !entry.name.startsWith('_')) {
        images.push(...collectImages(full, path.join(base, entry.name)));
      } else if (entry.isFile() && entry.name.endsWith('.png')) {
        const label = entry.name.replace(/\.png$/, '');
        images.push({ path: path.join(base, entry.name), label });
      }
    }
    return images;
  }

  const images = collectImages(dir, path.basename(dir));

  const html = `<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>E2E Screenshots - ${path.basename(dir)}</title>
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #f5f5f5; padding: 24px; }
    h1 { font-size: 20px; margin-bottom: 8px; }
    .run-info { color: #666; font-size: 13px; margin-bottom: 24px; }
    .suite { margin-bottom: 32px; }
    .suite-title { font-size: 16px; font-weight: 600; margin-bottom: 12px; padding: 8px 12px; background: #e8e8e8; border-radius: 6px; }
    .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(480px, 1fr)); gap: 16px; }
    .card { background: #fff; border-radius: 8px; overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
    .card img { width: 100%; display: block; border-bottom: 1px solid #eee; }
    .card-label { padding: 10px 12px; font-size: 12px; color: #333; font-family: 'SF Mono', monospace; word-break: break-all; }
  </style>
</head>
<body>
  <h1>E2E Screenshot Report</h1>
  <p class="run-info">Run: ${path.basename(dir)} | Images: ${images.length}</p>
  ${images.length === 0 ? '<p>No screenshots captured in this run.</p>' : ''}
  ${groupBySuite(images).map(([suite, imgs]) => `
  <div class="suite">
    <div class="suite-title">${suite}</div>
    <div class="grid">
      ${imgs.map(img => `
      <div class="card">
        <img src="${img.path}" alt="${img.label}" loading="lazy">
        <div class="card-label">${img.label}</div>
      </div>`).join('')}
    </div>
  </div>`).join('')}
</body>
</html>`;

  const indexPath = path.join(dir, '_index.html');
  fs.writeFileSync(indexPath, html, 'utf-8');
  return indexPath;
}

function groupBySuite(images: { path: string; label: string }[]): [string, { path: string; label: string }[]][] {
  const groups = new Map<string, { path: string; label: string }[]>();
  for (const img of images) {
    const parts = img.label.split('/');
    const suite = parts.length > 1 ? parts[0] : '_root';
    const entry = { path: img.path, label: parts.slice(1).join('/') || parts[0] };
    if (!groups.has(suite)) groups.set(suite, []);
    groups.get(suite)!.push(entry);
  }
  return [...groups.entries()];
}
