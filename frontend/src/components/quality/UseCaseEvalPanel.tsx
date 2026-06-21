import { useState, useRef } from "react";
import {
  FileCheck,
  Plus,
  Trash2,
  Loader2,
  Download,
  CheckCircle2,
  XCircle,
  Minus,
  ChevronRight,
  ChevronDown,
  Upload,
  ListChecks,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { evaluateUseCaseDocuments, downloadUseCaseEvalPdf } from "@/lib/api";
import type { UseCaseDocInput, UseCaseDocResult, UseCaseEvalResult, Verdict } from "@/lib/types";
import { toast } from "sonner";

// ── Sample documents (a small "test set": 1 correct, 1 incorrect) ──────────────
const SAMPLE_DOCS: UseCaseDocInput[] = [
  {
    name: "Login (correto)",
    expected_verdict: "correct",
    text: `# Caso de Uso: Realizar Login

Ator principal: Usuario cadastrado
Objetivo: Autenticar-se no sistema para acessar funcionalidades restritas.

Requisito: O usuario deve poder realizar login informando email e senha validos. O sistema valida as credredenciais e, em caso de sucesso, concede acesso; em caso de falha, exibe uma mensagem de erro.

Fluxo principal:
1. O usuario acessa a tela de login.
2. Informa email e senha.
3. O sistema valida as credenciais.
4. O sistema concede acesso ao painel.

@startuml
left to right direction
actor "Usuario" as Usuario
rectangle "Sistema de Autenticacao" {
  usecase "Realizar Login" as UC1
  usecase "Recuperar Senha" as UC2
}
Usuario --> UC1
Usuario --> UC2
UC1 ..> UC2 : <<extend>>
@enduml`,
  },
  {
    name: "Catalogo (incorreto)",
    expected_verdict: "incorrect",
    text: `# Catalogo

catalogo de produtos

@startuml
actor "Cliente
usecase Buscar Produto
Cliente -> Buscar`,
  },
];

const NEW_DOC: UseCaseDocInput = { name: "", text: "", expected_verdict: null };

// ── Small presentational helpers ───────────────────────────────────────────────
function CheckCell({ value }: { value: boolean | null }) {
  if (value === null) {
    return (
      <span className="inline-flex items-center gap-1 text-xs text-muted-foreground/60">
        <Minus className="h-3 w-3" /> n/a
      </span>
    );
  }
  return value ? (
    <span className="inline-flex items-center gap-1 text-xs text-emerald-400">
      <CheckCircle2 className="h-3.5 w-3.5" />
    </span>
  ) : (
    <span className="inline-flex items-center gap-1 text-xs text-amber-400">
      <XCircle className="h-3.5 w-3.5" />
    </span>
  );
}

function VerdictBadge({ verdict }: { verdict: Verdict }) {
  const isCorrect = verdict === "correct";
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-md px-2 py-0.5 text-xs font-semibold ${
        isCorrect
          ? "bg-emerald-500/15 text-emerald-300"
          : "bg-red-500/15 text-red-300"
      }`}
    >
      {isCorrect ? <CheckCircle2 className="h-3 w-3" /> : <XCircle className="h-3 w-3" />}
      {isCorrect ? "Correto" : "Incorreto"}
    </span>
  );
}

// ── Input: one editable document entry ─────────────────────────────────────────
function DocumentEntry({
  index,
  doc,
  onChange,
  onRemove,
}: {
  index: number;
  doc: UseCaseDocInput;
  onChange: (next: UseCaseDocInput) => void;
  onRemove: () => void;
}) {
  const fileRef = useRef<HTMLInputElement>(null);

  const handleFile = (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0];
    if (!f) return;
    const reader = new FileReader();
    reader.onload = () => onChange({ ...doc, name: doc.name || f.name, text: String(reader.result || "") });
    reader.readAsText(f);
    e.target.value = "";
  };

  return (
    <div className="rounded-lg border border-border bg-muted/20 p-3 space-y-2">
      <div className="flex items-center gap-2">
        <span className="text-xs font-mono text-muted-foreground/70 w-5 shrink-0">{index + 1}.</span>
        <input
          value={doc.name}
          onChange={(e) => onChange({ ...doc, name: e.target.value })}
          placeholder="Nome do documento"
          className="h-7 flex-1 rounded-md border border-border bg-background px-2 text-sm text-foreground placeholder:text-muted-foreground/50 focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
        />
        <select
          value={doc.expected_verdict ?? ""}
          onChange={(e) =>
            onChange({
              ...doc,
              expected_verdict: (e.target.value || null) as Verdict | null,
            })
          }
          className="h-7 rounded-md border border-border bg-background px-1.5 text-xs text-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
          title="Veredito esperado (ground truth)"
        >
          <option value="">— esperado —</option>
          <option value="correct">Correto</option>
          <option value="incorrect">Incorreto</option>
        </select>
        <button
          onClick={onRemove}
          className="rounded-md p-1 text-muted-foreground hover:bg-destructive/10 hover:text-red-400"
          title="Remover"
        >
          <Trash2 className="h-3.5 w-3.5" />
        </button>
      </div>

      <Textarea
        value={doc.text}
        onChange={(e) => onChange({ ...doc, text: e.target.value })}
        placeholder="Cole aqui o documento de caso de uso (contexto + diagrama PlantUML opcional)..."
        className="min-h-[140px] resize-y font-mono text-xs"
      />

      <div className="flex items-center justify-between">
        <button
          onClick={() => fileRef.current?.click()}
          className="inline-flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground"
        >
          <Upload className="h-3 w-3" /> importar .txt/.md
        </button>
        <span className="text-[10px] text-muted-foreground/50">{doc.text.length} chars</span>
        <input ref={fileRef} type="file" className="hidden" accept=".txt,.md,.puml" onChange={handleFile} />
      </div>
    </div>
  );
}

// ── Results table ──────────────────────────────────────────────────────────────
function ResultsTable({ docs }: { docs: UseCaseDocResult[] }) {
  const [expanded, setExpanded] = useState<number | null>(null);
  const toggle = (i: number) => setExpanded((cur) => (cur === i ? null : i));

  return (
    <div className="overflow-hidden rounded-lg border border-border">
      <table className="w-full border-collapse text-sm">
        <thead>
          <tr className="border-b border-border bg-muted/40 text-left text-xs text-muted-foreground">
            <th className="w-6 px-2 py-2"></th>
            <th className="w-8 px-2 py-2">#</th>
            <th className="px-2 py-2">Documento</th>
            <th className="px-2 py-2 text-center" title="Possui requisito">Req.</th>
            <th className="px-2 py-2 text-center" title="Possui contexto de caso de uso">Contexto</th>
            <th className="px-2 py-2 text-center" title="Simbologia do diagrama correta">Simb.</th>
            <th className="px-2 py-2">Veredito</th>
            <th className="px-2 py-2">Esperado</th>
          </tr>
        </thead>
        <tbody>
          {docs.map((d, i) => {
            const isOpen = expanded === i;
            return (
              <>
                <tr
                  key={`row-${i}`}
                  onClick={() => toggle(i)}
                  className={`cursor-pointer border-b border-border/60 transition-colors hover:bg-muted/30 ${
                    isOpen ? "bg-muted/30" : ""
                  }`}
                >
                  <td className="px-2 py-2 text-muted-foreground">
                    {isOpen ? <ChevronDown className="h-3.5 w-3.5" /> : <ChevronRight className="h-3.5 w-3.5" />}
                  </td>
                  <td className="px-2 py-2 font-mono text-xs text-muted-foreground">{i + 1}</td>
                  <td className="px-2 py-2 font-medium text-foreground">{d.name || `Documento ${i + 1}`}</td>
                  <td className="px-2 py-2 text-center"><CheckCell value={d.checks.has_requirement} /></td>
                  <td className="px-2 py-2 text-center"><CheckCell value={d.checks.has_use_case_context} /></td>
                  <td className="px-2 py-2 text-center"><CheckCell value={d.checks.symbology_correct} /></td>
                  <td className="px-2 py-2"><VerdictBadge verdict={d.verdict} /></td>
                  <td className="px-2 py-2 text-xs">
                    {d.expected_verdict ? (
                      <span
                        className={`inline-flex items-center gap-1 rounded px-1.5 py-0.5 font-medium ${
                          d.matches_expected
                            ? "bg-emerald-500/15 text-emerald-300"
                            : "bg-red-500/15 text-red-300"
                        }`}
                      >
                        {d.matches_expected ? "acerto" : "erro"}
                      </span>
                    ) : (
                      <span className="text-muted-foreground/40">—</span>
                    )}
                  </td>
                </tr>
                {isOpen && (
                  <tr key={`detail-${i}`}>
                    <td colSpan={8} className="bg-muted/20 px-4 py-3">
                      <div className="space-y-3">
                        <div>
                          <p className="mb-1 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                            Justificativa
                          </p>
                          <p className="text-sm leading-relaxed text-foreground">{d.justification || "—"}</p>
                        </div>
                        {d.errors.length > 0 && (
                          <div>
                            <p className="mb-1 text-xs font-semibold uppercase tracking-wider text-amber-400">
                              Erros
                            </p>
                            <ul className="space-y-1">
                              {d.errors.map((err, ei) => (
                                <li key={ei} className="flex items-start gap-1.5 text-xs text-muted-foreground">
                                  <XCircle className="mt-0.5 h-3 w-3 shrink-0 text-amber-500" />
                                  {err}
                                </li>
                              ))}
                            </ul>
                          </div>
                        )}
                        {d.correction && (
                          <div className="rounded-md border border-blue-500/20 bg-blue-500/5 p-2">
                            <p className="mb-1 text-xs font-semibold uppercase tracking-wider text-blue-400">
                              Correção sugerida
                            </p>
                            <p className="text-sm leading-relaxed text-foreground">{d.correction}</p>
                          </div>
                        )}
                      </div>
                    </td>
                  </tr>
                )}
              </>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

function EmptyState() {
  return (
    <div className="flex h-full flex-col items-center justify-center gap-3 text-center">
      <FileCheck className="h-14 w-14 text-muted-foreground/30" />
      <p className="text-base font-medium text-muted-foreground">Avaliação de Casos de Uso</p>
      <p className="max-w-sm text-sm text-muted-foreground/60">
        Adicione documentos de caso de uso (contexto + diagrama) e clique em Avaliar. O LLM classifica cada um como
        correto ou incorreto e sugere correções.
      </p>
    </div>
  );
}

export function UseCaseEvalPanel() {
  const [docs, setDocs] = useState<UseCaseDocInput[]>([{ ...NEW_DOC }]);
  const [maxDocuments, setMaxDocuments] = useState<string>("");
  const [isLoading, setIsLoading] = useState(false);
  const [isDownloading, setIsDownloading] = useState(false);
  const [result, setResult] = useState<UseCaseEvalResult | null>(null);

  const updateDoc = (i: number, next: UseCaseDocInput) =>
    setDocs((cur) => cur.map((d, idx) => (idx === i ? next : d)));
  const removeDoc = (i: number) => setDocs((cur) => cur.filter((_, idx) => idx !== i));
  const addDoc = () => setDocs((cur) => [...cur, { ...NEW_DOC }]);
  const loadSamples = () => {
    setDocs(SAMPLE_DOCS.map((d) => ({ ...d })));
    setResult(null);
  };

  const validCount = docs.filter((d) => d.text.trim()).length;

  const handleEvaluate = async () => {
    const toSend = docs.filter((d) => d.text.trim());
    if (!toSend.length) return;
    setIsLoading(true);
    setResult(null);
    try {
      const max = maxDocuments.trim() ? parseInt(maxDocuments, 10) : undefined;
      const res = await evaluateUseCaseDocuments(
        toSend,
        Number.isFinite(max) && (max as number) > 0 ? (max as number) : undefined,
      );
      setResult(res);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Erro ao avaliar documentos");
    } finally {
      setIsLoading(false);
    }
  };

  const handleDownload = async () => {
    if (!result) return;
    setIsDownloading(true);
    try {
      const blob = await downloadUseCaseEvalPdf(result);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "use_case_evaluation.pdf";
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Erro ao gerar PDF");
    } finally {
      setIsDownloading(false);
    }
  };

  const { summary } = result ?? { summary: null };

  return (
    <div className="flex h-full overflow-hidden">
      {/* Left: input */}
      <div className="w-[440px] shrink-0 border-r border-border overflow-y-auto">
        <div className="flex h-full flex-col gap-3 p-4">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold text-foreground">Documentos</h2>
            <button
              onClick={loadSamples}
              className="inline-flex items-center gap-1 text-xs text-primary hover:underline"
            >
              <ListChecks className="h-3 w-3" /> Carregar exemplo
            </button>
          </div>
          <p className="text-xs text-muted-foreground/70 -mt-1">
            Marque o <span className="text-muted-foreground">esperado</span> de cada documento para calcular a acurácia do
            LLM (test set: 5 corretos + 5 incorretos).
          </p>

          <div className="flex-1 space-y-2 overflow-y-auto pr-1">
            {docs.map((d, i) => (
              <DocumentEntry
                key={i}
                index={i}
                doc={d}
                onChange={(next) => updateDoc(i, next)}
                onRemove={() => removeDoc(i)}
              />
            ))}
            <button
              onClick={addDoc}
              className="flex w-full items-center justify-center gap-1 rounded-lg border border-dashed border-muted-foreground/30 py-2 text-xs text-muted-foreground transition-colors hover:border-primary/50 hover:text-foreground"
            >
              <Plus className="h-3.5 w-3.5" /> Adicionar documento
            </button>
          </div>

          <div className="flex items-center gap-2">
            <label className="text-xs text-muted-foreground">Teto (máx.)</label>
            <input
              type="number"
              min={1}
              value={maxDocuments}
              onChange={(e) => setMaxDocuments(e.target.value)}
              placeholder="todos"
              className="h-7 w-20 rounded-md border border-border bg-background px-2 text-xs text-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
            />
            <span className="text-[10px] text-muted-foreground/50">limite de documentos avaliados</span>
          </div>

          <Button
            onClick={handleEvaluate}
            disabled={isLoading || validCount === 0}
            className="w-full gap-2 bg-gradient-to-r from-primary to-primary/80 hover:from-primary/90 hover:to-primary/70"
          >
            {isLoading ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" /> Avaliando...
              </>
            ) : (
              <>
                <FileCheck className="h-4 w-4" /> Avaliar ({validCount})
              </>
            )}
          </Button>
        </div>
      </div>

      {/* Right: results */}
      <div className="flex-1 overflow-y-auto">
        {isLoading ? (
          <div className="flex h-full flex-col items-center justify-center gap-3">
            <Loader2 className="h-10 w-10 animate-spin text-primary" />
            <p className="text-sm text-muted-foreground">Avaliando {validCount} documento(s)...</p>
          </div>
        ) : result && summary ? (
          <div className="flex h-full flex-col gap-4 p-6">
            {/* Summary + download */}
            <div className="flex items-center justify-between gap-3">
              <div className="flex flex-wrap items-center gap-2">
                <StatChip label="Avaliados" value={`${summary.evaluated}/${summary.total}`} />
                <StatChip label="Corretos" value={String(summary.correct)} tone="emerald" />
                <StatChip label="Incorretos" value={String(summary.incorrect)} tone="red" />
                <StatChip
                  label="Acurácia"
                  value={summary.accuracy === null ? "—" : `${summary.accuracy}%`}
                  tone={summary.accuracy === null ? "muted" : "blue"}
                  hint={summary.accuracy === null ? "sem ground truth" : undefined}
                />
              </div>
              <Button onClick={handleDownload} disabled={isDownloading} variant="outline" size="sm" className="gap-2">
                {isDownloading ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Download className="h-3.5 w-3.5" />}
                {isDownloading ? "Gerando PDF..." : "Baixar PDF"}
              </Button>
            </div>

            <ResultsTable docs={result.documents} />
          </div>
        ) : (
          <EmptyState />
        )}
      </div>
    </div>
  );
}

function StatChip({
  label,
  value,
  tone = "muted",
  hint,
}: {
  label: string;
  value: string;
  tone?: "muted" | "emerald" | "red" | "blue";
  hint?: string;
}) {
  const toneClass = {
    muted: "border-border text-foreground",
    emerald: "border-emerald-500/30 text-emerald-300 bg-emerald-500/5",
    red: "border-red-500/30 text-red-300 bg-red-500/5",
    blue: "border-blue-500/30 text-blue-300 bg-blue-500/5",
  }[tone];
  return (
    <div className={`rounded-md border px-3 py-1.5 ${toneClass}`}>
      <span className="text-[10px] uppercase tracking-wider text-muted-foreground/70">{label}</span>
      <div className="flex items-baseline gap-1">
        <span className="text-sm font-semibold">{value}</span>
        {hint && <span className="text-[10px] text-muted-foreground/60">{hint}</span>}
      </div>
    </div>
  );
}
