/**
 * API client for the Cybersecurity Backend (Django DRF).
 * Base URL points to the Django dev server on port 8000.
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

// ── Types ────────────────────────────────────────────────────────────

export interface AnomalyEvent {
  event_id: string;
  user_id: string;
  entity_id?: string;
  timestamp?: string;
  score?: number;
  combined_score?: number | null;
  if_score?: number | null;
  dim_scores?: Record<string, number> | null;
  dimension_scores?: Record<string, number> | null;
  triggered_rules?: string[];
  rules?: string[] | null;
  raw_features?: Record<string, number> | null;
  confidence?: string;
  cold_start?: boolean;
  threat_classification?: string;
  monitor?: string | null;
  simulated?: boolean;
}

export interface ContextSummary {
  asset_sensitivity: string;
  asset_data_type: string;
  recent_incidents: unknown;
  triggered_rules_count: number;
}

export interface DecisionOutput {
  event_id: string;
  timestamp: string;
  user_id: string;
  entity_id: string;

  base_score: number;
  risk_adjustment: number;
  adjusted_risk_score: number;
  risk_level: string; // LOW | MEDIUM | HIGH

  decision: string; // ALLOW | MONITOR | ESCALATE | BLOCK
  recommended_action: string;

  base_score_analysis: string;
  risk_factors: string[];
  mitigating_factors: string[];
  adjustment_reasoning: string;
  decision_reasoning: string;

  context_summary: ContextSummary;
  confidence: string;
  computation_method?: string;
  llm_driven?: boolean;
  execution_logs?: string[];
}

export interface HealthStatus {
  status: string;
  agent: string;
  version: string;
}

export interface SampleEventsResponse {
  events: AnomalyEvent[];
}

export interface AnalyzeError {
  error: string;
  details?: Record<string, unknown>;
}

// ── API Methods ──────────────────────────────────────────────────────

async function apiFetch<T>(
  path: string,
  options?: RequestInit & { timeout?: number }
): Promise<T> {
  const { timeout, ...fetchOptions } = options || {};
  
  // Create abort controller for timeout
  const controller = new AbortController();
  const timeoutId = timeout ? setTimeout(() => controller.abort(), timeout) : null;
  
  try {
    const res = await fetch(`${API_BASE}${path}`, {
      headers: { "Content-Type": "application/json" },
      signal: controller.signal,
      ...fetchOptions,
    });

    if (timeoutId) clearTimeout(timeoutId);

    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      throw new Error(body.error || `API Error ${res.status}`);
    }

    return res.json() as Promise<T>;
  } catch (error) {
    if (timeoutId) clearTimeout(timeoutId);
    if (error instanceof Error && error.name === 'AbortError') {
      throw new Error(`Request timed out after ${timeout}ms`);
    }
    throw error;
  }
}

/** GET /api/v1/risk-decision/health/ */
export async function getHealthStatus(): Promise<HealthStatus> {
  return apiFetch<HealthStatus>("/api/v1/risk-decision/health/");
}

/** GET /api/v1/risk-decision/sample-events/ */
export async function getSampleEvents(): Promise<SampleEventsResponse> {
  return apiFetch<SampleEventsResponse>("/api/v1/risk-decision/sample-events/");
}

/** POST /api/v1/risk-decision/analyze/ */
export async function analyzeEvent(
  event: AnomalyEvent
): Promise<DecisionOutput> {
  return apiFetch<DecisionOutput>("/api/v1/risk-decision/analyze/", {
    method: "POST",
    body: JSON.stringify(event),
  });
}

/** POST /api/v1/risk-decision/batch/ */
export async function analyzeBatch(
  events: AnomalyEvent[],
  parallel = 1
): Promise<{ results: Array<{ ok: boolean; decision?: DecisionOutput; error?: string }> }> {
  return apiFetch("/api/v1/risk-decision/batch/", {
    method: "POST",
    body: JSON.stringify({ events, parallel }),
  });
}

/** GET /api/v1/risk-decision/cache/stats/ */
export async function getCacheStats() {
  return apiFetch<Record<string, unknown>>("/api/v1/risk-decision/cache/stats/");
}

// ── Behavior Agent Types ─────────────────────────────────────────────

export interface SessionInput {
  user_id: string;
  pc?: string;
  session_start?: string;
  hour_of_day?: number;
  is_weekend?: number;
  is_outside_hours?: number;
  duration_minutes?: number;
  file_count?: number;
  max_sensitivity?: number;
  usb_connected?: number;
  usb_first_time?: number;
  email_count?: number;
  has_ext_email?: number;
  visited_exfil_domain?: number;
  visited_jobsearch_domain?: number;
  simulated?: boolean;
}

export interface DimensionScores {
  time: number;
  device: number;
  volume: number;
  sensitivity: number;
}

export interface DetectionAgentAnalysis {
  model: string;
  llm_used: boolean;
  analyst_note: string;
  scoring_mode: string;
  score: number;
  threshold: number;
  verdict: string;
  triggered_signals: string[];
  dimension_breakdown: DimensionScores;
  session_summary: Record<string, unknown>;
  baseline_context: Record<string, unknown>;
}

export interface BehaviorAnomalyResult {
  event_id: string;
  timestamp: string;
  source: string[];
  user_anomaly_score: number;
  network_anomaly_score: number | null;
  combined_score: number;
  user_id: string;
  entity_id: string | null;
  dimension_scores: DimensionScores;
  triggered_rules: string[];
  network_attack_category: string | null;
  correlation: Record<string, unknown>;
  explanation: string;
  baseline_age_days: number;
  confidence: string;
  cold_start: boolean;
  simulated: boolean;
  flagged: boolean;
  if_score: number;
  detection_agent_analysis: DetectionAgentAnalysis;
}

export interface BehaviorHealthStatus {
  status: string;
  agent: string;
  version: string;
}

export interface UserBaseline {
  user_id: string;
  department?: string;
  observation_days?: number;
  cold_start?: boolean;
  login_hour_mean?: number;
  login_hour_std?: number;
  daily_file_access_mean?: number;
  recent_scores?: number[];
  [key: string]: unknown;
}

export interface UserHistory {
  user_id: string;
  history: Array<{
    timestamp: string;
    score: number;
    flagged: boolean;
    verdict: string;
  }>;
}

// ── Behavior Agent API Methods ───────────────────────────────────────

/** GET /api/v1/behavior/health/ */
export async function getBehaviorHealth(): Promise<BehaviorHealthStatus> {
  return apiFetch<BehaviorHealthStatus>("/api/v1/behavior/health/");
}

/** POST /api/v1/behavior/score/ */
export async function scoreBehaviorSession(
  session: SessionInput
): Promise<BehaviorAnomalyResult> {
  return apiFetch<BehaviorAnomalyResult>("/api/v1/behavior/score/", {
    method: "POST",
    body: JSON.stringify(session),
  });
}

/** GET /api/v1/behavior/baseline/<user_id>/ */
export async function getUserBaseline(userId: string): Promise<UserBaseline> {
  return apiFetch<UserBaseline>(`/api/v1/behavior/baseline/${userId}/`);
}

/** GET /api/v1/behavior/history/<user_id>/ */
export async function getUserHistory(
  userId: string,
  limit = 10
): Promise<UserHistory> {
  return apiFetch<UserHistory>(`/api/v1/behavior/history/${userId}/?limit=${limit}`);
}

/** GET /api/v1/behavior/sample-sessions/ */
export async function getSampleBehaviorSessions(
  n = 30,
  flaggedOnly = false
): Promise<{ sessions: SessionInput[]; total: number }> {
  const params = new URLSearchParams({ n: String(n) });
  if (flaggedOnly) params.set('flagged', '1');
  return apiFetch(`/api/v1/behavior/sample-sessions/?${params}`);
}

// ── Data Agent Types ─────────────────────────────────────────────────

export interface DataCollectionResult {
  ok: boolean;
  llm_reasoning: string;
  tools_executed: string[];
  events_by_tool: Record<string, number>;
  total_events: number;
  collectors: string[];
  timestamp: string;
  status: string;
  errors?: string[];
  // Pipeline mode fields
  sessions_created?: number;
  behavior_result?: {
    ok: boolean;
    sessions_sent: number;
    flagged_count: number;
    results: Array<{
      ok: boolean;
      anomaly_result?: BehaviorAnomalyResult;
      error?: string;
    }>;
    error?: string;
  };
}

// ── Data Agent API Methods ───────────────────────────────────────────

/** POST /api/v1/data/pipeline-collect/ */
export async function pipelineCollectData(
  collectors: string[] = []
): Promise<DataCollectionResult> {
  // Increased timeout to 10 minutes for pipeline mode (data collection + behavior analysis + risk analysis)
  return apiFetch<DataCollectionResult>("/api/v1/data/pipeline-collect/", {
    method: "POST",
    body: JSON.stringify({ collectors }),
    timeout: 600000, // 10 minutes
  });
}

// ── Attacker Agent Types ─────────────────────────────────────────────

export interface AttackPattern {
  id: string;
  name: string;
  category: string;
  mitre_technique: string;
  severity: string;
  description: string;
}

export interface AttackInjectionResult {
  ok: boolean;
  attack_id: string;
  events_generated: number;
  events_stored: number;
  attack_name?: string;
  mitre_technique?: string;
  severity?: string;
  timestamp: string;
  error?: string;
}

export interface AttackerStats {
  ok: boolean;
  total_attacks: number;
  by_type: Record<string, number>;
  by_severity: Record<string, number>;
  agent_running: boolean;
  simulating: boolean;
  timestamp: string;
  error?: string;
}

export interface AttackHistoryItem {
  attack_id: string;
  attack_name: string;
  attack_type: string;
  mitre_technique: string;
  severity: string;
  timestamp: string;
  user_id: string;
  device_id: string;
  event_count: number;
}

export interface AttackHistory {
  ok: boolean;
  attacks: AttackHistoryItem[];
  count: number;
  limit: number;
  timestamp: string;
  error?: string;
}

export interface AttackerHealthStatus {
  status: string;
  agent: string;
  version: string;
  capabilities: string[];
}

// ── Attacker Agent API Methods ───────────────────────────────────────

/** GET /api/v1/attacker/health/ */
export async function getAttackerHealth(): Promise<AttackerHealthStatus> {
  return apiFetch<AttackerHealthStatus>("/api/v1/attacker/health/");
}

/** GET /api/v1/attacker/patterns/ */
export async function listAttackPatterns(
  category?: string,
  severity?: string
): Promise<{ ok: boolean; patterns: AttackPattern[]; count: number; error?: string }> {
  const params = new URLSearchParams();
  if (category) params.set('category', category);
  if (severity) params.set('severity', severity);
  const query = params.toString();
  return apiFetch(`/api/v1/attacker/patterns/${query ? '?' + query : ''}`);
}

/** POST /api/v1/attacker/inject/ */
export async function injectAttack(
  attackId: string,
  userId?: string,
  deviceId?: string
): Promise<AttackInjectionResult> {
  return apiFetch<AttackInjectionResult>("/api/v1/attacker/inject/", {
    method: "POST",
    body: JSON.stringify({
      attack_id: attackId,
      user_id: userId,
      device_id: deviceId,
    }),
  });
}

/** POST /api/v1/attacker/start/ */
export async function startAttackerAgent(
  intervalSeconds: number = 600,
  maxAttacks?: number
): Promise<{ ok: boolean; message: string; error?: string }> {
  return apiFetch("/api/v1/attacker/start/", {
    method: "POST",
    body: JSON.stringify({
      interval_seconds: intervalSeconds,
      max_attacks: maxAttacks,
    }),
  });
}

/** POST /api/v1/attacker/stop/ */
export async function stopAttackerAgent(): Promise<{ ok: boolean; message: string; error?: string }> {
  return apiFetch("/api/v1/attacker/stop/", {
    method: "POST",
  });
}

/** POST /api/v1/attacker/simulate/ - Run ONE complete 5-phase attack cycle */
export async function simulateAttack(): Promise<{ ok: boolean; message: string; error?: string }> {
  return apiFetch("/api/v1/attacker/simulate/", {
    method: "POST",
  });
}

/** GET /api/v1/attacker/stats/ */
export async function getAttackerStats(): Promise<AttackerStats> {
  return apiFetch<AttackerStats>("/api/v1/attacker/stats/");
}

/** GET /api/v1/attacker/history/ */
export async function getAttackHistory(limit: number = 50): Promise<AttackHistory> {
  return apiFetch<AttackHistory>(`/api/v1/attacker/history/?limit=${limit}`);
}

/** GET /api/v1/attacker/logs/ */
export async function getAttackerLogs(limit: number = 50): Promise<{
  ok: boolean;
  logs: Array<{
    timestamp: string;
    level: string;
    message: string;
    logger: string;
  }>;
  count: number;
  error?: string;
}> {
  return apiFetch(`/api/v1/attacker/logs/?limit=${limit}`);
}

/** GET /api/v1/attacker/behavior-result/ - Get A2A behavior analysis result */
export async function getAttackerBehaviorResult(): Promise<{
  ok: boolean;
  simulating: boolean;
  behavior_result?: {
    ok: boolean;
    sessions_sent: number;
    results: Array<{
      ok: boolean;
      anomaly_result?: BehaviorAnomalyResult;
      error?: string;
    }>;
    flagged_count: number;
    skipped_count: number;
    error?: string;
  };
  error?: string;
}> {
  return apiFetch(`/api/v1/attacker/behavior-result/`);
}

// ── Network Agent Types ──────────────────────────────────────────────

export interface NetworkEvent {
  event_type: string;
  action: string;
  timestamp: string;
  user_id: string;
  device_id?: string;
  metadata: {
    src_ip: string;
    dst_ip: string;
    src_port: number;
    dst_port: number;
    protocol: string;
    bytes_sent: number;
    bytes_received: number;
    process_name?: string;
  };
}

export interface NetworkSession {
  user_id: string;
  device_id: string;
  events: NetworkEvent[];
}

export interface NetworkAnalysisResult {
  event_id: string;
  timestamp: string;
  source: string[];
  user_anomaly_score: number | null;
  network_anomaly_score: number;
  combined_score: number;
  user_id: string;
  entity_id: string;
  dimension_scores: DimensionScores;
  triggered_rules: string[];
  network_attack_category: string | null;
  correlation: Record<string, unknown>;
  explanation: string;
  baseline_age_days: number;
  confidence: string;
  cold_start: boolean;
  simulated: boolean;
  flagged: boolean;
  if_score: number;
  detection_agent_analysis: DetectionAgentAnalysis;
}

export interface NetworkBatchResponse {
  results: NetworkAnalysisResult[];
  count: number;
  flagged: number;
}

// ── Network Agent API Methods ────────────────────────────────────────

/** GET /api/v1/network/health/ */
export async function getNetworkHealth(): Promise<{ status: string; agent: string }> {
  return apiFetch("/api/v1/network/health/");
}

/** POST /api/v1/network/analyze/batch/ */
export async function analyzeNetworkBatch(
  sessions: NetworkSession[]
): Promise<NetworkBatchResponse> {
  return apiFetch<NetworkBatchResponse>("/api/v1/network/analyze/batch/", {
    method: "POST",
    body: JSON.stringify({ sessions }),
  });
}

/** Helper: Get current network connections from the machine */
export async function getCurrentNetworkConnections(): Promise<NetworkEvent[]> {
  // This would typically call a local data collection endpoint
  // For now, return empty array - implement based on your data agent
  return [];
}
