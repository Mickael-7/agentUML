import { useState, useRef } from "react";
import { FileText, Upload, ShieldCheck, AlertCircle, Lightbulb, Loader2, Download, CheckCircle2, XCircle, ThumbsUp } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Textarea } from "@/components/ui/textarea";
import { analyzeQuality, downloadQualityPdf } from "@/lib/api";
import type { QualityResult, QualityReport, QualityDimension } from "@/lib/types";
import { toast } from "sonner";

const DIMENSION_LABELS: Record<string, string> = {
  clarity: "Clareza",
  completeness: "Completude",
  consistency: "Consistência",
  verifiability: "Verificabilidade",
};

const DIMENSION_ORDER = ["clarity", "completeness", "consistency", "verifiability"] as const;

function DimensionCard({ dimension, data }: { dimension: string; data: QualityDimension }) {
  const label = DIMENSION_LABELS[dimension] ?? dimension;
  const hasIssues = data.issues.length > 0;
  const hasHighlights = (data.highlights ?? []).length > 0;

  return (
    <div className={`rounded-lg border p-3 space-y-2 ${hasIssues ? "border-amber-500/20 bg-amber-500/5" : "border-emerald-500/20 bg-emerald-500/5"}`}>
      <div className="flex items-center gap-2">
        {hasIssues
          ? <XCircle className="h-4 w-4 shrink-0 text-amber-400" />
          : <CheckCircle2 className="h-4 w-4 shrink-0 text-emerald-400" />
        }
        <span className={`text-sm font-semibold ${hasIssues ? "text-amber-300" : "text-emerald-300"}`}>{label}</span>
      </div>

      {hasHighlights && (
        <ul className="space-y-1 pl-1">
          {(data.highlights ?? []).map((h, i) => (
            <li key={i} className="flex items-start gap-1.5 text-xs text-emerald-400/80">
              <ThumbsUp className="mt-0.5 h-3 w-3 shrink-0 text-emerald-500" />
              {h}
            </li>
          ))}
        </ul>
      )}

      {hasIssues && (
        <ul className="space-y-1 pl-1">
          {data.issues.map((issue, i) => (
            <li key={i} className="flex items-start gap-1.5 text-xs text-muted-foreground">
              <AlertCircle className="mt-0.5 h-3 w-3 shrink-0 text-amber-500" />
              {issue}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

export function RequirementsReportView({ report }: { report: QualityReport }) {
  return (
    <>
      {/* Summary */}
      <div className="rounded-lg border border-border bg-muted/30 p-4">
        <p className="mb-1 text-xs font-semibold uppercase tracking-wider text-muted-foreground">Resumo</p>
        <p className="text-sm leading-relaxed text-foreground">{report.summary}</p>
      </div>

      {/* Dimensions */}
      <div>
        <p className="mb-3 text-xs font-semibold uppercase tracking-wider text-muted-foreground">Avaliação por Dimensão</p>
        <div className="grid grid-cols-1 gap-3">
          {DIMENSION_ORDER.map((dim) =>
            report[dim] ? <DimensionCard key={dim} dimension={dim} data={report[dim]} /> : null
          )}
        </div>
      </div>

      {/* Suggestions */}
      {report.suggestions.length > 0 && (
        <div className="rounded-lg border border-blue-500/20 bg-blue-500/5 p-4">
          <p className="mb-2 text-xs font-semibold uppercase tracking-wider text-blue-400">Sugestões de Melhoria</p>
          <ol className="space-y-2">
            {report.suggestions.map((s, i) => (
              <li key={i} className="flex items-start gap-2 text-sm text-muted-foreground">
                <Lightbulb className="mt-0.5 h-3.5 w-3.5 shrink-0 text-blue-400" />
                {s}
              </li>
            ))}
          </ol>
        </div>
      )}
    </>
  );
}

function QualityResults({ result, onDownload, isDownloading }: {
  result: QualityResult;
  onDownload: () => void;
  isDownloading: boolean;
}) {
  const { report } = result;

  return (
    <div className="flex h-full flex-col gap-5 overflow-y-auto p-6">
      {/* Download button */}
      <div className="flex justify-end">
        <Button onClick={onDownload} disabled={isDownloading} variant="outline" size="sm" className="gap-2">
          {isDownloading
            ? <Loader2 className="h-3.5 w-3.5 animate-spin" />
            : <Download className="h-3.5 w-3.5" />
          }
          {isDownloading ? "Gerando PDF..." : "Baixar PDF"}
        </Button>
      </div>

      <RequirementsReportView report={report} />
    </div>
  );
}

function EmptyState() {
  return (
    <div className="flex h-full flex-col items-center justify-center gap-3 text-center">
      <ShieldCheck className="h-14 w-14 text-muted-foreground/30" />
      <p className="text-base font-medium text-muted-foreground">Análise de Qualidade</p>
      <p className="max-w-xs text-sm text-muted-foreground/60">
        Insira o documento de requisitos e clique em Analisar para ver o relatório de qualidade.
      </p>
    </div>
  );
}

export function QualityPanel() {
  const [text, setText] = useState("");
  const [file, setFile] = useState<File | undefined>();
  const [isLoading, setIsLoading] = useState(false);
  const [isDownloading, setIsDownloading] = useState(false);
  const [result, setResult] = useState<QualityResult | null>(null);
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
      const res = await analyzeQuality(text, file);
      setResult(res);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Erro ao analisar requisitos");
    } finally {
      setIsLoading(false);
    }
  };

  const handleDownload = async () => {
    if (!result) return;
    setIsDownloading(true);
    try {
      const blob = await downloadQualityPdf(result);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "quality_report.pdf";
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

          <Button
            onClick={handleAnalyze}
            disabled={isLoading || (!text.trim() && !file)}
            className="w-full gap-2 bg-gradient-to-r from-primary to-primary/80 hover:from-primary/90 hover:to-primary/70"
          >
            {isLoading ? (
              <><Loader2 className="h-4 w-4 animate-spin" />Analisando...</>
            ) : (
              <><ShieldCheck className="h-4 w-4" />Analisar Qualidade</>
            )}
          </Button>
        </div>
      </div>

      {/* Right: results */}
      <div className="flex-1 overflow-hidden">
        {isLoading ? (
          <div className="flex h-full flex-col items-center justify-center gap-3">
            <Loader2 className="h-10 w-10 animate-spin text-primary" />
            <p className="text-sm text-muted-foreground">Analisando documento...</p>
          </div>
        ) : result ? (
          <QualityResults result={result} onDownload={handleDownload} isDownloading={isDownloading} />
        ) : (
          <EmptyState />
        )}
      </div>
    </div>
  );
}
