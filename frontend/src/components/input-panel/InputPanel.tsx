import { useState, useRef } from "react";
import { Sparkles, Upload, FileText } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Textarea } from "@/components/ui/textarea";

interface InputPanelProps {
  onGenerate: (text: string, file?: File) => void;
  isGenerating: boolean;
}

export function InputPanel({ onGenerate, isGenerating }: InputPanelProps) {
  const [text, setText] = useState("");
  const [file, setFile] = useState<File | undefined>();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleGenerate = () => {
    if (text.trim() || file) {
      onGenerate(text, file);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    const droppedFile = e.dataTransfer.files[0];
    if (droppedFile) setFile(droppedFile);
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selected = e.target.files?.[0];
    if (selected) setFile(selected);
  };

  return (
    <div className="flex h-full flex-col gap-4 p-4">
      <h2 className="text-lg font-semibold text-foreground">Requisitos</h2>

      <Tabs defaultValue="text" className="flex-1 flex flex-col">
        <TabsList className="w-full">
          <TabsTrigger value="text" className="flex-1 gap-1">
            <FileText className="h-3 w-3" />
            Texto
          </TabsTrigger>
          <TabsTrigger value="file" className="flex-1 gap-1">
            <Upload className="h-3 w-3" />
            Arquivo
          </TabsTrigger>
        </TabsList>

        <TabsContent value="text" className="flex-1 mt-2">
          <Textarea
            placeholder="Cole aqui os requisitos do sistema..."
            className="h-full min-h-[300px] resize-none"
            value={text}
            onChange={(e) => setText(e.target.value)}
          />
        </TabsContent>

        <TabsContent value="file" className="flex-1 mt-2">
          <div
            onDrop={handleDrop}
            onDragOver={(e) => e.preventDefault()}
            onClick={() => fileInputRef.current?.click()}
            className="flex h-full min-h-[300px] cursor-pointer flex-col items-center justify-center rounded-lg border-2 border-dashed border-muted-foreground/25 bg-muted/50 transition-colors hover:border-primary/50 hover:bg-muted"
          >
            {file ? (
              <div className="text-center">
                <FileText className="mx-auto h-10 w-10 text-primary" />
                <p className="mt-2 text-sm font-medium text-foreground">{file.name}</p>
                <p className="text-xs text-muted-foreground">{(file.size / 1024).toFixed(1)} KB</p>
              </div>
            ) : (
              <div className="text-center">
                <Upload className="mx-auto h-10 w-10 text-muted-foreground" />
                <p className="mt-2 text-sm text-muted-foreground">Arraste um arquivo ou clique para selecionar</p>
                <p className="text-xs text-muted-foreground">.txt, .md, .pdf, .docx</p>
              </div>
            )}
            <input ref={fileInputRef} type="file" className="hidden" accept=".txt,.md,.pdf,.docx" onChange={handleFileChange} />
          </div>
        </TabsContent>
      </Tabs>

      <Button onClick={handleGenerate} disabled={isGenerating || (!text.trim() && !file)} className="w-full gap-2 bg-gradient-to-r from-primary to-primary/80 hover:from-primary/90 hover:to-primary/70">
        <Sparkles className="h-4 w-4" />
        {isGenerating ? "Gerando..." : "Gerar Diagrama UML"}
      </Button>
    </div>
  );
}
