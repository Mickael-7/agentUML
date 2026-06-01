import { useState } from "react";
import { FileJson } from "lucide-react";
import { DiagramViewer } from "./DiagramViewer";
import type { DiagramInfo } from "@/lib/types";

interface VisualizationPanelProps {
  jobId: string | null;
  diagrams: DiagramInfo[];
}

export function VisualizationPanel({ jobId, diagrams }: VisualizationPanelProps) {
  const [activeTab, setActiveTab] = useState(0);
  const completed = diagrams.filter((d) => d.status === "completed");

  if (!jobId || completed.length === 0) {
    return (
      <div className="flex h-full flex-col items-center justify-center gap-4 text-muted-foreground">
        <FileJson className="h-16 w-16" />
        <div className="text-center">
          <p className="text-lg font-medium">Nenhum diagrama gerado</p>
          <p className="text-sm">Envie os requisitos para gerar diagramas UML</p>
        </div>
      </div>
    );
  }

  const activeDiagram = completed[activeTab] || completed[0];

  return (
    <div className="flex h-full flex-col">
      {completed.length > 1 && (
        <div className="flex border-b border-border overflow-x-auto">
          {completed.map((d, idx) => (
            <button
              key={d.diagram_id}
              onClick={() => setActiveTab(idx)}
              className={`whitespace-nowrap px-4 py-2 text-sm transition-colors border-b-2 ${
                activeTab === idx
                  ? "border-primary text-foreground"
                  : "border-transparent text-muted-foreground hover:text-foreground"
              }`}
            >
              {d.name || d.diagram_id}
            </button>
          ))}
        </div>
      )}
      <div className="flex-1">
        <DiagramViewer
          jobId={jobId}
          diagramId={activeDiagram.diagram_id}
          diagramType={activeDiagram.diagram_type}
          name={activeDiagram.name}
        />
      </div>
    </div>
  );
}
