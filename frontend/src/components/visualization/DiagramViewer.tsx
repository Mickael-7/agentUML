import { useState, useEffect } from "react";
import { ZoomIn, ZoomOut, RotateCcw, Code, Eye } from "lucide-react";
import { Button } from "@/components/ui/button";
import { MermaidRenderer } from "./MermaidRenderer";
import { ExportMenu } from "./ExportMenu";
import { getDiagramPuml, getDiagramImageUrl, getDiagramMermaid } from "@/lib/api";

interface DiagramViewerProps {
  jobId: string;
  diagramId: string;
  diagramType: string;
  name: string;
}

export function DiagramViewer({ jobId, diagramId, diagramType, name }: DiagramViewerProps) {
  const [zoom, setZoom] = useState(100);
  const [viewMode, setViewMode] = useState<"rendered" | "mermaid" | "code">("rendered");
  const [pumlText, setPumlText] = useState("");
  const [mermaidText, setMermaidText] = useState("");
  const [imageUrl, setImageUrl] = useState("");

  useEffect(() => {
    getDiagramPuml(jobId, diagramId).then(setPumlText);
    getDiagramImageUrl(jobId, diagramId).then(setImageUrl);
    getDiagramMermaid(jobId, diagramId, diagramType).then((r) => setMermaidText(r.mermaid_text));
  }, [jobId, diagramId, diagramType]);

  return (
    <div className="flex h-full flex-col">
      <div className="flex items-center justify-between border-b border-border px-4 py-2">
        <div className="flex items-center gap-2">
          <h3 className="text-sm font-medium text-foreground">{name}</h3>
          <span className="rounded bg-muted px-2 py-0.5 text-xs text-muted-foreground">{diagramType}</span>
        </div>
        <div className="flex items-center gap-1">
          <Button variant="ghost" size="icon" onClick={() => setViewMode("rendered")} className={viewMode === "rendered" ? "bg-accent" : ""}>
            <Eye className="h-4 w-4" />
          </Button>
          <Button variant="ghost" size="icon" onClick={() => setViewMode("mermaid")} className={viewMode === "mermaid" ? "bg-accent" : ""}>
            <RotateCcw className="h-4 w-4" />
          </Button>
          <Button variant="ghost" size="icon" onClick={() => setViewMode("code")} className={viewMode === "code" ? "bg-accent" : ""}>
            <Code className="h-4 w-4" />
          </Button>
          <div className="mx-1 h-4 w-px bg-border" />
          <Button variant="ghost" size="icon" onClick={() => setZoom((z) => Math.min(z + 20, 200))}>
            <ZoomIn className="h-4 w-4" />
          </Button>
          <Button variant="ghost" size="icon" onClick={() => setZoom((z) => Math.max(z - 20, 40))}>
            <ZoomOut className="h-4 w-4" />
          </Button>
          <Button variant="ghost" size="icon" onClick={() => setZoom(100)}>
            <RotateCcw className="h-4 w-4" />
          </Button>
          <div className="mx-1 h-4 w-px bg-border" />
          {pumlText && <ExportMenu jobId={jobId} diagramId={diagramId} pumlText={pumlText} />}
        </div>
      </div>

      <div className="flex-1 overflow-auto bg-[radial-gradient(circle,_var(--border)_1px,_transparent_1px)] bg-[size:20px_20px] p-4">
        <div className="mx-auto" style={{ transform: `scale(${zoom / 100})`, transformOrigin: "center top" }}>
          {viewMode === "rendered" && imageUrl && (
            <img src={imageUrl} alt={name} className="max-w-full" />
          )}
          {viewMode === "rendered" && !imageUrl && (
            <div className="flex h-64 items-center justify-center text-muted-foreground text-sm">
              Loading diagram...
            </div>
          )}
          {viewMode === "mermaid" && mermaidText && (
            <MermaidRenderer chart={mermaidText} />
          )}
          {viewMode === "mermaid" && !mermaidText && (
            <div className="flex h-64 items-center justify-center text-muted-foreground text-sm">
              Mermaid conversion not available
            </div>
          )}
          {viewMode === "code" && pumlText && (
            <pre className="rounded-lg border border-border bg-card p-4 text-sm text-foreground overflow-auto">
              <code>{pumlText}</code>
            </pre>
          )}
        </div>
      </div>
    </div>
  );
}
