import { CheckCircle2, Loader2, XCircle, Zap } from "lucide-react";

interface DiagramProgress {
  diagram_id: string;
  status: string;
  name: string;
  sub_status?: string;
  attempt?: number;
  attempt_max?: number;
  critic_score?: number;
  critic_round?: number;
  critic_round_max?: number;
  error?: string;
}

interface ProgressOverlayProps {
  status: string;
  message: string;
  diagrams: DiagramProgress[];
  tokenUsage?: { prompt_tokens: number; completion_tokens: number; total_tokens: number; call_count: number } | null;
}

const STEPS = [
  { key: "quality_gate", label: "Verificando qualidade" },
  { key: "extracting_rules", label: "Extraindo regras de negocio" },
  { key: "partitioning", label: "Particionando requisitos" },
  { key: "generating", label: "Gerando diagramas" },
  { key: "completed", label: "Concluido" },
];

const SUB_STATUS_LABELS: Record<string, (d: DiagramProgress) => string> = {
  generating: (d) => `Gerando (tentativa ${d.attempt ?? "?"}/${d.attempt_max ?? "?"})...`,
  validating_syntax: () => "Validando sintaxe...",
  validating_semantics: () => "Validando semantica...",
  critiquing: (d) => `Avaliando qualidade (round ${(d.critic_round ?? 0) + 1}/${(d.critic_round_max ?? "?") + 1})...`,
  refining: (d) => {
    const base = "Refinando diagrama";
    return d.critic_score != null ? `${base} (score: ${d.critic_score}/10)` : `${base}...`;
  },
  completed: () => "Concluido",
};

function getSubStatusLabel(d: DiagramProgress): string | null {
  if (!d.sub_status) return null;
  const fn = SUB_STATUS_LABELS[d.sub_status];
  return fn ? fn(d) : d.sub_status;
}

export function ProgressOverlay({ status, message, diagrams, tokenUsage }: ProgressOverlayProps) {
  const currentStepIdx = STEPS.findIndex((s) => s.key === status) ?? 0;

  return (
    <div className="absolute inset-0 z-10 flex items-center justify-center bg-background/80 backdrop-blur-sm">
      <div className="w-full max-w-md rounded-lg border border-border bg-card p-6 shadow-lg">
        <div className="flex items-center gap-3 mb-4">
          <Loader2 className="h-5 w-5 animate-spin text-primary" />
          <p className="text-sm text-foreground">{message}</p>
        </div>

        <div className="space-y-2">
          {STEPS.map((step, idx) => {
            const isActive = idx === currentStepIdx;
            const isDone = idx < currentStepIdx || status === "completed";
            return (
              <div key={step.key} className={`flex items-center gap-2 text-sm ${isDone ? "text-primary" : isActive ? "text-foreground" : "text-muted-foreground"}`}>
                {isDone ? <CheckCircle2 className="h-4 w-4" /> : isActive ? <Loader2 className="h-4 w-4 animate-spin" /> : <div className="h-4 w-4 rounded-full border border-muted-foreground/50" />}
                {step.label}
              </div>
            );
          })}
        </div>

        {diagrams.length > 0 && (
          <div className="mt-4 space-y-1 border-t border-border pt-3">
            {diagrams.map((d) => {
              const isDone = d.status === "completed";
              const isFailed = d.status === "failed";
              const subLabel = getSubStatusLabel(d);

              return (
                <div key={d.diagram_id} className="flex flex-col gap-0.5">
                  <div className="flex items-center gap-2 text-xs">
                    {isDone ? <CheckCircle2 className="h-3 w-3 text-green-500" /> : isFailed ? <XCircle className="h-3 w-3 text-red-500" /> : <Loader2 className="h-3 w-3 animate-spin text-primary" />}
                    <span className={isDone ? "text-foreground" : isFailed ? "text-red-400" : "text-muted-foreground"}>
                      {d.name || d.diagram_id}
                    </span>
                  </div>
                  {!isDone && !isFailed && subLabel && (
                    <span className="ml-5 text-[11px] text-muted-foreground/70 italic">
                      {subLabel}
                    </span>
                  )}
                </div>
              );
            })}
          </div>
        )}

        {tokenUsage && tokenUsage.total_tokens > 0 && (
          <div className="mt-3 flex items-center gap-2 border-t border-border pt-3 text-xs text-muted-foreground">
            <Zap className="h-3 w-3 text-yellow-500" />
            <span>{tokenUsage.total_tokens.toLocaleString()} tokens</span>
            <span className="text-muted-foreground/50">
              ({tokenUsage.prompt_tokens.toLocaleString()} in / {tokenUsage.completion_tokens.toLocaleString()} out / {tokenUsage.call_count} calls)
            </span>
          </div>
        )}
      </div>
    </div>
  );
}
