"use client"

import { useState, useEffect, useCallback } from "react"
import { motion } from "framer-motion"
import { cn } from "@/lib/utils"
import { Card, CardContent, CardHeader } from "@/components/ui/card"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Button } from "@/components/ui/button"
import {
  getSampleBehaviorSessions,
  scoreBehaviorSession,
  type BehaviorAnomalyResult,
  type SessionInput,
} from "@/lib/api"
import {
  Play,
  Loader2,
  AlertTriangle,
  ShieldAlert,
  Eye,
  ShieldOff,
  ShieldCheck,
  RefreshCw,
  Network,
} from "lucide-react"
import { NetworkAgentTest } from "./network-agent-test"

interface BehaviorAgentLiveProps {
  agentSlug: string
  onLog?: (log: { type: "info" | "success" | "error" | "warning"; message: string }) => void
  onAnalysisComplete?: (result: { timeTakenMs: number; isAlert: boolean }) => void
  pipelineActive?: boolean
}

const verdictConfig: Record<string, { icon: typeof ShieldCheck; color: string }> = {
  LOW:      { icon: ShieldCheck, color: "text-emerald-500" },
  MEDIUM:   { icon: Eye,         color: "text-amber-500"   },
  HIGH:     { icon: ShieldAlert, color: "text-orange-500"  },
  CRITICAL: { icon: ShieldOff,   color: "text-red-500"     },
}

const verdictBadge: Record<string, string> = {
  LOW:      "border-emerald-500/30 bg-emerald-500/10 text-emerald-600",
  MEDIUM:   "border-amber-500/30  bg-amber-500/10  text-amber-600",
  HIGH:     "border-orange-500/30 bg-orange-500/10 text-orange-600",
  CRITICAL: "border-red-500/30    bg-red-500/10    text-red-600",
}

/** Build a human-readable label for a session row */
function sessionLabel(s: SessionInput, i: number): string {
  const signals: string[] = []
  if (s.visited_exfil_domain) signals.push("exfil")
  if (s.usb_connected)        signals.push("USB")
  if (s.has_ext_email)        signals.push("ext-email")
  if (s.is_outside_hours)     signals.push("after-hours")
  if (s.visited_jobsearch_domain) signals.push("job-search")
  const tag = signals.length ? `[${signals.join(",")}]` : "[normal]"
  return `#${i + 1} ${s.user_id} · ${s.session_start?.slice(0, 10) ?? ""} ${tag}`
}

export function BehaviorAgentLive({ agentSlug, onLog, onAnalysisComplete, pipelineActive }: BehaviorAgentLiveProps) {
  const [activeTab, setActiveTab]       = useState("summary")
  const [sessions, setSessions]         = useState<SessionInput[]>([])
  const [selectedIdx, setSelectedIdx]   = useState(0)
  const [result, setResult]             = useState<BehaviorAnomalyResult | null>(null)
  const [loading, setLoading]           = useState(false)
  const [loadingSessions, setLoadingSessions] = useState(false)
  const [error, setError]               = useState<string | null>(null)
  const [flaggedOnly, setFlaggedOnly]   = useState(false)

  const isBehaviorAgent = agentSlug === "behavior-agent"

  const addLog = useCallback(
    (type: "info" | "success" | "error" | "warning", message: string) => {
      onLog?.({ type, message })
    },
    [onLog]
  )

  const loadSessions = useCallback(async (flagged: boolean) => {
    setLoadingSessions(true)
    setError(null)
    try {
      addLog("info", `LOAD Fetching sessions from test_sessions.parquet (flagged=${flagged})`)
      const res = await getSampleBehaviorSessions(30, flagged)
      setSessions(res.sessions)
      setSelectedIdx(0)
      setResult(null)
      addLog("success", `LOAD ${res.total} sessions loaded from Monitor A test data`)
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Unknown error"
      setError(msg)
      addLog("error", `LOAD failed: ${msg}`)
    } finally {
      setLoadingSessions(false)
    }
  }, [addLog])

  useEffect(() => {
    if (!isBehaviorAgent) return
    loadSessions(false)
  }, [isBehaviorAgent, loadSessions])

  const handleToggleFlagged = () => {
    const next = !flaggedOnly
    setFlaggedOnly(next)
    loadSessions(next)
  }

  const handleScore = async () => {
    if (sessions.length === 0) return
    const session = sessions[selectedIdx]
    setLoading(true)
    setError(null)
    setResult(null)

    addLog("info", `INIT Scoring: ${session.user_id} @ ${session.session_start?.slice(0, 16)}`)
    addLog("info", `FEAT hour=${session.hour_of_day} files=${session.file_count} usb=${session.usb_connected} exfil=${session.visited_exfil_domain}`)

    try {
      addLog("info", "SEND POST /api/v1/behavior/score/")
      const t0  = performance.now()
      const res = await scoreBehaviorSession(session)
      const ms  = Math.round(performance.now() - t0)

      setResult(res)
      const a = res.detection_agent_analysis
      addLog("success", `DONE verdict=${a.verdict} score=${a.score.toFixed(4)} in ${ms}ms`)
      addLog(res.flagged ? "warning" : "success",
        `FLAGGED=${res.flagged} confidence=${res.confidence} cold_start=${res.cold_start}`)
      if (res.triggered_rules.length > 0)
        addLog("warning", `RULES ${res.triggered_rules.join(", ")}`)
      addLog("info", `LLM ${a.llm_used ? "used" : "template"} | ${a.analyst_note.slice(0, 80)}...`)
      setActiveTab("summary")

      onAnalysisComplete?.({ timeTakenMs: ms, isAlert: res.flagged })
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Unknown error"
      setError(msg)
      addLog("error", `FAIL ${msg}`)
    } finally {
      setLoading(false)
    }
  }

  if (!isBehaviorAgent) return null

  const analysis = result?.detection_agent_analysis
  const vc = analysis ? (verdictConfig[analysis.verdict] ?? verdictConfig.MEDIUM) : null
  const vb = analysis ? (verdictBadge[analysis.verdict]  ?? verdictBadge.MEDIUM)  : ""
  const selected = sessions[selectedIdx]

  return (
    <div className="flex h-full flex-col gap-4">
      {/* Controls */}
      <Card className="shrink-0 rounded border-border">
        <CardHeader className="p-3">
          <div className="flex items-center justify-between">
            <span className="font-mono text-[10px] font-medium uppercase tracking-wider text-muted-foreground">
              Live Scoring — Monitor A
            </span>
            <div className="flex items-center gap-2">
              <button
                onClick={handleToggleFlagged}
                className={cn(
                  "rounded border px-1.5 py-0.5 font-mono text-[9px] font-medium uppercase transition-colors",
                  flaggedOnly
                    ? "border-amber-500/50 bg-amber-500/20 text-amber-600"
                    : "border-border bg-muted/50 text-muted-foreground hover:text-foreground"
                )}
              >
                {flaggedOnly ? "Anomalous only" : "All sessions"}
              </button>
              <button
                onClick={() => loadSessions(flaggedOnly)}
                disabled={loadingSessions}
                className="rounded border border-border bg-muted/50 p-1 text-muted-foreground hover:text-foreground disabled:opacity-50"
                title="Reload sessions"
              >
                <RefreshCw className={cn("h-3 w-3", loadingSessions && "animate-spin")} />
              </button>
            </div>
          </div>
        </CardHeader>

        <CardContent className="space-y-3 p-3 pt-0">
          {/* Session selector */}
          {sessions.length > 0 ? (
            <div className="space-y-1.5">
              <label className="font-mono text-[10px] uppercase tracking-wider text-muted-foreground">
                Select Session ({sessions.length} loaded from test_sessions.parquet)
              </label>
              <select
                value={selectedIdx}
                onChange={(e) => { setSelectedIdx(Number(e.target.value)); setResult(null) }}
                className="w-full rounded border border-border bg-card px-2 py-1.5 font-mono text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-blue-500"
              >
                {sessions.map((s, i) => (
                  <option key={i} value={i}>{sessionLabel(s, i)}</option>
                ))}
              </select>
            </div>
          ) : (
            <div className="rounded border border-border bg-muted/30 p-2 text-center font-mono text-[11px] text-muted-foreground">
              {loadingSessions ? "Loading sessions..." : "No sessions loaded"}
            </div>
          )}

          {/* Selected session preview */}
          {selected && (
            <div className="grid grid-cols-3 gap-1.5 rounded border border-border bg-muted/30 p-2">
              {(["hour_of_day", "file_count", "duration_minutes", "usb_connected", "has_ext_email", "visited_exfil_domain", "is_outside_hours", "is_weekend", "max_sensitivity"] as const).map((k) => (
                <div key={k} className="flex flex-col">
                  <span className="font-mono text-[9px] uppercase tracking-wider text-muted-foreground">
                    {k.replace(/_/g, " ")}
                  </span>
                  <span className={cn(
                    "font-mono text-xs font-medium",
                    (k === "usb_connected" || k === "has_ext_email" || k === "visited_exfil_domain") && selected[k]
                      ? "text-amber-500"
                      : "text-foreground"
                  )}>
                    {String(selected[k] ?? "—")}
                  </span>
                </div>
              ))}
            </div>
          )}

          {pipelineActive && (
            <div className="flex items-center gap-2 rounded border border-blue-500/30 bg-blue-500/10 p-2">
              <span className="relative flex h-2 w-2">
                <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-blue-400 opacity-75" />
                <span className="relative inline-flex h-2 w-2 rounded-full bg-blue-500" />
              </span>
              <span className="font-mono text-[11px] text-blue-500">Running via pipeline — check logs panel for real-time updates</span>
            </div>
          )}

          <Button
            onClick={handleScore}
            disabled={loading || sessions.length === 0 || pipelineActive}
            className="w-full gap-2 rounded-md bg-blue-600 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
          >
            {pipelineActive ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                <span>Running via Pipeline...</span>
              </>
            ) : loading ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                <span>Scoring...</span>
              </>
            ) : (
              <>
                <Play className="h-4 w-4" />
                <span>Score Session</span>
              </>
            )}
          </Button>

          {error && (
            <div className="flex items-center gap-2 rounded border border-red-500/30 bg-red-500/10 p-2">
              <AlertTriangle className="h-3 w-3 text-red-500" />
              <span className="font-mono text-[11px] text-red-500">{error}</span>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Result */}
      {result && analysis && (
        <Card className="rounded border-border">
          <CardHeader className="shrink-0 border-b border-border p-3">
            <div className="flex items-center justify-between">
              <span className="font-mono text-[10px] font-medium uppercase tracking-wider text-muted-foreground">
                Anomaly Result
              </span>
              <div className="flex items-center gap-2">
                <span className={cn("rounded border px-1.5 py-0.5 font-mono text-[9px] font-bold uppercase", vb)}>
                  {analysis.verdict}
                </span>
                {vc && (
                  <span className={cn("flex items-center gap-1 font-mono text-[10px] font-semibold", vc.color)}>
                    <vc.icon className="h-3.5 w-3.5" />
                    {result.flagged ? "FLAGGED" : "NORMAL"}
                  </span>
                )}
              </div>
            </div>
          </CardHeader>

          <CardContent className="flex-1 overflow-auto p-0">
            <Tabs value={activeTab} onValueChange={setActiveTab} className="flex flex-col">
              <TabsList className="mx-3 mt-3 h-7 w-fit shrink-0 rounded border border-border bg-muted/50 p-0.5">
                <TabsTrigger value="summary"  className="h-6 rounded px-2 font-mono text-[10px] uppercase tracking-wider">Summary</TabsTrigger>
                <TabsTrigger value="analysis" className="h-6 rounded px-2 font-mono text-[10px] uppercase tracking-wider">Analysis</TabsTrigger>
                <TabsTrigger value="json"     className="h-6 rounded px-2 font-mono text-[10px] uppercase tracking-wider">JSON</TabsTrigger>
              </TabsList>

              <div className="p-3">
                {/* Summary */}
                <TabsContent value="summary" className="m-0 mt-0">
                  <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="space-y-3">
                    <div className="grid grid-cols-2 gap-2">
                      {[
                        { label: "IF Score",     value: analysis.score.toFixed(4) },
                        { label: "Verdict",      value: analysis.verdict },
                        { label: "User",         value: result.user_id },
                        { label: "Confidence",   value: result.confidence.toUpperCase() },
                        { label: "Cold Start",   value: result.cold_start ? "YES" : "NO" },
                        { label: "Baseline Age", value: `${result.baseline_age_days}d` },
                      ].map(({ label, value }) => (
                        <div key={label} className="rounded border border-border bg-card p-2">
                          <p className="font-mono text-[9px] uppercase tracking-wider text-muted-foreground">{label}</p>
                          <p className={cn("mt-0.5 font-mono text-sm font-semibold",
                            label === "Verdict" ? vc?.color : "text-foreground"
                          )}>{value}</p>
                        </div>
                      ))}
                    </div>

                    {/* Dimension bars */}
                    <div className="rounded border border-border bg-muted/30 p-3 space-y-2">
                      <h4 className="font-mono text-[10px] font-medium uppercase tracking-wider text-muted-foreground">
                        Dimension Scores
                      </h4>
                      {Object.entries(analysis.dimension_breakdown).map(([dim, val]) => (
                        <div key={dim} className="flex items-center gap-2">
                          <span className="w-20 font-mono text-[10px] uppercase text-muted-foreground">{dim}</span>
                          <div className="flex-1 h-1.5 rounded-full bg-muted overflow-hidden">
                            <div
                              className={cn("h-full rounded-full transition-all",
                                (val as number) > 0.6 ? "bg-red-500" :
                                (val as number) > 0.3 ? "bg-amber-500" : "bg-emerald-500"
                              )}
                              style={{ width: `${Math.min((val as number) * 100, 100)}%` }}
                            />
                          </div>
                          <span className="w-10 text-right font-mono text-[10px] text-foreground">
                            {(val as number).toFixed(3)}
                          </span>
                        </div>
                      ))}
                    </div>

                    {/* Triggered rules */}
                    {result.triggered_rules.length > 0 && (
                      <div className="rounded border border-amber-500/30 bg-amber-500/10 p-3 space-y-1">
                        <h4 className="font-mono text-[10px] font-medium uppercase tracking-wider text-amber-600">
                          Triggered Signals
                        </h4>
                        {result.triggered_rules.map((r) => (
                          <div key={r} className="flex items-center gap-1.5">
                            <AlertTriangle className="h-3 w-3 text-amber-500 shrink-0" />
                            <span className="font-mono text-[11px] text-amber-700 dark:text-amber-400">{r}</span>
                          </div>
                        ))}
                      </div>
                    )}
                  </motion.div>
                </TabsContent>

                {/* Analysis — LLM note */}
                <TabsContent value="analysis" className="m-0 mt-0">
                  <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="space-y-3">
                    <div className="rounded border border-border bg-muted/30 p-3 space-y-2">
                      <div className="flex items-center justify-between">
                        <h4 className="font-mono text-[10px] font-medium uppercase tracking-wider text-muted-foreground">
                          Analyst Note
                        </h4>
                        <span className={cn(
                          "rounded border px-1.5 py-0.5 font-mono text-[9px] uppercase",
                          analysis.llm_used
                            ? "border-blue-500/30 bg-blue-500/10 text-blue-600"
                            : "border-zinc-500/30 bg-zinc-500/10 text-zinc-500"
                        )}>
                          {analysis.llm_used ? "LLM · Llama-3.1-70B" : "Template"}
                        </span>
                      </div>
                      <p className="text-xs leading-relaxed text-foreground">{analysis.analyst_note}</p>
                    </div>

                    <div className="rounded border border-border bg-muted/30 p-3 space-y-1.5">
                      <h4 className="font-mono text-[10px] font-medium uppercase tracking-wider text-muted-foreground">
                        Scoring
                      </h4>
                      <p className="font-mono text-xs text-foreground">{analysis.scoring_mode}</p>
                      <p className="font-mono text-[10px] text-muted-foreground">
                        Score {analysis.score.toFixed(4)} / Threshold {analysis.threshold}
                      </p>
                    </div>

                    <div className="rounded border border-border bg-muted/30 p-3 space-y-1.5">
                      <h4 className="font-mono text-[10px] font-medium uppercase tracking-wider text-muted-foreground">
                        Baseline Context
                      </h4>
                      {Object.entries(analysis.baseline_context).map(([k, v]) => (
                        <div key={k} className="flex justify-between">
                          <span className="font-mono text-[10px] text-muted-foreground">{k.replace(/_/g, " ")}</span>
                          <span className="font-mono text-[10px] text-foreground">{String(v)}</span>
                        </div>
                      ))}
                    </div>
                  </motion.div>
                </TabsContent>

                {/* JSON */}
                <TabsContent value="json" className="m-0 mt-0">
                  <div className="max-h-[500px] overflow-auto rounded border border-zinc-800 bg-zinc-950">
                    <motion.pre
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      className="p-3 font-mono text-[11px] leading-relaxed text-zinc-300"
                    >
                      {JSON.stringify(result, null, 2)}
                    </motion.pre>
                  </div>
                </TabsContent>
              </div>
            </Tabs>
          </CardContent>
        </Card>
      )}

      {/* Network Agent Test */}
      <NetworkAgentTest />
    </div>
  )
}
