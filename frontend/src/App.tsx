import { useState, useEffect } from "react";
import { Settings, Zap } from "lucide-react";
import { Sidebar } from "@/components/layout/sidebar";
import { InputPanel } from "@/components/input-panel/InputPanel";
import { VisualizationPanel } from "@/components/visualization/VisualizationPanel";
import { ProgressOverlay } from "@/components/progress/ProgressOverlay";
import { SettingsDialog } from "@/components/settings/SettingsDialog";
import { useJob } from "@/hooks/useJob";
import { getHistory } from "@/lib/api";
import { Toaster, toast } from "sonner";
import type { HistoryJob } from "@/lib/types";

const isGenerating = (status: string) =>
  ["queued", "quality_gate", "extracting_rules", "partitioning", "generating"].includes(status);

export default function App() {
  const { jobId, status, statusMessage, diagrams, error, tokenUsage, startGeneration, reset } = useJob();
  const [history, setHistory] = useState<HistoryJob[]>([]);
  const [selectedJobId, setSelectedJobId] = useState<string | null>(null);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [provider, setProvider] = useState<string | undefined>();
  const [model, setModel] = useState<string | undefined>();

  useEffect(() => {
    getHistory().then((r) => setHistory(r.jobs));
  }, [status]);

  useEffect(() => {
    if (error) toast.error(error);
  }, [error]);

  const handleGenerate = async (text: string, file?: File) => {
    toast.success("Geracao iniciada!");
    await startGeneration(text, file, provider, model);
  };

  const handleNewDiagram = () => {
    reset();
    setSelectedJobId(null);
  };

  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar
        onNewDiagram={handleNewDiagram}
        history={history}
        onSelectJob={setSelectedJobId}
        selectedJobId={selectedJobId}
      />

      <div className="flex flex-1 flex-col">
        <header className="flex items-center justify-between border-b border-border px-4 py-2">
          <h1 className="text-sm font-medium text-muted-foreground">
            {status === "idle" ? "Pronto para gerar" : statusMessage}
          </h1>
          <div className="flex items-center gap-3">
            {tokenUsage && (
              <div className="flex items-center gap-1.5 text-xs text-muted-foreground bg-muted/50 rounded-md px-2 py-1">
                <Zap className="h-3 w-3 text-yellow-500" />
                <span>{tokenUsage.total_tokens.toLocaleString()} tokens</span>
                <span className="text-muted-foreground/60">({tokenUsage.call_count} calls)</span>
              </div>
            )}
            <button
              onClick={() => setSettingsOpen(true)}
              className="rounded-md p-2 text-muted-foreground hover:bg-accent hover:text-foreground"
              aria-label="Settings"
            >
              <Settings className="h-4 w-4" />
            </button>
          </div>
        </header>

        <div className="flex flex-1 overflow-hidden relative">
          <div className="w-[400px] border-r border-border overflow-y-auto">
            <InputPanel onGenerate={handleGenerate} isGenerating={isGenerating(status)} />
          </div>

          <div className="flex-1 overflow-hidden">
            <VisualizationPanel jobId={jobId} diagrams={diagrams} />
          </div>

          {isGenerating(status) && (
            <ProgressOverlay status={status} message={statusMessage} diagrams={diagrams} tokenUsage={tokenUsage} />
          )}
        </div>
      </div>

      <SettingsDialog
        open={settingsOpen}
        onOpenChange={setSettingsOpen}
        onProviderChange={setProvider}
        onModelChange={setModel}
      />

      <Toaster theme="dark" position="bottom-right" />
    </div>
  );
}
