import { useEffect, useRef } from "react";
import mermaid from "mermaid";

mermaid.initialize({ startOnLoad: false, theme: "dark" });

interface MermaidRendererProps {
  chart: string;
}

export function MermaidRenderer({ chart }: MermaidRendererProps) {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (containerRef.current && chart) {
      const id = `mermaid-${Date.now()}`;
      mermaid.render(id, chart).then(({ svg }) => {
        if (containerRef.current) {
          containerRef.current.innerHTML = svg;
        }
      }).catch(() => {
        if (containerRef.current) {
          containerRef.current.innerHTML = "<p class='text-muted-foreground text-sm'>Failed to render Mermaid diagram</p>";
        }
      });
    }
  }, [chart]);

  return <div ref={containerRef} className="overflow-auto p-4" />;
}
