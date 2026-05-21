import { useEffect, useState } from "react";
import { useProjectStore } from "@/store/projectSlice";
import { useUIStore } from "@/store/uiSlice";
import { useVideoStore } from "@/store/videoSlice";
import { ProjectListView } from "@/components/ProjectList/ProjectListView";
import { ImportDialog } from "@/components/ProjectList/ImportDialog";
import { EditorView } from "@/components/Editor/EditorView";

export default function App() {
  const { loading, loadProjects, currentProjectId } = useProjectStore();
  const { showImport, setShowImport, errorMessage, setErrorMessage } = useUIStore();
  const reset = useVideoStore((s) => s.reset);
  const [importedProjectId, setImportedProjectId] = useState<string | null>(null);

  useEffect(() => {
    loadProjects();
  }, []);

  const handleBack = () => {
    useProjectStore.getState().setCurrentProject(null);
    reset();
  };

  return (
    <div className="h-dvh flex flex-col">
      {errorMessage && (
        <div className="bg-destructive/10 text-destructive text-sm px-4 py-2 flex justify-between items-center">
          <span>{errorMessage}</span>
          <button onClick={() => setErrorMessage(null)} className="font-bold ml-4">&times;</button>
        </div>
      )}

      {currentProjectId ? (
        <EditorView onBack={handleBack} />
      ) : (
        <>
          <header className="border-b px-4 py-3 flex items-center justify-between">
            <h1 className="text-xl font-bold">BadmFrame</h1>
            <button
              onClick={() => setShowImport(true)}
              className="inline-flex items-center gap-1.5 rounded-md bg-primary text-primary-foreground text-sm font-medium h-9 px-4 hover:bg-primary/90"
            >
              导入视频
            </button>
          </header>

          {loading ? (
            <div className="flex-1 flex items-center justify-center">
              <p className="text-muted-foreground">加载中...</p>
            </div>
          ) : (
            <ProjectListView onProjectCreated={(id) => setImportedProjectId(id)} />
          )}

          <ImportDialog
            open={showImport}
            onClose={() => setShowImport(false)}
          />
        </>
      )}
    </div>
  );
}
