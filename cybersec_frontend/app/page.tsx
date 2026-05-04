"use client"

import { useState, useEffect } from "react"
import { motion } from "framer-motion"
import { cn } from "@/lib/utils"
import { PipelineVisualization, type PipelineSource } from "@/components/dashboard/pipeline-visualization"
import { StatsCards } from "@/components/dashboard/stats-cards"
import { Card, CardContent, CardHeader } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Play, Loader2, Database, Swords } from "lucide-react"
import { getSampleBehaviorSessions, scoreBehaviorSession, analyzeEvent, pipelineCollectData, simulateAttack, getAttackerStats, getAttackHistory, getAttackerBehaviorResult, getAttackerLogs } from "@/lib/api"
import type { SessionInput, BehaviorAnomalyResult, DecisionOutput, DataCollectionResult } from "@/lib/api"
import { RefreshCw } from "lucide-react"
import type { AgentStatus } from "@/lib/mock-data"
import { usePipeline } from "@/lib/pipeline-store"

export default function HomePage() {
  // ─── Global pipeline store ──────────────────────────────────────
  const pipeline = usePipeline()
  const { agentStatuses, pipelineRunning, pipelineResult } = pipeline
  const setAgentStatuses = pipeline.setAgentStatuses
  const setPipelineResult = pipeline.setPipelineResult
  
  // Debug: Log when pipelineResult changes
  useEffect(() => {
    console.log('[DEBUG] pipelineResult changed:', pipelineResult)
  }, [pipelineResult])
  
  // Session selection state
  const [sessions, setSessions] = useState<SessionInput[]>([])
  const [selectedSessionIdx, setSelectedSessionIdx] = useState(0)
  const [loadingSessions, setLoadingSessions] = useState(false)
  const [flaggedOnly, setFlaggedOnly] = useState(false)
  
  // Pipeline mode: 'real' or 'test'
  const [pipelineMode, setPipelineMode] = useState<'real' | 'test'>('test')
  
  // Pipeline source: which agent starts the pipeline
  const [pipelineSource, setPipelineSource] = useState<PipelineSource>('data-agent')
  
  // Attacker pipeline result
  const [attackerResult, setAttackerResult] = useState<{
    attack_name?: string
    events_generated?: number
    severity?: string
    mitre_technique?: string
  } | null>(null)

  // Helper function to build session labels
  const sessionLabel = (s: SessionInput, i: number): string => {
    const signals: string[] = []
    if (s.visited_exfil_domain) signals.push("exfil")
    if (s.usb_connected) signals.push("USB")
    if (s.has_ext_email) signals.push("ext-email")
    if (s.is_outside_hours) signals.push("after-hours")
    if (s.visited_jobsearch_domain) signals.push("job-search")
    const tag = signals.length ? `[${signals.join(",")}]` : "[normal]"
    return `#${i + 1} ${s.user_id} · ${s.session_start?.slice(0, 10) ?? ""} ${tag}`
  }

  // Load sessions function
  const loadSessions = async (flagged: boolean) => {
    setLoadingSessions(true)
    try {
      const res = await getSampleBehaviorSessions(30, flagged)
      setSessions(res.sessions)
      setSelectedSessionIdx(0)
    } catch (error) {
      console.error("Failed to load sessions:", error)
      alert(`Failed to load sessions: ${error instanceof Error ? error.message : 'Unknown error'}`)
    } finally {
      setLoadingSessions(false)
    }
  }

  // Load sessions on component mount
  useEffect(() => {
    loadSessions(false)
  }, [])

  const handleToggleFlagged = () => {
    const next = !flaggedOnly
    setFlaggedOnly(next)
    loadSessions(next)
  }

  // Helper function to check if LLM detected a threat
  const checkLLMThreatDetection = (behaviorResult: BehaviorAnomalyResult): boolean => {
    const analystNote = behaviorResult.detection_agent_analysis?.analyst_note?.toLowerCase() || ""
    const threatKeywords = [
      'threat', 'suspicious', 'malicious', 'attack', 'breach', 'compromise',
      'exfiltration', 'infiltration', 'unauthorized', 'anomalous behavior',
      'security risk', 'potential threat', 'concerning', 'unusual activity'
    ]
    return threatKeywords.some(keyword => analystNote.includes(keyword))
  }

  // Helper: run behavior + risk analysis on a BehaviorAnomalyResult
  const runDownstreamAgents = async (behaviorResult: BehaviorAnomalyResult): Promise<DecisionOutput | undefined> => {
    // Behavior agent complete, risk agent active
    setAgentStatuses(prev => ({
      ...prev,
      'behavior-agent': 'completed',
      'risk-behavior-agent': 'processing'
    }))

    let riskResult: DecisionOutput | undefined

    pipeline.addLog('risk-behavior-agent', { type: 'info', message: `Analyzing event ${behaviorResult.event_id} (score: ${behaviorResult.combined_score.toFixed(4)})...` })
    try {
      const priority = behaviorResult.flagged ? 'HIGH_PRIORITY' : 'MEDIUM_PRIORITY'
      pipeline.addLog('risk-behavior-agent', { type: 'info', message: `Priority: ${priority} | User: ${behaviorResult.user_id}` })
      const anomalyEvent = {
        event_id: behaviorResult.event_id,
        user_id: behaviorResult.user_id,
        timestamp: behaviorResult.timestamp,
        score: behaviorResult.combined_score,
        combined_score: behaviorResult.combined_score,
        if_score: behaviorResult.if_score,
        dimension_scores: behaviorResult.dimension_scores,
        triggered_rules: behaviorResult.triggered_rules,
        confidence: behaviorResult.confidence,
        cold_start: behaviorResult.cold_start,
        simulated: behaviorResult.simulated,
        monitor: 'A',
        threat_classification: priority
      }
      riskResult = await analyzeEvent(anomalyEvent)
      
      if (riskResult.execution_logs && riskResult.execution_logs.length > 0) {
        riskResult.execution_logs.forEach(log => {
          const cleanLog = log.replace(/\n===.*?===\n/, '').trim();
          if (cleanLog) {
            const isTool = cleanLog.includes('[Tool]') || cleanLog.includes('[ReAct]');
            pipeline.addLog('risk-behavior-agent', { 
              type: isTool ? 'info' : 'warning', 
              message: cleanLog 
            })
          }
        });
      }

      pipeline.addLog('risk-behavior-agent', { type: 'success', message: `Decision: ${riskResult.decision} | Risk Level: ${riskResult.risk_level} | Score: ${riskResult.adjusted_risk_score.toFixed(2)}` })
      setAgentStatuses(prev => ({ ...prev, 'risk-behavior-agent': 'completed' }))
    } catch (riskError) {
      console.warn("Risk agent analysis failed:", riskError)
      pipeline.addLog('risk-behavior-agent', { type: 'error', message: `Analysis failed: ${riskError instanceof Error ? riskError.message : 'Unknown'}` })
      setAgentStatuses(prev => ({ ...prev, 'risk-behavior-agent': 'alert' }))
    }

    return riskResult
  }

  // Helper: poll attacker stats until simulation finishes (max 120s)
  // Also polls attacker logs and pushes them into the pipeline store
  const waitForAttackerSimulation = async (): Promise<void> => {
    const maxWait = 120_000
    const interval = 3_000
    let elapsed = 0
    let lastLogTimestamp: string | null = null
    
    while (elapsed < maxWait) {
      await new Promise(r => setTimeout(r, interval))
      elapsed += interval
      try {
        // Poll logs and push to pipeline store
        const logsRes = await getAttackerLogs(50)
        if (logsRes.ok && logsRes.logs.length > 0) {
          const newLogs = lastLogTimestamp 
            ? logsRes.logs.filter(log => log.timestamp > lastLogTimestamp!)
            : logsRes.logs
          newLogs.forEach(log => {
            const logType = log.level === 'ERROR' ? 'error' : 
                           log.level === 'WARNING' ? 'warning' : 'info'
            pipeline.addLog('attacker-agent', { type: logType as "info" | "error" | "warning", message: log.message })
          })
          if (logsRes.logs.length > 0) {
            lastLogTimestamp = logsRes.logs[logsRes.logs.length - 1].timestamp
          }
        }
        
        const stats = await getAttackerStats()
        if (!stats.simulating) return
      } catch { /* ignore */ }
    }
    throw new Error("Attack simulation timed out after 120s")
  }

  const runPipelineTest = async () => {
    setPipelineResult(null)
    setAttackerResult(null)
    pipeline.clearAllLogs()

    // Determine which agents will be part of this pipeline run
    const pipelineAgentList = pipelineSource === 'attacker-agent'
      ? ['attacker-agent', 'behavior-agent', 'risk-behavior-agent']
      : ['data-agent', 'behavior-agent', 'risk-behavior-agent']
    pipeline.startPipeline(pipelineAgentList)

    const resetStatuses: Record<string, AgentStatus> = {
      'data-agent': 'idle',
      'attacker-agent': 'idle',
      'behavior-agent': 'idle',
      'risk-behavior-agent': 'idle',
      'response-agent': 'idle',
      'reporting-agent': 'idle'
    }

    try {
      if (pipelineSource === 'attacker-agent') {
        // ── ATTACKER AGENT PIPELINE (A2A) ────────────────────────
        setAgentStatuses({ ...resetStatuses, 'attacker-agent': 'processing' })
        pipeline.addLog('attacker-agent', { type: 'info', message: '🎯 Starting attack simulation (5-phase cycle)...' })

        const simResult = await simulateAttack()
        if (!simResult.ok) {
          pipeline.addLog('attacker-agent', { type: 'error', message: `❌ Attack simulation failed: ${simResult.error || 'Unknown error'}` })
          alert(`Attack simulation failed: ${simResult.error || 'Unknown error'}`)
          setAgentStatuses({ ...resetStatuses, 'attacker-agent': 'alert' })
          return
        }
        pipeline.addLog('attacker-agent', { type: 'success', message: '✅ Attack simulation triggered — running 5 phases...' })

        await waitForAttackerSimulation()
        pipeline.addLog('attacker-agent', { type: 'success', message: '✅ Attack simulation completed' })

        const historyRes = await getAttackHistory(1)
        const latestAttack = historyRes.attacks?.[0]
        setAttackerResult(latestAttack ? {
          attack_name: latestAttack.attack_name,
          events_generated: latestAttack.event_count,
          severity: latestAttack.severity,
          mitre_technique: latestAttack.mitre_technique,
        } : null)
        if (latestAttack) {
          pipeline.addLog('attacker-agent', { type: 'info', message: `Attack: ${latestAttack.attack_name} | Events: ${latestAttack.event_count} | Severity: ${latestAttack.severity}` })
        }

        setAgentStatuses(prev => ({
          ...prev,
          'attacker-agent': 'completed',
          'behavior-agent': 'processing'
        }))
        pipeline.addLog('behavior-agent', { type: 'info', message: 'Receiving forwarded attack events via A2A protocol...' })

        const a2aResult = await getAttackerBehaviorResult()

        if (a2aResult.ok && a2aResult.behavior_result?.ok) {
          const firstResult = a2aResult.behavior_result.results.find(
            (r: { ok: boolean; anomaly_result?: BehaviorAnomalyResult }) => r.ok && r.anomaly_result
          )

          if (firstResult?.anomaly_result) {
            const behaviorResult = firstResult.anomaly_result
            pipeline.addLog('behavior-agent', { type: 'success', message: `Anomaly score: ${behaviorResult.combined_score.toFixed(4)} | Verdict: ${behaviorResult.detection_agent_analysis.verdict}` })
            pipeline.addLog('behavior-agent', { type: behaviorResult.flagged ? 'warning' : 'success', message: `Flagged: ${behaviorResult.flagged} | Confidence: ${behaviorResult.confidence}` })

            const riskResult = await runDownstreamAgents(behaviorResult)

            const displaySession: SessionInput = {
              user_id: behaviorResult.user_id,
              pc: 'attacker_sim',
              session_start: behaviorResult.timestamp,
              hour_of_day: new Date(behaviorResult.timestamp).getHours(),
              is_weekend: 0, is_outside_hours: 1, duration_minutes: 45,
              file_count: latestAttack?.event_count || 0, max_sensitivity: 2,
              usb_connected: 1, usb_first_time: 0, email_count: 0,
              has_ext_email: 0, visited_exfil_domain: 0,
              visited_jobsearch_domain: 0, simulated: true
            }

            setPipelineResult({ session: displaySession, behaviorResult, riskResult })
          } else {
            setAgentStatuses(prev => ({ ...prev, 'behavior-agent': 'completed', 'risk-behavior-agent': 'completed' }))
            pipeline.addLog('behavior-agent', { type: 'warning', message: `No scorable sessions (${a2aResult.behavior_result.skipped_count} skipped)` })
            alert(`A2A forwarding complete but no scorable sessions (${a2aResult.behavior_result.skipped_count} skipped — no baselines)`)
          }
        } else {
          setAgentStatuses(prev => ({ ...prev, 'behavior-agent': 'alert' }))
          pipeline.addLog('behavior-agent', { type: 'error', message: `A2A analysis failed: ${a2aResult.error || a2aResult.behavior_result?.error || 'No result'}` })
          alert(`A2A behavior analysis: ${a2aResult.error || a2aResult.behavior_result?.error || 'No result available'}`)
        }

      } else {
        // ── DATA AGENT PIPELINE ──────────────────────────────────
        setAgentStatuses({ ...resetStatuses, 'data-agent': 'processing' })
        pipeline.addLog('data-agent', { type: 'info', message: `Starting data pipeline (mode: ${pipelineMode})...` })

        if (pipelineMode === 'real') {
          pipeline.addLog('data-agent', { type: 'info', message: 'Collecting real security events from data sources...' })
          
          // Use SSE streaming to get real-time logs into global pipeline store
          const dataResult = await (async () => {
            const response = await fetch('http://localhost:8000/api/v1/data/collect-stream/', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ collectors: [] })
            })
            if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`)
            const reader = response.body?.getReader()
            const decoder = new TextDecoder()
            if (!reader) throw new Error('Response body is not readable')
            
            let buffer = ''
            let finalResult: any = null
            while (true) {
              const { done, value } = await reader.read()
              if (done) break
              buffer += decoder.decode(value, { stream: true })
              const messages = buffer.split('\n\n')
              buffer = messages.pop() || ''
              for (const message of messages) {
                if (!message.trim() || !message.startsWith('data: ')) continue
                try {
                  const data = JSON.parse(message.replace('data: ', ''))
                  if (data.type === 'complete') {
                    finalResult = data.result
                  } else {
                    const isBrowserTimeout = data.message?.includes('collect_browser_events') && 
                                             (data.message?.includes('timed out') || data.message?.includes('timeout'))
                    if (!isBrowserTimeout) {
                      pipeline.addLog('data-agent', { 
                        type: data.type as "info" | "success" | "error" | "warning", 
                        message: data.message 
                      })
                    }
                  }
                } catch (e) { console.error('SSE parse error:', e) }
              }
            }
            return finalResult as DataCollectionResult
          })()

          setAgentStatuses(prev => ({ ...prev, 'data-agent': 'completed', 'behavior-agent': 'processing' }))
          
          // Handle case where SSE stream didn't return a result
          if (!dataResult) {
            console.error('[DEBUG] dataResult is null/undefined')
            pipeline.addLog('data-agent', { type: 'error', message: 'No result returned from data collection stream' })
            alert('Data collection failed: No result returned from stream')
            setAgentStatuses({ ...resetStatuses, 'data-agent': 'alert' })
            return
          }
          
          console.log('[DEBUG] dataResult:', dataResult)
          console.log('[DEBUG] behavior_result:', dataResult.behavior_result)
          
          pipeline.addLog('data-agent', { type: 'success', message: `Data collection complete: ${dataResult.total_events || 0} events` })

          if (!dataResult.ok) {
            console.error('[DEBUG] dataResult.ok is false')
            pipeline.addLog('data-agent', { type: 'error', message: `Collection failed: ${dataResult.errors?.join(', ') || 'Unknown'}` })
            alert(`Data collection failed: ${dataResult.errors?.join(', ') || 'Unknown error'}`)
            setAgentStatuses({ ...resetStatuses, 'data-agent': 'alert' })
            return
          }

          pipeline.addLog('behavior-agent', { type: 'info', message: 'Analyzing collected events for anomalies...' })

          // Check if behavior_result exists and has results
          if (!dataResult.behavior_result) {
            console.error('[DEBUG] behavior_result is missing')
            pipeline.addLog('behavior-agent', { type: 'error', message: 'No behavior result returned' })
            alert('Behavior analysis failed: No result returned')
            setAgentStatuses(prev => ({ ...prev, 'behavior-agent': 'alert' }))
            return
          }

          console.log('[DEBUG] behavior_result.ok:', dataResult.behavior_result.ok)
          console.log('[DEBUG] behavior_result.results:', dataResult.behavior_result.results)

          // Log if there was an error but continue if we have results
          if (!dataResult.behavior_result.ok) {
            console.warn('[DEBUG] behavior_result.ok is false, error:', dataResult.behavior_result.error)
            pipeline.addLog('behavior-agent', { type: 'warning', message: `Analysis completed with issues: ${dataResult.behavior_result.error || 'Unknown'}` })
          }

          // Try to get results even if ok is false (might have partial results)
          const firstResult = dataResult.behavior_result.results?.find(r => r.ok && r.anomaly_result)
          console.log('[DEBUG] firstResult:', firstResult)
          
          if (!firstResult || !firstResult.anomaly_result) {
            console.warn('[DEBUG] No valid anomaly result found, creating placeholder')
            // Show more detailed error message
            const sessionsInfo = dataResult.sessions_created ? `${dataResult.sessions_created} sessions created, ` : ''
            const sentInfo = dataResult.behavior_result.sessions_sent ? `${dataResult.behavior_result.sessions_sent} sent, ` : ''
            const errorInfo = dataResult.behavior_result.error || 'No results available'
            
            pipeline.addLog('behavior-agent', { type: 'warning', message: `No scorable results: ${sessionsInfo}${sentInfo}${errorInfo}` })
            
            // Still show a summary card even without full results
            const summarySession: SessionInput = {
              user_id: 'N/A',
              pc: 'collected_data',
              session_start: new Date().toISOString(),
              hour_of_day: 0,
              is_weekend: 0,
              is_outside_hours: 0,
              duration_minutes: 0,
              file_count: dataResult.total_events || 0,
              max_sensitivity: 0,
              usb_connected: 0,
              usb_first_time: 0,
              email_count: 0,
              has_ext_email: 0,
              visited_exfil_domain: 0,
              visited_jobsearch_domain: 0,
              simulated: false
            }
            
            const placeholderResult: BehaviorAnomalyResult = {
              event_id: 'N/A',
              timestamp: new Date().toISOString(),
              source: ['data_agent'],
              user_anomaly_score: 0,
              network_anomaly_score: null,
              combined_score: 0,
              user_id: 'N/A',
              entity_id: null,
              dimension_scores: { time: 0, device: 0, volume: 0, sensitivity: 0 },
              triggered_rules: [],
              network_attack_category: null,
              correlation: {},
              explanation: `Pipeline completed but analysis unavailable: ${errorInfo}`,
              baseline_age_days: 0,
              confidence: 'low',
              cold_start: true,
              simulated: false,
              flagged: false,
              if_score: 0,
              detection_agent_analysis: {
                model: 'N/A',
                llm_used: false,
                analyst_note: `Analysis could not be completed. ${sessionsInfo}${sentInfo}Error: ${errorInfo}. This may be due to missing baseline data or timeout issues.`,
                scoring_mode: 'N/A',
                score: 0,
                threshold: 0,
                verdict: 'INCOMPLETE',
                triggered_signals: [],
                dimension_breakdown: { time: 0, device: 0, volume: 0, sensitivity: 0 },
                session_summary: {},
                baseline_context: {}
              }
            }
            
            console.log('[DEBUG] Setting placeholder pipelineResult')
            setPipelineResult({ session: summarySession, behaviorResult: placeholderResult })
            setAgentStatuses(prev => ({ ...prev, 'behavior-agent': 'alert', 'risk-behavior-agent': 'idle' }))
            return
          }

          console.log('[DEBUG] Found valid result, processing...')
          const behaviorResult = firstResult.anomaly_result
          pipeline.addLog('behavior-agent', { type: 'success', message: `Score: ${behaviorResult.combined_score.toFixed(4)} | Verdict: ${behaviorResult.detection_agent_analysis.verdict}` })
          const riskResult = await runDownstreamAgents(behaviorResult)

          const dummySession: SessionInput = {
            user_id: behaviorResult.user_id, pc: 'collected_data',
            session_start: behaviorResult.timestamp,
            hour_of_day: new Date(behaviorResult.timestamp).getHours(),
            is_weekend: 0, is_outside_hours: 0, duration_minutes: 60,
            file_count: 0, max_sensitivity: 0, usb_connected: 0,
            usb_first_time: 0, email_count: 0, has_ext_email: 0,
            visited_exfil_domain: 0, visited_jobsearch_domain: 0, simulated: false
          }

          console.log('[DEBUG] Setting real pipelineResult')
          setPipelineResult({ session: dummySession, behaviorResult, riskResult })

        } else {
          // TEST SESSION MODE
          if (sessions.length === 0) {
            alert("No test sessions loaded. Please wait for sessions to load or refresh.")
            setAgentStatuses(resetStatuses)
            return
          }

          const session = sessions[selectedSessionIdx]
          pipeline.addLog('data-agent', { type: 'info', message: `Loading test session: ${session.user_id} @ ${session.session_start?.slice(0, 16)}` })
          pipeline.addLog('data-agent', { type: 'success', message: 'Test session loaded successfully' })
          setAgentStatuses(prev => ({ ...prev, 'data-agent': 'completed', 'behavior-agent': 'processing' }))

          pipeline.addLog('behavior-agent', { type: 'info', message: `Scoring session for ${session.user_id}...` })
          const behaviorResult = await scoreBehaviorSession(session)
          pipeline.addLog('behavior-agent', { type: 'success', message: `Score: ${behaviorResult.combined_score.toFixed(4)} | Verdict: ${behaviorResult.detection_agent_analysis.verdict}` })
          pipeline.addLog('behavior-agent', { type: behaviorResult.flagged ? 'warning' : 'success', message: `Flagged: ${behaviorResult.flagged} | Confidence: ${behaviorResult.confidence}` })

          const riskResult = await runDownstreamAgents(behaviorResult)

          setPipelineResult({ session, behaviorResult, riskResult })
        }
      }

    } catch (error) {
      console.error("Pipeline test failed:", error)
      const errMsg = error instanceof Error ? error.message : 'Unknown error'
      alert(`Pipeline test failed: ${errMsg}`)
      // Log the error to whichever agent was processing
      const processingAgent = Object.entries(agentStatuses).find(([, s]) => s === 'processing')?.[0]
      if (processingAgent) {
        pipeline.addLog(processingAgent, { type: 'error', message: `Pipeline failed: ${errMsg}` })
      }
      setAgentStatuses(prev => {
        const keys = Object.keys(prev) as Array<keyof typeof prev>
        const pa = keys.find(k => prev[k] === 'processing')
        if (pa) {
          return { ...prev, [pa]: 'alert' }
        }
        return prev
      })
    } finally {
      pipeline.stopPipeline()
    }
  }
  return (
    <div className="p-4">
      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: -10 }}
        animate={{ opacity: 1, y: 0 }}
        className="mb-4"
      >
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-lg font-semibold text-foreground">
              Pipeline Overview
            </h1>
            <p className="font-mono text-[10px] uppercase tracking-wider text-muted-foreground">
              Multi-agent security monitoring system
            </p>
          </div>
          <div className="flex items-center gap-2 rounded border border-border bg-muted/50 px-2 py-1">
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
            <span className="font-mono text-[10px] font-medium text-emerald-600">ALL SYSTEMS OPERATIONAL</span>
          </div>
        </div>
      </motion.div>

      {/* Stats Cards */}
      <div className="mb-4">
        <StatsCards />
      </div>

      {/* Pipeline Visualization */}
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1 }}
      >
        <Card className="rounded border-border">
          <CardHeader className="border-b border-border p-3">
            <div className="flex items-center justify-between">
              <span className="font-mono text-[10px] font-medium uppercase tracking-wider text-muted-foreground">
                Agent Pipeline
              </span>
              <span className="font-mono text-[10px] text-muted-foreground">
                Real-time data flow visualization
              </span>
            </div>
          </CardHeader>
          <CardContent className="p-4">
            <div className="space-y-4">
              <PipelineVisualization 
                agentStatuses={agentStatuses} 
                pipelineSource={pipelineSource}
                onSourceChange={(source) => {
                  if (!pipelineRunning) {
                    setPipelineSource(source)
                    setPipelineResult(null)
                    setAttackerResult(null)
                  }
                }}
              />
              
              {/* Session Selection Controls - Only show for data-agent in test mode */}
              {pipelineSource === 'data-agent' && pipelineMode === 'test' && (
                <div className="border-t border-border pt-4 space-y-3">
                  <div className="flex items-center justify-between">
                    <h3 className="font-mono text-xs font-medium uppercase tracking-wider text-foreground">
                      Test Session Selection
                    </h3>
                    <div className="flex items-center gap-2">
                      <button
                        onClick={handleToggleFlagged}
                        className={`rounded border px-1.5 py-0.5 font-mono text-[9px] font-medium uppercase transition-colors ${
                          flaggedOnly
                            ? "border-amber-500/50 bg-amber-500/20 text-amber-600"
                            : "border-border bg-muted/50 text-muted-foreground hover:text-foreground"
                        }`}
                      >
                        {flaggedOnly ? "Anomalous only" : "All sessions"}
                      </button>
                      <button
                        onClick={() => loadSessions(flaggedOnly)}
                        disabled={loadingSessions}
                        className="rounded border border-border bg-muted/50 p-1 text-muted-foreground hover:text-foreground disabled:opacity-50"
                        title="Reload sessions"
                      >
                        <RefreshCw className={`h-3 w-3 ${loadingSessions ? "animate-spin" : ""}`} />
                      </button>
                    </div>
                  </div>

                  {/* Session Selector */}
                  {sessions.length > 0 ? (
                    <div className="space-y-2">
                      <label className="font-mono text-[10px] uppercase tracking-wider text-muted-foreground">
                        Select Session ({sessions.length} loaded from test_sessions.parquet)
                      </label>
                      <select
                        value={selectedSessionIdx}
                        onChange={(e) => { setSelectedSessionIdx(Number(e.target.value)); setPipelineResult(null) }}
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

                  {/* Selected Session Preview */}
                  {sessions.length > 0 && sessions[selectedSessionIdx] && (
                    <div className="grid grid-cols-3 gap-1.5 rounded border border-border bg-muted/30 p-2">
                      {(["hour_of_day", "file_count", "duration_minutes", "usb_connected", "has_ext_email", "visited_exfil_domain", "is_outside_hours", "is_weekend", "max_sensitivity"] as const).map((k) => {
                        const selected = sessions[selectedSessionIdx]
                        return (
                          <div key={k} className="flex flex-col">
                            <span className="font-mono text-[9px] uppercase tracking-wider text-muted-foreground">
                              {k.replace(/_/g, " ")}
                            </span>
                            <span className={`font-mono text-xs font-medium ${
                              (k === "usb_connected" || k === "has_ext_email" || k === "visited_exfil_domain") && selected[k]
                                ? "text-amber-500"
                                : "text-foreground"
                            }`}>
                              {String(selected[k] ?? "—")}
                            </span>
                          </div>
                        )
                      })}
                    </div>
                  )}
                </div>
              )}

              {/* Attacker Agent Info - Show when attacker source selected */}
              {pipelineSource === 'attacker-agent' && (
                <div className="border-t border-border pt-4 space-y-3">
                  <div className="flex items-center gap-2">
                    <Swords className="h-4 w-4 text-red-500" />
                    <h3 className="font-mono text-xs font-medium uppercase tracking-wider text-foreground">
                      Attack Simulation Mode
                    </h3>
                  </div>
                  <p className="font-mono text-[10px] text-muted-foreground leading-relaxed">
                    Runs a single LLM-powered 5-phase attack cycle: <span className="text-red-400">Observe → List → Analyze → Choose → Inject</span>. 
                    Events are stored via MCP, then forwarded to the Behavior Agent via <span className="text-blue-400">A2A protocol</span> for analysis.
                  </p>
                  {attackerResult && (
                    <div className="grid grid-cols-2 gap-2 rounded border border-red-500/20 bg-red-500/5 p-2">
                      <div className="flex flex-col">
                        <span className="font-mono text-[9px] uppercase text-muted-foreground">Attack</span>
                        <span className="font-mono text-xs font-medium text-red-400">{attackerResult.attack_name}</span>
                      </div>
                      <div className="flex flex-col">
                        <span className="font-mono text-[9px] uppercase text-muted-foreground">Events</span>
                        <span className="font-mono text-xs font-medium text-foreground">{attackerResult.events_generated}</span>
                      </div>
                      <div className="flex flex-col">
                        <span className="font-mono text-[9px] uppercase text-muted-foreground">Severity</span>
                        <span className={`font-mono text-xs font-medium ${
                          attackerResult.severity === 'high' ? 'text-red-500' : 
                          attackerResult.severity === 'medium' ? 'text-amber-500' : 'text-blue-500'
                        }`}>{attackerResult.severity?.toUpperCase()}</span>
                      </div>
                      <div className="flex flex-col">
                        <span className="font-mono text-[9px] uppercase text-muted-foreground">MITRE</span>
                        <span className="font-mono text-xs font-medium text-foreground">{attackerResult.mitre_technique}</span>
                      </div>
                    </div>
                  )}
                </div>
              )}
              
              {/* Pipeline Controls */}
              <div className="flex items-center justify-between border-t border-border pt-4">
                <div className="space-y-1">
                  {pipelineSource === 'data-agent' && (
                    <>
                      <h3 className="font-mono text-xs font-medium uppercase tracking-wider text-foreground">
                        Data Agent Mode
                      </h3>
                      <div className="flex items-center gap-2">
                        <button
                          onClick={() => setPipelineMode('test')}
                          className={`rounded border px-2 py-1 font-mono text-[10px] font-medium uppercase transition-colors ${
                            pipelineMode === 'test'
                              ? "border-blue-500/50 bg-blue-500/20 text-blue-600"
                              : "border-border bg-muted/50 text-muted-foreground hover:text-foreground"
                          }`}
                        >
                          Test Sessions
                        </button>
                        <button
                          onClick={() => setPipelineMode('real')}
                          className={`rounded border px-2 py-1 font-mono text-[10px] font-medium uppercase transition-colors ${
                            pipelineMode === 'real'
                              ? "border-emerald-500/50 bg-emerald-500/20 text-emerald-600"
                              : "border-border bg-muted/50 text-muted-foreground hover:text-foreground"
                          }`}
                        >
                          Real Data Collection
                        </button>
                      </div>
                      <p className="font-mono text-[10px] text-muted-foreground">
                        {pipelineMode === 'real' 
                          ? "Data Agent (collect) → Behavior Agent → Risk Agent"
                          : "Test Session → Behavior Agent → Risk Agent (if flagged)"
                        }
                      </p>
                    </>
                  )}
                  {pipelineSource === 'attacker-agent' && (
                    <>
                      <h3 className="font-mono text-xs font-medium uppercase tracking-wider text-foreground">
                        Attacker Pipeline (A2A)
                      </h3>
                      <p className="font-mono text-[10px] text-muted-foreground">
                        Attacker (MCP) → Data Storage → A2A → Behavior Agent → Risk Agent
                      </p>
                    </>
                  )}
                </div>
                <Button
                  onClick={runPipelineTest}
                  disabled={pipelineRunning || (pipelineSource === 'data-agent' && pipelineMode === 'test' && sessions.length === 0)}
                  className={cn(
                    "gap-2 rounded-md text-sm font-medium text-white disabled:opacity-50",
                    pipelineSource === 'attacker-agent'
                      ? "bg-red-600 hover:bg-red-700"
                      : "bg-blue-600 hover:bg-blue-700"
                  )}
                >
                  {pipelineRunning
                    ? <><Loader2 className="h-4 w-4 animate-spin" /><span>Running...</span></>
                    : pipelineSource === 'attacker-agent'
                    ? <><Swords className="h-4 w-4" /><span>Simulate Attack</span></>
                    : <><Play className="h-4 w-4" /><span>Start Pipeline</span></>
                  }
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>
      </motion.div>

      {/* Pipeline Test Results */}
      {pipelineResult && (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          className="mt-4"
        >
          <Card className="rounded border-border">
            <CardHeader className="border-b border-border p-3">
              <div className="flex items-center justify-between">
                <span className="font-mono text-[10px] font-medium uppercase tracking-wider text-muted-foreground">
                  Pipeline Test Results
                </span>
                <div className="flex items-center gap-2">
                  {(() => {
                    const llmThreat = checkLLMThreatDetection(pipelineResult.behaviorResult)
                    const ifFlagged = pipelineResult.behaviorResult.flagged
                    const detectionSource = ifFlagged ? 'IF Model' : llmThreat ? 'LLM Analysis' : 'None'
                    const priority = ifFlagged ? 'HIGH' : llmThreat ? 'MEDIUM' : 'NONE'
                    
                    return (
                      <>
                        <span className={`rounded border px-1.5 py-0.5 font-mono text-[9px] font-bold uppercase ${
                          ifFlagged || llmThreat
                            ? "border-red-500/30 bg-red-500/10 text-red-600"
                            : "border-emerald-500/30 bg-emerald-500/10 text-emerald-600"
                        }`}>
                          {ifFlagged || llmThreat ? `${detectionSource} THREAT` : "NORMAL"}
                        </span>
                        {(ifFlagged || llmThreat) && (
                          <span className={`rounded border px-1.5 py-0.5 font-mono text-[9px] font-bold uppercase ${
                            priority === 'HIGH'
                              ? "border-red-500/30 bg-red-500/10 text-red-600"
                              : "border-amber-500/30 bg-amber-500/10 text-amber-600"
                          }`}>
                            {priority} PRIORITY
                          </span>
                        )}
                        {pipelineResult.riskResult && (
                          <span className={`rounded border px-1.5 py-0.5 font-mono text-[9px] font-bold uppercase ${
                            pipelineResult.riskResult.decision === "ESCALATE" || pipelineResult.riskResult.decision === "BLOCK"
                              ? "border-red-500/30 bg-red-500/10 text-red-600"
                              : pipelineResult.riskResult.decision === "MONITOR"
                              ? "border-amber-500/30 bg-amber-500/10 text-amber-600"
                              : "border-emerald-500/30 bg-emerald-500/10 text-emerald-600"
                          }`}>
                            {pipelineResult.riskResult.decision}
                          </span>
                        )}
                      </>
                    )
                  })()}
                </div>
              </div>
            </CardHeader>
            <CardContent className="p-4">
              <div className="grid gap-4 lg:grid-cols-2">
                {/* Behavior Agent Results */}
                <div className="space-y-3">
                  <h4 className="font-mono text-[10px] font-medium uppercase tracking-wider text-muted-foreground">
                    Monitor A (Behavior Agent)
                  </h4>
                  <div className="rounded border border-border bg-muted/30 p-3 space-y-2">
                    <div className="grid grid-cols-2 gap-2 text-xs">
                      <div>
                        <span className="font-mono text-[9px] uppercase text-muted-foreground">User</span>
                        <p className="font-mono font-medium">{pipelineResult.behaviorResult.user_id}</p>
                      </div>
                      <div>
                        <span className="font-mono text-[9px] uppercase text-muted-foreground">Score</span>
                        <p className="font-mono font-medium">{pipelineResult.behaviorResult.combined_score.toFixed(4)}</p>
                      </div>
                      <div>
                        <span className="font-mono text-[9px] uppercase text-muted-foreground">Verdict</span>
                        <p className="font-mono font-medium">{pipelineResult.behaviorResult.detection_agent_analysis.verdict}</p>
                      </div>
                      <div>
                        <span className="font-mono text-[9px] uppercase text-muted-foreground">Confidence</span>
                        <p className="font-mono font-medium">{pipelineResult.behaviorResult.confidence.toUpperCase()}</p>
                      </div>
                    </div>
                    {pipelineResult.behaviorResult.triggered_rules.length > 0 && (
                      <div>
                        <span className="font-mono text-[9px] uppercase text-muted-foreground">Triggered Rules</span>
                        <div className="flex flex-wrap gap-1 mt-1">
                          {pipelineResult.behaviorResult.triggered_rules.map((rule) => (
                            <span key={rule} className="rounded border border-amber-500/30 bg-amber-500/10 px-1.5 py-0.5 font-mono text-[9px] text-amber-600">
                              {rule}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}
                    <div>
                      <span className="font-mono text-[9px] uppercase text-muted-foreground">Analysis</span>
                      <p className="text-xs leading-relaxed mt-1">{pipelineResult.behaviorResult.detection_agent_analysis.analyst_note}</p>
                    </div>
                  </div>
                </div>

                {/* Risk Agent Results */}
                <div className="space-y-3">
                  <h4 className="font-mono text-[10px] font-medium uppercase tracking-wider text-muted-foreground">
                    Risk Decision Agent
                  </h4>
                  {pipelineResult.riskResult ? (
                    <div className="rounded border border-border bg-muted/30 p-3 space-y-2">
                      <div className="grid grid-cols-2 gap-2 text-xs">
                        <div>
                          <span className="font-mono text-[9px] uppercase text-muted-foreground">Decision</span>
                          <p className="font-mono font-medium">{pipelineResult.riskResult.decision}</p>
                        </div>
                        <div>
                          <span className="font-mono text-[9px] uppercase text-muted-foreground">Risk Level</span>
                          <p className="font-mono font-medium">{pipelineResult.riskResult.risk_level}</p>
                        </div>
                        <div>
                          <span className="font-mono text-[9px] uppercase text-muted-foreground">Base Score</span>
                          <p className="font-mono font-medium">{pipelineResult.riskResult.base_score.toFixed(2)}</p>
                        </div>
                        <div>
                          <span className="font-mono text-[9px] uppercase text-muted-foreground">Adjusted Score</span>
                          <p className="font-mono font-medium">{pipelineResult.riskResult.adjusted_risk_score.toFixed(2)}</p>
                        </div>
                      </div>
                      <div>
                        <span className="font-mono text-[9px] uppercase text-muted-foreground">Recommended Action</span>
                        <p className="text-xs leading-relaxed mt-1">{pipelineResult.riskResult.recommended_action}</p>
                      </div>
                      <div>
                        <span className="font-mono text-[9px] uppercase text-muted-foreground">Decision Reasoning</span>
                        <p className="text-xs leading-relaxed mt-1">{pipelineResult.riskResult.decision_reasoning}</p>
                      </div>
                    </div>
                  ) : (
                    <div className="rounded border border-border bg-muted/30 p-3">
                      <p className="font-mono text-xs text-muted-foreground">
                        Session not flagged - no risk analysis performed
                      </p>
                    </div>
                  )}
                </div>
              </div>

              {/* Session Details */}
              <div className="mt-4 pt-4 border-t border-border">
                <h4 className="font-mono text-[10px] font-medium uppercase tracking-wider text-muted-foreground mb-2">
                  Test Session Details
                </h4>
                <div className="grid grid-cols-4 gap-2 rounded border border-border bg-muted/30 p-2">
                  {Object.entries({
                    'Hour': pipelineResult.session.hour_of_day,
                    'Files': pipelineResult.session.file_count,
                    'USB': pipelineResult.session.usb_connected ? 'Yes' : 'No',
                    'Ext Email': pipelineResult.session.has_ext_email ? 'Yes' : 'No',
                    'Exfil Domain': pipelineResult.session.visited_exfil_domain ? 'Yes' : 'No',
                    'After Hours': pipelineResult.session.is_outside_hours ? 'Yes' : 'No',
                    'Duration': `${pipelineResult.session.duration_minutes?.toFixed(1)}m`,
                    'Sensitivity': pipelineResult.session.max_sensitivity
                  }).map(([key, value]) => (
                    <div key={key} className="flex flex-col">
                      <span className="font-mono text-[9px] uppercase tracking-wider text-muted-foreground">
                        {key}
                      </span>
                      <span className="font-mono text-xs font-medium text-foreground">
                        {String(value ?? '—')}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            </CardContent>
          </Card>
        </motion.div>
      )}

      {/* Recent Activity */}
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.15 }}
        className="mt-4 grid gap-4 lg:grid-cols-2"
      >
        {/* High Priority Events */}
        <Card className="rounded border-border">
          <CardHeader className="border-b border-border p-3">
            <div className="flex items-center justify-between">
              <span className="font-mono text-[10px] font-medium uppercase tracking-wider text-muted-foreground">
                High Priority Events
              </span>
              <span className="rounded border border-red-500/30 bg-red-500/10 px-1.5 py-0.5 font-mono text-[9px] font-medium uppercase text-red-600">
                3 Critical
              </span>
            </div>
          </CardHeader>
          <CardContent className="p-3">
            <div className="space-y-2">
              {[
                { id: "EVT-001542", risk: 87, user: "USR-4521", type: "Suspicious Login" },
                { id: "EVT-001539", risk: 72, user: "USR-3892", type: "Data Exfiltration Attempt" },
                { id: "EVT-001535", risk: 68, user: "USR-1205", type: "Privilege Escalation" },
              ].map((event) => (
                <div
                  key={event.id}
                  className="flex items-center justify-between rounded border border-border bg-muted/30 p-2 transition-colors hover:bg-muted/50"
                >
                  <div className="flex items-center gap-3">
                    <div className="flex h-8 w-8 items-center justify-center rounded border border-red-500/30 bg-red-500/10">
                      <span className="font-mono text-xs font-bold text-red-600">{event.risk}</span>
                    </div>
                    <div>
                      <p className="text-xs font-medium">{event.type}</p>
                      <p className="font-mono text-[10px] text-muted-foreground">
                        {event.id} | {event.user}
                      </p>
                    </div>
                  </div>
                  <span className="rounded border border-red-500/30 bg-red-500/10 px-1.5 py-0.5 font-mono text-[9px] font-medium uppercase text-red-600">
                    High
                  </span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Recent Responses */}
        <Card className="rounded border-border">
          <CardHeader className="border-b border-border p-3">
            <div className="flex items-center justify-between">
              <span className="font-mono text-[10px] font-medium uppercase tracking-wider text-muted-foreground">
                Recent Responses
              </span>
              <span className="font-mono text-[10px] text-muted-foreground">
                Last 15 minutes
              </span>
            </div>
          </CardHeader>
          <CardContent className="p-3">
            <div className="space-y-2">
              {[
                { action: "Session Terminated", target: "USR-4521", time: "2m ago", status: "completed" },
                { action: "MFA Challenge Sent", target: "USR-3892", time: "5m ago", status: "pending" },
                { action: "Account Locked", target: "USR-1205", time: "8m ago", status: "completed" },
              ].map((response, index) => (
                <div
                  key={index}
                  className="flex items-center justify-between rounded border border-border bg-muted/30 p-2 transition-colors hover:bg-muted/50"
                >
                  <div>
                    <p className="text-xs font-medium">{response.action}</p>
                    <p className="font-mono text-[10px] text-muted-foreground">
                      {response.target} | {response.time}
                    </p>
                  </div>
                  <span className={`rounded border px-1.5 py-0.5 font-mono text-[9px] font-medium uppercase ${
                    response.status === "completed" 
                      ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-600" 
                      : "border-amber-500/30 bg-amber-500/10 text-amber-600"
                  }`}>
                    {response.status === "completed" ? "Done" : "Pending"}
                  </span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </motion.div>
    </div>
  )
}
