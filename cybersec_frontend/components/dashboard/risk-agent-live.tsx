"use client"

import { useState, useEffect, useCallback } from "react"
import { motion, AnimatePresence } from "framer-motion"
import { cn } from "@/lib/utils"
import { Card, CardContent, CardHeader } from "@/components/ui/card"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Button } from "@/components/ui/button"
import { ScrollArea } from "@/components/ui/scroll-area"
import {
  analyzeEvent,
  getSampleEvents,
  type DecisionOutput,
  type AnomalyEvent,
} from "@/lib/api"
import {
  Play,
  Loader2,
  AlertTriangle,
  CheckCircle2,
  ShieldAlert,
  Eye,
  ShieldOff,
  ShieldCheck,
} from "lucide-react"
import { usePipeline } from "@/lib/pipeline-store"

interface RiskAgentLiveOutputProps {
  agentSlug: string
  onLog?: (log: { type: "info" | "success" | "error" | "warning"; message: string }) => void
  onAnalysisComplete?: (result: { timeTakenMs: number; isAlert: boolean }) => void
  pipelineActive?: boolean
}

// Map decision strings to display config
const decisionConfig: Record<string, { icon: typeof CheckCircle2; color: string; label: string }> = {
  ALLOW: { icon: ShieldCheck, color: "text-emerald-500", label: "ALLOW" },
  MONITOR: { icon: Eye, color: "text-amber-500", label: "MONITOR" },
  ESCALATE: { icon: ShieldAlert, color: "text-orange-500", label: "ESCALATE" },
  BLOCK: { icon: ShieldOff, color: "text-red-500", label: "BLOCK" },
}

const riskLevelColors: Record<string, string> = {
  LOW: "text-emerald-500 border-emerald-500/30 bg-emerald-500/10",
  MEDIUM: "text-amber-500 border-amber-500/30 bg-amber-500/10",
  HIGH: "text-red-500 border-red-500/30 bg-red-500/10",
}

export function RiskAgentLiveOutput({ agentSlug, onLog, onAnalysisComplete, pipelineActive }: RiskAgentLiveOutputProps) {
  const [activeTab, setActiveTab] = useState("summary")
  const [decision, setDecision] = useState<DecisionOutput | null>(null)
  const [sampleEvents, setSampleEvents] = useState<AnomalyEvent[]>([])
  const [selectedEventIndex, setSelectedEventIndex] = useState(0)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Only activate for the risk agent
  const isRiskAgent = agentSlug === "risk-behavior-agent"

  // Hook into the global pipeline store to grab the result if the pipeline just ran
  const pipeline = usePipeline()
  const pipelineDecision = pipeline.pipelineResult?.riskResult

  // If pipeline produced a decision, surface it here
  useEffect(() => {
    if (!isRiskAgent) return
    if (pipelineDecision) {
      setDecision(pipelineDecision)
      setActiveTab("summary")
    }
  }, [isRiskAgent, pipelineDecision])

  // Load sample events on mount
  useEffect(() => {
    if (!isRiskAgent) return
    getSampleEvents()
      .then((res) => {
        setSampleEvents(res.events || [])
        addLog("info", `Loaded ${res.events?.length || 0} sample events from backend`)
      })
      .catch((err) => {
        addLog("error", `Failed to load sample events: ${err.message}`)
      })
  }, [isRiskAgent])

  const addLog = useCallback((type: "info" | "success" | "error" | "warning", message: string) => {
    if (onLog) {
      onLog({ type, message })
    }
  }, [onLog])

  const handleAnalyze = async () => {
    if (sampleEvents.length === 0) {
      setError("No sample events available")
      return
    }

    const event = sampleEvents[selectedEventIndex]
    setLoading(true)
    setError(null)
    setDecision(null)

    addLog("info", `INIT Analyzing event ${event.event_id}`)
    addLog("info", `USER ${event.user_id} | SCORE ${event.score}`)
    addLog("info", `RULES ${event.triggered_rules?.join(", ") || "none"}`)

    try {
      addLog("info", "SEND POST /api/v1/risk-decision/analyze/")
      const startTime = performance.now()
      const result = await analyzeEvent(event)
      const timeTakenMs = Math.round(performance.now() - startTime)
      
      if (result.execution_logs && result.execution_logs.length > 0) {
        result.execution_logs.forEach(log => {
          const cleanLog = log.replace(/\n===.*?===\n/, '').trim();
          if (cleanLog) {
            const isTool = cleanLog.includes('[Tool]') || cleanLog.includes('[ReAct]');
            addLog(isTool ? 'info' : 'warning', cleanLog);
          }
        });
      }

      setDecision(result)
      addLog("success", `DONE risk_level=${result.risk_level} decision=${result.decision} in ${timeTakenMs}ms`)
      addLog("success", `SCORE base=${result.base_score} adjusted=${result.adjusted_risk_score}`)
      addLog("info", `METHOD ${result.computation_method || "llm"} llm_driven=${result.llm_driven}`)
      setActiveTab("summary")
      
      if (onAnalysisComplete) {
        onAnalysisComplete({
          timeTakenMs,
          isAlert: result.risk_level === "HIGH" || result.decision === "ESCALATE" || result.decision === "BLOCK"
        })
      }
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Unknown error"
      setError(msg)
      addLog("error", `FAIL ${msg}`)
    } finally {
      setLoading(false)
    }
  }

  if (!isRiskAgent) return null

  const dc = decision ? (decisionConfig[decision.decision] || decisionConfig.MONITOR) : null
  const rlColor = decision ? (riskLevelColors[decision.risk_level] || riskLevelColors.MEDIUM) : ""

  return (
    <div className="flex h-full flex-col gap-4">
      {/* Controls */}
      {!pipelineDecision && (
      <Card className="shrink-0 rounded border-border">
        <CardHeader className="p-3">
          <div className="flex items-center justify-between">
            <span className="font-mono text-[10px] font-medium uppercase tracking-wider text-muted-foreground">
              Live Analysis
            </span>
            <span className="rounded border border-blue-500/30 bg-blue-500/10 px-1.5 py-0.5 font-mono text-[9px] font-medium uppercase text-blue-600">
              Backend Connected
            </span>
          </div>
        </CardHeader>
        <CardContent className="space-y-3 p-3 pt-0">
          {/* Pipeline active banner */}
          {pipelineActive ? (
            <div className="flex items-center gap-2 rounded border border-blue-500/30 bg-blue-500/10 p-2">
              <span className="relative flex h-2 w-2">
                <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-blue-400 opacity-75" />
                <span className="relative inline-flex h-2 w-2 rounded-full bg-blue-500" />
              </span>
              <span className="font-mono text-[11px] text-blue-500">Running via pipeline — check logs panel for real-time updates</span>
            </div>
          ) : (
            <div className="flex items-center gap-2 rounded border border-border bg-card p-2 text-muted-foreground">
              <span className="font-mono text-[11px]">Waiting for pipeline to run... (Start it from the Overview page)</span>
            </div>
          )}
        </CardContent>
      </Card>
      )}

      {/* Decision Result */}
      {decision && (
        <Card className="flex flex-1 flex-col overflow-hidden rounded border-border">
          <CardHeader className="shrink-0 border-b border-border p-3">
            <div className="flex items-center justify-between">
              <span className="font-mono text-[10px] font-medium uppercase tracking-wider text-muted-foreground">
                Decision Result
              </span>
              <div className="flex items-center gap-2">
                <span className={cn("rounded border px-1.5 py-0.5 font-mono text-[9px] font-bold uppercase", rlColor)}>
                  {decision.risk_level}
                </span>
                {dc && (
                  <span className={cn("flex items-center gap-1 font-mono text-[10px] font-semibold", dc.color)}>
                    <dc.icon className="h-3.5 w-3.5" />
                    {dc.label}
                  </span>
                )}
              </div>
            </div>
          </CardHeader>

          <CardContent className="flex-1 overflow-hidden p-0">
            <Tabs value={activeTab} onValueChange={setActiveTab} className="flex h-full flex-col">
              <TabsList className="mx-3 mt-3 h-7 w-fit shrink-0 rounded border border-border bg-muted/50 p-0.5">
                <TabsTrigger value="summary" className="h-6 rounded px-2 font-mono text-[10px] uppercase tracking-wider">
                  Summary
                </TabsTrigger>
                <TabsTrigger value="json" className="h-6 rounded px-2 font-mono text-[10px] uppercase tracking-wider">
                  JSON
                </TabsTrigger>
                <TabsTrigger value="details" className="h-6 rounded px-2 font-mono text-[10px] uppercase tracking-wider">
                  Details
                </TabsTrigger>
              </TabsList>

              <div className="flex-1 overflow-auto p-3">
                <TabsContent value="summary" className="m-0 h-full">
                  <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="space-y-4">
                    {/* Key Metrics */}
                    <div className="space-y-2 rounded border border-border bg-muted/30 p-3">
                      <h4 className="font-mono text-[10px] font-medium uppercase tracking-wider text-muted-foreground">
                        Key Metrics
                      </h4>
                      <div className="grid grid-cols-2 gap-2">
                        <div className="rounded border border-border bg-card p-2">
                          <p className="font-mono text-[9px] uppercase tracking-wider text-muted-foreground">Decision</p>
                          <p className={cn("mt-0.5 font-mono text-sm font-semibold uppercase", dc?.color)}>{decision.decision}</p>
                        </div>
                        <div className="rounded border border-border bg-card p-2">
                          <p className="font-mono text-[9px] uppercase tracking-wider text-muted-foreground">Risk Score</p>
                          <p className={cn("mt-0.5 font-mono text-sm font-semibold", rlColor.split(" ")[0])}>{decision.adjusted_risk_score.toFixed(2)}</p>
                        </div>
                        <div className="rounded border border-border bg-card p-2">
                          <p className="font-mono text-[9px] uppercase tracking-wider text-muted-foreground">User ID</p>
                          <p className="mt-0.5 font-mono text-sm font-semibold text-blue-500">{decision.user_id}</p>
                        </div>
                        <div className="rounded border border-border bg-card p-2">
                          <p className="font-mono text-[9px] uppercase tracking-wider text-muted-foreground">Event ID</p>
                          <p className="mt-0.5 font-mono text-sm font-semibold text-blue-500">{decision.event_id}</p>
                        </div>
                      </div>
                    </div>
                  </motion.div>
                </TabsContent>

                <TabsContent value="json" className="m-0 h-full">
                  <div className="h-[280px] overflow-auto rounded border border-zinc-800 bg-zinc-950">
                    <motion.pre
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      className="p-3 font-mono text-[11px] leading-relaxed text-zinc-300"
                    >
                      {JSON.stringify({
                        ...decision,
                        base_score_analysis: undefined,
                        adjustment_reasoning: undefined,
                        decision_reasoning: undefined,
                      }, null, 2)}
                    </motion.pre>
                  </div>
                </TabsContent>

                <TabsContent value="details" className="m-0 h-full">
                  <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="space-y-4">
                    <div className="space-y-1.5 rounded border border-border bg-muted/30 p-3">
                      <h4 className="font-mono text-[10px] font-medium uppercase tracking-wider text-muted-foreground">Base Score Analysis</h4>
                      <p className="text-xs leading-relaxed text-muted-foreground">{decision.base_score_analysis || "N/A"}</p>
                    </div>
                    {decision.adjustment_reasoning && (
                      <div className="space-y-1.5 rounded border border-border bg-muted/30 p-3">
                        <h4 className="font-mono text-[10px] font-medium uppercase tracking-wider text-muted-foreground">Adjustment Reasoning</h4>
                        <p className="text-xs leading-relaxed text-muted-foreground">{decision.adjustment_reasoning}</p>
                      </div>
                    )}
                    {decision.decision_reasoning && (
                      <div className="space-y-1.5 rounded border border-border bg-muted/30 p-3">
                        <h4 className="font-mono text-[10px] font-medium uppercase tracking-wider text-muted-foreground">Decision Reasoning</h4>
                        <p className="text-xs leading-relaxed text-muted-foreground">{decision.decision_reasoning}</p>
                      </div>
                    )}
                  </motion.div>
                </TabsContent>
              </div>
            </Tabs>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
