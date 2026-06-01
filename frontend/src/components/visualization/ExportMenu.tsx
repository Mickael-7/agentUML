import { Download, Copy, Image, FileCode } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Tooltip, TooltipContent, TooltipTrigger, TooltipProvider } from "@/components/ui/tooltip";

interface ExportMenuProps {
  jobId: string;
  diagramId: string;
  pumlText: string;
}

export function ExportMenu({ jobId, diagramId, pumlText }: ExportMenuProps) {
  const handleDownload = (format: string) => {
    const url = `/api/diagrams/${jobId}/${diagramId}/image?format=${format}`;
    const a = document.createElement("a");
    a.href = url;
    a.download = `${diagramId}.${format}`;
    a.click();
  };

  const handleCopyCode = async () => {
    await navigator.clipboard.writeText(pumlText);
  };

  return (
    <TooltipProvider>
      <div className="flex items-center gap-1">
        <Tooltip>
          <TooltipTrigger asChild>
            <Button variant="ghost" size="icon" onClick={() => handleDownload("png")}>
              <Image className="h-4 w-4" />
            </Button>
          </TooltipTrigger>
          <TooltipContent>Exportar PNG</TooltipContent>
        </Tooltip>
        <Tooltip>
          <TooltipTrigger asChild>
            <Button variant="ghost" size="icon" onClick={() => handleDownload("svg")}>
              <Download className="h-4 w-4" />
            </Button>
          </TooltipTrigger>
          <TooltipContent>Exportar SVG</TooltipContent>
        </Tooltip>
        <Tooltip>
          <TooltipTrigger asChild>
            <Button variant="ghost" size="icon" onClick={handleCopyCode}>
              <Copy className="h-4 w-4" />
            </Button>
          </TooltipTrigger>
          <TooltipContent>Copiar PUML</TooltipContent>
        </Tooltip>
        <Tooltip>
          <TooltipTrigger asChild>
            <Button variant="ghost" size="icon" onClick={() => {
              const blob = new Blob([pumlText], { type: "text/plain" });
              const a = document.createElement("a");
              a.href = URL.createObjectURL(blob);
              a.download = `${diagramId}.puml`;
              a.click();
            }}>
              <FileCode className="h-4 w-4" />
            </Button>
          </TooltipTrigger>
          <TooltipContent>Baixar .puml</TooltipContent>
        </Tooltip>
      </div>
    </TooltipProvider>
  );
}
