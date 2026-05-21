import type { Project, SourceVideo, Marker, Clip } from "@/types";

const DB_NAME = "badmframe";
const DB_VERSION = 1;

function openDB(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const req = indexedDB.open(DB_NAME, DB_VERSION);
    req.onupgradeneeded = () => {
      const db = req.result;
      if (!db.objectStoreNames.contains("projects")) {
        const store = db.createObjectStore("projects", { keyPath: "id" });
        store.createIndex("updatedAt", "updatedAt", { unique: false });
      }
    };
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
}

async function tx<T>(storeName: IDBTransactionMode, fn: (store: IDBObjectStore) => IDBRequest<T>): Promise<T> {
  const db = await openDB();
  return new Promise((resolve, reject) => {
    const t = db.transaction("projects", storeName);
    const store = t.objectStore("projects");
    const req = fn(store);
    req.onsuccess = () => resolve(req.result as T);
    req.onerror = () => reject(req.error);
  });
}

async function txVoid(storeName: IDBTransactionMode, fn: (store: IDBObjectStore) => IDBRequest): Promise<void> {
  await tx<unknown>(storeName, fn);
}

export const db = {
  async getAllProjects(): Promise<Project[]> {
    const db = await openDB();
    return new Promise((resolve, reject) => {
      const t = db.transaction("projects", "readonly");
      const store = t.objectStore("projects");
      const idx = store.index("updatedAt");
      const req = idx.getAll();
      req.onsuccess = () => {
        const projects = req.result || [];
        projects.sort((a, b) => new Date(b.updatedAt).getTime() - new Date(a.updatedAt).getTime());
        resolve(projects);
      };
      req.onerror = () => reject(req.error);
    });
  },

  async getProject(id: string): Promise<Project | undefined> {
    return tx("readonly", (s) => s.get(id));
  },

  async saveProject(project: Project): Promise<void> {
    return txVoid("readwrite", (s) => s.put(project));
  },

  async deleteProject(id: string): Promise<void> {
    return txVoid("readwrite", (s) => s.delete(id));
  },
};
