import { Page } from '@playwright/test';

export async function clearIndexedDB(page: Page): Promise<void> {
  await page.evaluate(() => {
    return new Promise<void>((resolve) => {
      const req = indexedDB.deleteDatabase('badmframe');
      req.onsuccess = () => resolve();
      req.onerror = () => resolve();
      req.onblocked = () => {
        // close any open connections and retry
        indexedDB.deleteDatabase('badmframe');
        resolve();
      };
    });
  });
}

export async function getProjectsFromDB(page: Page): Promise<unknown[]> {
  return page.evaluate(() => {
    return new Promise((resolve, reject) => {
      const req = indexedDB.open('badmframe', 1);
      req.onsuccess = () => {
        const db = req.result;
        const tx = db.transaction('projects', 'readonly');
        const store = tx.objectStore('projects');
        const getAll = store.getAll();
        getAll.onsuccess = () => resolve(getAll.result);
        getAll.onerror = () => reject(getAll.error);
      };
      req.onerror = () => reject(req.error);
    });
  });
}

export async function seedProject(page: Page, project: Record<string, unknown>): Promise<void> {
  await page.evaluate((p) => {
    return new Promise<void>((resolve, reject) => {
      const req = indexedDB.open('badmframe', 1);
      req.onsuccess = () => {
        const db = req.result;
        const tx = db.transaction('projects', 'readwrite');
        const store = tx.objectStore('projects');
        store.put(p);
        tx.oncomplete = () => resolve();
        tx.onerror = () => reject(tx.error);
      };
      req.onerror = () => reject(req.error);
      req.onupgradeneeded = () => {
        const db = req.result;
        if (!db.objectStoreNames.contains('projects')) {
          const store = db.createObjectStore('projects', { keyPath: 'id' });
          store.createIndex('updatedAt', 'updatedAt', { unique: false });
        }
      };
    });
  }, project);
}

export async function getProjectCount(page: Page): Promise<number> {
  const projects = await getProjectsFromDB(page);
  return (projects as unknown[]).length;
}
