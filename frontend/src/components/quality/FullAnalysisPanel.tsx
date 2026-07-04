import { useState, useRef } from "react";
import {
  FileText,
  Upload,
  Loader2,
  Download,
  Layers,
  Sparkles,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Textarea } from "@/components/ui/textarea";
import { analyzeAll, downloadAnalysisPdf } from "@/lib/api";
import type { FullAnalysisResult } from "@/lib/types";
import { RequirementsReportView } from "@/components/quality/QualityPanel";
import { ResultsTable } from "@/components/quality/UseCaseEvalPanel";
import { toast } from "sonner";

function StatChip({ label, value, tone = "muted" }: { label: string; value: string; tone?: "muted" | "emerald" | "red" | "blue" }) {
  const toneClass = {
    muted: "border-border text-foreground",
    emerald: "border-emerald-500/30 text-emerald-300 bg-emerald-500/5",
    red: "border-red-500/30 text-red-300 bg-red-500/5",
    blue: "border-blue-500/30 text-blue-300 bg-blue-500/5",
  }[tone];
  return (
    <div className={`rounded-md border px-3 py-1.5 ${toneClass}`}>
      <span className="text-[10px] uppercase tracking-wider text-muted-foreground/70">{label}</span>
      <div className="text-sm font-semibold">{value}</div>
    </div>
  );
}

function EmptyState() {
  return (
    <div className="flex h-full flex-col items-center justify-center gap-3 text-center">
      <Sparkles className="h-14 w-14 text-muted-foreground/30" />
      <p className="text-base font-medium text-muted-foreground">Análise Integrada</p>
      <p className="max-w-sm text-sm text-muted-foreground/60">
        Cole um documento de requisitos. O sistema avalia a qualidade dos requisitos, extrai os casos de uso e avalia cada
        um — tudo num clique.
      </p>
    </div>
  );
}

function FullResults({
  result,
  onDownload,
  isDownloading,
}: {
  result: FullAnalysisResult;
  onDownload: () => void;
  isDownloading: boolean;
}) {
  const { requirements, use_cases, summary } = result;
  const isValid = requirements.is_valid;

  return (
    <div className="flex h-full flex-col gap-5 overflow-y-auto p-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-2">
          <StatChip label="Requisitos" value={isValid ? "Aprovado" : "Reprovado"} tone={isValid ? "emerald" : "red"} />
          <StatChip label="Casos de uso" value={String(summary.use_cases_found)} />
          <StatChip label="Corretos" value={String(summary.correct)} tone="emerald" />
          <StatChip label="Incorretos" value={String(summary.incorrect)} tone="red" />
        </div>
        <Button onClick={onDownload} disabled={isDownloading} variant="outline" size="sm" className="gap-2">
          {isDownloading ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Download className="h-3.5 w-3.5" />}
          {isDownloading ? "Gerando PDF..." : "Baixar PDF"}
        </Button>
      </div>

      <div className="space-y-3">
        <div className="flex items-center gap-2 text-sm font-semibold text-foreground">
          <FileText className="h-4 w-4 text-primary" />
          Qualidade dos Requisitos
        </div>
        <RequirementsReportView report={requirements.report} />
      </div>

      <div className="space-y-3">
        <div className="flex items-center gap-2 text-sm font-semibold text-foreground">
          <Layers className="h-4 w-4 text-primary" />
          Casos de Uso Extraídos
        </div>
        {use_cases.length > 0 ? (
          <ResultsTable docs={use_cases} />
        ) : (
          <p className="rounded-lg border border-border bg-muted/20 p-4 text-sm text-muted-foreground">
            Nenhum caso de uso identificado no documento.
          </p>
        )}
      </div>
    </div>
  );
}

export function FullAnalysisPanel() {
  const [text, setText] = useState("");
  const [file, setFile] = useState<File | undefined>();
  const [isLoading, setIsLoading] = useState(false);
  const [isDownloading, setIsDownloading] = useState(false);
  const [result, setResult] = useState<FullAnalysisResult | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    const dropped = e.dataTransfer.files[0];
    if (dropped) setFile(dropped);
  };
  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selected = e.target.files?.[0];
    if (selected) setFile(selected);
  };

  const handleAnalyze = async () => {
    if (!text.trim() && !file) return;
    setIsLoading(true);
    setResult(null);
    try {
      const res = await analyzeAll(text, file);
      setResult(res);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Erro ao analisar o documento");
    } finally {
      setIsLoading(false);
    }
  };

  const handleDownload = async () => {
    if (!result) return;
    setIsDownloading(true);
    try {
      const blob = await downloadAnalysisPdf(result);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "analysis_report.pdf";
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Erro ao gerar PDF");
    } finally {
      setIsDownloading(false);
    }
  };

  return (
    <div className="flex h-full overflow-hidden">
      {/* Left: input */}
      <div className="w-[400px] shrink-0 border-r border-border overflow-y-auto">
        <div className="flex h-full flex-col gap-4 p-4">
          <h2 className="text-lg font-semibold text-foreground">Documento de Requisitos</h2>
          <p className="-mt-2 text-xs text-muted-foreground/70">
            Análise integrada em um clique: qualidade dos requisitos + extração e avaliação dos casos de uso.
          </p>

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
                placeholder="Cole aqui o documento de requisitos do sistema..."
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

          <Button
            onClick={handleAnalyze}
            disabled={isLoading || (!text.trim() && !file)}
            className="w-full gap-2 bg-gradient-to-r from-primary to-primary/80 hover:from-primary/90 hover:to-primary/70"
          >
            {isLoading ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" /> Analisando...
              </>
            ) : (
              <>
                <Sparkles className="h-4 w-4" /> Analisar Tudo
              </>
            )}
          </Button>
        </div>
      </div>

      {/* Right: results */}
      <div className="flex-1 overflow-hidden">
        {isLoading ? (
          <div className="flex h-full flex-col items-center justify-center gap-3">
            <Loader2 className="h-10 w-10 animate-spin text-primary" />
            <p className="text-sm text-muted-foreground">Analisando requisitos e casos de uso...</p>
          </div>
        ) : result ? (
          <FullResults result={result} onDownload={handleDownload} isDownloading={isDownloading} />
        ) : (
          <EmptyState />
        )}
      </div>
    </div>
  );
}
