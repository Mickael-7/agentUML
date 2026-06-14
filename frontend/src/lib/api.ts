const BASE_URL = import.meta.env.VITE_API_URL || "";

async function apiFetch(url: string, options?: RequestInit): Promise<Response> {
  const res = await fetch(url, options);
  if (!res.ok) {
    const text = await res.text().catch(() => "Unknown error");
    throw new Error(text);
  }
  return res;
}

export async function generateJob(text: string, file?: File, provider?: string, model?: string): Promise<{ job_id: string; error?: string }> {
  const formData = new FormData();
  if (text) formData.append("text", text);
  if (file) formData.append("file", file);
  if (provider) formData.append("provider", provider);
  if (model) formData.append("model", model);
  const res = await apiFetch(`${BASE_URL}/api/generate`, { method: "POST", body: formData });
  return res.json();
}

export async function getJobDiagrams(jobId: string): Promise<import("./types").JobStatus> {
  const res = await apiFetch(`${BASE_URL}/api/diagrams/${jobId}`);
  return res.json();
}

export async function getDiagramPuml(jobId: string, diagramId: string): Promise<string> {
  const res = await apiFetch(`${BASE_URL}/api/diagrams/${jobId}/${diagramId}/puml`);
  return res.text();
}

export async function getDiagramImageUrl(jobId: string, diagramId: string, format: string = "png"): Promise<string> {
  return `${BASE_URL}/api/diagrams/${jobId}/${diagramId}/image?format=${format}`;
}

export async function getDiagramMermaid(jobId: string, diagramId: string, diagramType: string): Promise<{ mermaid_text: string }> {
  const res = await apiFetch(`${BASE_URL}/api/diagrams/${jobId}/${diagramId}/mermaid?diagram_type=${diagramType}`);
  return res.json();
}

export async function getConfig(): Promise<import("./types").ConfigResponse> {
  const res = await apiFetch(`${BASE_URL}/api/config`);
  return res.json();
}

export async function updateConfig(data: { provider?: string; model?: string; temperature?: number }): Promise<import("./types").ConfigResponse> {
  const res = await apiFetch(`${BASE_URL}/api/config`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  return res.json();
}

export async function getHistory(limit = 20, offset = 0): Promise<{ jobs: import("./types").HistoryJob[]; total: number }> {
  const res = await apiFetch(`${BASE_URL}/api/history?limit=${limit}&offset=${offset}`);
  return res.json();
}

export async function deleteJob(jobId: string): Promise<void> {
  await apiFetch(`${BASE_URL}/api/history/${jobId}`, { method: "DELETE" });
}

export async function analyzeQuality(text: string, file?: File): Promise<import("./types").QualityResult> {
  const formData = new FormData();
  if (text) formData.append("text", text);
  if (file) formData.append("file", file);
  const res = await apiFetch(`${BASE_URL}/api/quality`, { method: "POST", body: formData });
  return res.json();
}

export async function downloadQualityPdf(result: import("./types").QualityResult): Promise<Blob> {
  const res = await apiFetch(`${BASE_URL}/api/quality/pdf`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(result),
  });
  return res.blob();
}
