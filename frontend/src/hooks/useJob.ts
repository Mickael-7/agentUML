import { useState, useCallback, useRef, useEffect } from "react";
import type { DiagramInfo } from "@/lib/types";
import { generateJob } from "@/lib/api";
import { subscribeToJob } from "@/lib/sse";

export interface TokenUsage {
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
  call_count: number;
}

export function useJob() {
  const [jobId, setJobId] = useState<string | null>(null);
  const [status, setStatus] = useState<string>("idle");
  const [statusMessage, setStatusMessage] = useState<string>("");
  const [diagrams, setDiagrams] = useState<DiagramInfo[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [tokenUsage, setTokenUsage] = useState<TokenUsage | null>(null);
  const unsubscribeRef = useRef<(() => void) | null>(null);

  // Cleanup SSE on unmount
  useEffect(() => {
    return () => {
      unsubscribeRef.current?.();
    };
  }, []);

  const startGeneration = useCallback(async (text: string, file?: File, provider?: string, model?: string) => {
    // Cleanup previous subscription
    unsubscribeRef.current?.();
    unsubscribeRef.current = null;

    setDiagrams([]);
    setError(null);
    setTokenUsage(null);
    setStatus("queued");
    setStatusMessage("Starting generation...");

    try {
      const result = await generateJob(text, file, provider, model);
      if ("error" in result && result.error) {
        setError(result.error as string);
        setStatus("failed");
        return;
      }
      setJobId(result.job_id);

      const unsubscribe = subscribeToJob(result.job_id, {
        onStatus: (d) => {
          setStatus(d.status);
          setStatusMessage(d.message);
        },
        onDiagram: (d) => {
          // Update live token usage from diagram events
          if (d.token_usage) {
            setTokenUsage(d.token_usage as TokenUsage);
          }
          setDiagrams((prev) => {
            const idx = prev.findIndex((x) => x.diagram_id === d.diagram_id);
            if (idx >= 0) {
              const next = [...prev];
              next[idx] = { ...next[idx], ...d, status: d.status as DiagramInfo["status"] };
              return next;
            }
            return [...prev, d as DiagramInfo];
          });
        },
        onComplete: (d) => {
          setStatus(d.exit_code === 0 ? "completed" : "completed_with_errors");
          setStatusMessage(`Done: ${d.succeeded}/${d.total} diagrams generated.`);
          if (d.token_usage) setTokenUsage(d.token_usage);
          unsubscribeRef.current = null;
        },
        onError: (d) => {
          setError(d.message);
          setStatus("failed");
          unsubscribeRef.current = null;
        },
      });
      unsubscribeRef.current = unsubscribe;
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unknown error");
      setStatus("failed");
    }
  }, []);

  const reset = useCallback(() => {
    unsubscribeRef.current?.();
    unsubscribeRef.current = null;
    setJobId(null);
    setStatus("idle");
    setStatusMessage("");
    setDiagrams([]);
    setError(null);
    setTokenUsage(null);
  }, []);

  return { jobId, status, statusMessage, diagrams, error, tokenUsage, startGeneration, reset };
}
