const BASE_URL = import.meta.env.VITE_API_URL || "";

interface SSEHandlers {
  onStatus?: (data: { status: string; message: string; total?: number }) => void;
  onDiagram?: (data: {
    diagram_id: string;
    diagram_type: string;
    name: string;
    status: string;
    error?: string;
    sub_status?: string;
    attempt?: number;
    attempt_max?: number;
    critic_score?: number;
    critic_round?: number;
    critic_round_max?: number;
  }) => void;
  onComplete?: (data: {
    job_id: string;
    exit_code: number;
    total: number;
    succeeded: number;
    failed: number;
    token_usage?: { prompt_tokens: number; completion_tokens: number; total_tokens: number; call_count: number };
  }) => void;
  onError?: (data: { message: string }) => void;
}

function safeParse(data: string | null): Record<string, unknown> | null {
  if (!data) return null;
  try {
    return JSON.parse(data);
  } catch {
    return null;
  }
}

export function subscribeToJob(jobId: string, handlers: SSEHandlers): () => void {
  const url = `${BASE_URL}/api/generate/${jobId}/stream`;
  const eventSource = new EventSource(url);

  eventSource.addEventListener("status", (e) => {
    const data = safeParse((e as MessageEvent).data);
    if (data) handlers.onStatus?.(data as Parameters<NonNullable<SSEHandlers["onStatus"]>>[0]);
  });
  eventSource.addEventListener("diagram", (e) => {
    const data = safeParse((e as MessageEvent).data);
    if (data) handlers.onDiagram?.(data as Parameters<NonNullable<SSEHandlers["onDiagram"]>>[0]);
  });
  eventSource.addEventListener("complete", (e) => {
    const data = safeParse((e as MessageEvent).data);
    if (data) handlers.onComplete?.(data as Parameters<NonNullable<SSEHandlers["onComplete"]>>[0]);
    eventSource.close();
  });
  eventSource.addEventListener("error", (e) => {
    const data = safeParse((e as MessageEvent).data);
    handlers.onError?.(data ? (data as { message: string }) : { message: "Connection lost" });
    eventSource.close();
  });

  return () => eventSource.close();
}
