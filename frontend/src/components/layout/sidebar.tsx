import { GitGraph, Plus, Clock } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import type { HistoryJob } from "@/lib/types";

interface SidebarProps {
  onNewDiagram: () => void;
  history: HistoryJob[];
  onSelectJob: (jobId: string) => void;
  selectedJobId?: string | null;
}

export function Sidebar({ onNewDiagram, history, onSelectJob, selectedJobId }: SidebarProps) {
  return (
    <div className="flex h-screen w-64 flex-col border-r border-border bg-card">
      <div className="flex items-center gap-2 px-4 py-4">
        <GitGraph className="h-6 w-6 text-primary" />
        <span className="text-lg font-bold text-foreground">UML-AI</span>
      </div>

      <div className="px-3 pb-3">
        <Button onClick={onNewDiagram} className="w-full gap-2" size="sm">
          <Plus className="h-4 w-4" />
          Novo Diagrama
        </Button>
      </div>

      <Separator />

      <div className="flex items-center gap-2 px-4 py-2 text-xs font-medium text-muted-foreground uppercase tracking-wider">
        <Clock className="h-3 w-3" />
        Historico
      </div>

      <div className="flex-1 overflow-y-auto px-2">
        {history.length === 0 && (
          <p className="px-2 py-4 text-xs text-muted-foreground text-center">Nenhum diagrama gerado ainda.</p>
        )}
        {history.map((job) => (
          <button
            key={job.job_id}
            onClick={() => onSelectJob(job.job_id)}
            className={`w-full rounded-md px-3 py-2 text-left text-sm transition-colors hover:bg-accent ${
              selectedJobId === job.job_id ? "bg-accent" : ""
            }`}
          >
            <div className="font-medium text-foreground truncate">
              {job.diagrams.length > 0 ? job.diagrams[0].name : job.job_id}
            </div>
            <div className="text-xs text-muted-foreground">
              {job.diagrams.length} diagrama{job.diagrams.length !== 1 ? "s" : ""} - {new Date(job.created_at).toLocaleDateString()}
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}
