const API_BASE = import.meta.env.VITE_API_URL ?? '';

export type AnalysisStatus =
  | 'queued' | 'cloning' | 'scanning' | 'reasoning' | 'generating' | 'validating' | 'done' | 'failed';

export interface Evidence { file: string; line: number; snippet: string }
export interface Fact { value: string; evidence: Evidence[] }
export interface PortFact { port: number; evidence: Evidence[] }

export interface FactsSummary {
  repo_url: string;
  head_sha: string;
  languages: Fact[];
  frameworks: Fact[];
  ports: PortFact[];
  datastores: Fact[];
  queues: Fact[];
  storage: Fact[];
  env_vars: Fact[];
  has_dockerfile: boolean;
  static_output_dir: string | null;
  build_commands: Fact[];
}

export interface ServiceProposal {
  name: string;
  zerops_type: string;
  role: 'frontend' | 'api' | 'worker' | 'database' | 'cache' | 'storage';
  reasoning: string;
  evidence_refs?: string[];
}

export interface ChecklistStep {
  step_id: string;
  phase: 'before_deploy' | 'deploy' | 'after_deploy';
  title: string;
  detail: string;
  docs_url?: string;
  evidence_ref?: string;
  checked?: boolean;
}

export interface AnalysisResult {
  id: string;
  slug: string;
  status: AnalysisStatus;
  error: string | null;
  facts_summary: FactsSummary | null;
  services: ServiceProposal[] | null;
  zerops_yaml: string | null;
  yaml_valid: boolean;
  checklist: ChecklistStep[] | null;
  timings: Record<string, number> | null;
  created_at: string;
  completed_at: string | null;
}

export interface GalleryEntry { slug: string; repo_url: string; created_at: string }

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: { 'Content-Type': 'application/json', ...(init?.headers ?? {}) },
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail ?? `Request failed: ${res.status}`);
  }
  return res.json();
}

export function createAnalysis(repoUrl: string): Promise<{ id: string; slug: string }> {
  return request('/api/analyses', { method: 'POST', body: JSON.stringify({ repo_url: repoUrl }) });
}

export function getAnalysis(idOrSlug: string): Promise<AnalysisResult> {
  return request(`/api/analyses/${idOrSlug}`);
}

export function listGallery(limit = 20): Promise<GalleryEntry[]> {
  return request(`/api/analyses?public=1&limit=${limit}`);
}

export function toggleChecklistStep(analysisId: string, stepId: string): Promise<{ checked: boolean }> {
  return request(`/api/analyses/${analysisId}/checklist/${stepId}/toggle`, { method: 'POST' });
}

export interface ProgressEvent { status: string; message: string }

export function streamAnalysisEvents(
  analysisId: string,
  onEvent: (event: ProgressEvent) => void,
  onDone: () => void,
): () => void {
  const source = new EventSource(`${API_BASE}/api/analyses/${analysisId}/events`);
  source.onmessage = (e) => {
    const data: ProgressEvent = JSON.parse(e.data);
    onEvent(data);
    if (data.status === 'done' || data.status === 'failed') {
      source.close();
      onDone();
    }
  };
  source.onerror = () => { source.close(); onDone(); };
  return () => source.close();
}

export const ORBIT_SELF_REPO_URL = 'https://github.com/abhinav2712/Orbit';
