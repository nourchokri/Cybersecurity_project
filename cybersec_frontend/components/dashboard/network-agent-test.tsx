"use client"

import { useState, useEffect } from "react"
import { motion } from "framer-motion"
import { Card, CardContent, CardHeader } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Play, Loader2, Network, AlertTriangle, CheckCircle2, XCircle, RefreshCw, FileJson } from "lucide-react"
import { usePipeline } from "@/lib/pipeline-store"

interface NetworkAnalysisResult {
  event_id: string
  timestamp: string
  source: string[]
  user_anomaly_score: number | null
  network_anomaly_score: number
  combined_score: number
  user_id: string
  entity_id: string
  dimension_scores: {
    time: number
    device: number
    volume: number
    sensitivity: number
  }
  triggered_rules: string[]
  network_attack_category: string | null
  correlation: Record<string, unknown>
  explanation: string
  baseline_age_days: number
  confidence: string
  cold_start: boolean
  simulated: boolean
  flagged: boolean
  if_score: number
  detection_agent_analysis: {
    model: string
    llm_used: boolean
    analyst_note: string
    scoring_mode: string
    score: number
    threshold: number
    verdict: string
    triggered_signals: string[]
    dimension_breakdown: {
      time: number
      device: number
      volume: number
      sensitivity: number
    }
    session_summary: Record<string, unknown>
    baseline_context: Record<string, unknown>
  }
}

export function NetworkAgentTest() {
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<NetworkAnalysisResult | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [connectionCount, setConnectionCount] = useState<number>(0)
  const [lastPipelineResult, setLastPipelineResult] = useState<any>(null)
  const [storedEvents, setStoredEvents] = useState<any>(null)
  const [activeTab, setActiveTab] = useState("results")
  const [selectedDate, setSelectedDate] = useState<string>("")

  const pipeline = usePipeline()

  // Check if there's a pipeline result with network data
  useEffect(() => {
    if (pipeline.pipelineResult) {
      setLastPipelineResult(pipeline.pipelineResult)
    }
  }, [pipeline.pipelineResult])

  const loadNetworkResults = async () => {
    setLoading(true)
    setError(null)
    setResult(null)
    setConnectionCount(0)
    setStoredEvents(null)

    try {
      // Step 1: Load stored events from logs/
      const storedResponse = await fetch('http://localhost:8000/api/v1/data/stored-events/')
      
      if (!storedResponse.ok) {
        throw new Error(`Failed to load stored events: ${storedResponse.status}`)
      }

      const storedData = await storedResponse.json()
      
      if (!storedData.ok) {
        setError(storedData.message || 'No stored events found')
        return
      }

      setStoredEvents(storedData)
      
      // Set default selected date to the most recent
      const dates = Object.keys(storedData.events_by_date || {})
      if (dates.length > 0 && !selectedDate) {
        setSelectedDate(dates[0])
      }

      // Step 2: Analyze stored network events
      const analyzeResponse = await fetch('http://localhost:8000/api/v1/data/analyze-stored-network/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          date: selectedDate || undefined  // Analyze specific date or all
        })
      })

      if (!analyzeResponse.ok) {
        throw new Error(`Failed to analyze network events: ${analyzeResponse.status}`)
      }

      const analyzeData = await analyzeResponse.json()
      
      if (!analyzeData.ok) {
        setError(analyzeData.message || 'Network analysis failed')
        return
      }

      // Extract network results
      if (analyzeData.network_result && analyzeData.network_result.results && analyzeData.network_result.results.length > 0) {
        const networkResults = analyzeData.network_result.results
        setConnectionCount(networkResults.length)
        
        // Prioritize flagged results
        const flaggedResult = networkResults.find((r: any) => r.flagged)
        const selectedResult = flaggedResult || networkResults[0]
        
        setResult(selectedResult)
      } else {
        setError("No network events found in stored files. Collect network data first.")
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error occurred")
    } finally {
      setLoading(false)
    }
  }

  // Auto-load if there's a pipeline result with network data
  useEffect(() => {
    if (lastPipelineResult && !result && !loading) {
      // Check if the pipeline result has network data
      const hasNetworkData = lastPipelineResult.behaviorResult?.network_anomaly_score !== null
      if (hasNetworkData) {
        loadNetworkResults()
      }
    }
  }, [lastPipelineResult])

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.2 }}
    >
      <Card className="rounded border-border">
        <CardHeader className="border-b border-border p-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Network className="h-4 w-4 text-blue-500" />
              <span className="font-mono text-[10px] font-medium uppercase tracking-wider text-muted-foreground">
                Network Analysis Results
              </span>
            </div>
            <Button
              onClick={loadNetworkResults}
              disabled={loading}
              size="sm"
              className="h-7 gap-1.5 rounded border border-blue-500/50 bg-blue-500/10 px-2 font-mono text-[10px] font-medium uppercase text-blue-600 hover:bg-blue-500/20"
            >
              {loading ? (
                <>
                  <Loader2 className="h-3 w-3 animate-spin" />
                  <span>Analyzing...</span>
                </>
              ) : (
                <>
                  <RefreshCw className="h-3 w-3" />
                  <span>Analyze Stored Events</span>
                </>
              )}
            </Button>
          </div>
        </CardHeader>

        <CardContent className="p-4">
          {!result && !error && !loading && (
            <div className="rounded border border-dashed border-border bg-muted/30 p-6 text-center">
              <Network className="mx-auto mb-2 h-8 w-8 text-muted-foreground/50" />
              <p className="font-mono text-xs text-muted-foreground">
                Click "Analyze Stored Events" to load events from logs/
              </p>
              <p className="mt-1 font-mono text-[10px] text-muted-foreground/70">
                Reads events_*.jsonl files and analyzes network risks
              </p>
            </div>
          )}

          {error && (
            <div className="rounded border border-red-500/50 bg-red-500/10 p-4">
              <div className="flex items-start gap-2">
                <XCircle className="h-4 w-4 text-red-500 mt-0.5" />
                <div className="flex-1">
                  <p className="font-mono text-xs font-medium text-red-600">No Stored Events Found</p>
                  <p className="mt-1 font-mono text-[10px] text-red-600/80">{error}</p>
                  <div className="mt-3 space-y-2 rounded border border-red-500/30 bg-red-500/5 p-2">
                    <p className="font-mono text-[10px] font-medium text-red-600">How to collect events:</p>
                    <ol className="ml-3 list-decimal space-y-1 font-mono text-[10px] text-red-600/70">
                      <li>Go to the <strong>Data Agent</strong> page</li>
                      <li>Click <strong>"Start Collection"</strong> button</li>
                      <li>Wait for events to be collected and stored</li>
                      <li>Return here and click <strong>"Analyze Stored Events"</strong></li>
                    </ol>
                    <p className="mt-2 font-mono text-[9px] text-red-600/60">
                      Events will be saved to: cybersec_backend/architecture/data_agent/logs/events_*.jsonl
                    </p>
                  </div>
                </div>
              </div>
            </div>
          )}

          {result && (
            <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-4">
              <TabsList className="h-7 w-fit rounded border border-border bg-muted/50 p-0.5">
                <TabsTrigger value="results" className="h-6 rounded px-2 font-mono text-[10px] uppercase tracking-wider">
                  Analysis Results
                </TabsTrigger>
                <TabsTrigger value="input" className="h-6 rounded px-2 font-mono text-[10px] uppercase tracking-wider">
                  <FileJson className="mr-1 h-3 w-3" />
                  Input Data
                </TabsTrigger>
              </TabsList>

              <TabsContent value="results" className="m-0 space-y-4">
                {/* Connection Count Info */}
                {connectionCount > 0 && (
                  <div className="rounded border border-blue-500/30 bg-blue-500/10 p-2">
                    <p className="font-mono text-[10px] text-blue-600">
                      Analyzed {connectionCount} network connection{connectionCount !== 1 ? 's' : ''} from pipeline data
                    </p>
                  </div>
                )}

                {/* Attack Detection Status */}
                <div className={`rounded border p-3 ${
                  result.flagged 
                    ? "border-amber-500/50 bg-amber-500/10" 
                    : "border-emerald-500/50 bg-emerald-500/10"
                }`}>
                  <div className="flex items-center gap-2">
                    {result.flagged ? (
                      <AlertTriangle className="h-4 w-4 text-amber-500" />
                    ) : (
                      <CheckCircle2 className="h-4 w-4 text-emerald-500" />
                    )}
                    <span className={`font-mono text-xs font-medium ${
                      result.flagged ? "text-amber-600" : "text-emerald-600"
                    }`}>
                      {result.flagged ? "ATTACK DETECTED" : "NORMAL TRAFFIC"}
                    </span>
                  </div>
                </div>

                {/* Attack Details Grid */}
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <p className="font-mono text-[10px] uppercase tracking-wider text-muted-foreground">
                      Attack Type
                    </p>
                    <p className="mt-1 font-mono text-sm font-medium text-foreground">
                      {result.network_attack_category || "Normal"}
                    </p>
                  </div>

                  <div>
                    <p className="font-mono text-[10px] uppercase tracking-wider text-muted-foreground">
                      Confidence
                    </p>
                    <p className="mt-1 font-mono text-sm font-medium text-foreground capitalize">
                      {result.confidence}
                    </p>
                  </div>

                  <div>
                    <p className="font-mono text-[10px] uppercase tracking-wider text-muted-foreground">
                      Anomaly Score
                    </p>
                    <p className="mt-1 font-mono text-sm font-medium text-foreground">
                      {result.combined_score.toFixed(4)}
                    </p>
                  </div>

                  <div>
                    <p className="font-mono text-[10px] uppercase tracking-wider text-muted-foreground">
                      Verdict
                    </p>
                    <p className="mt-1 font-mono text-sm font-medium text-foreground">
                      {result.detection_agent_analysis.verdict}
                    </p>
                  </div>

                  <div>
                    <p className="font-mono text-[10px] uppercase tracking-wider text-muted-foreground">
                      User ID
                    </p>
                    <p className="mt-1 font-mono text-sm font-medium text-foreground">
                      {result.user_id}
                    </p>
                  </div>

                  <div>
                    <p className="font-mono text-[10px] uppercase tracking-wider text-muted-foreground">
                      Source IP
                    </p>
                    <p className="mt-1 font-mono text-sm font-medium text-foreground">
                      {result.entity_id}
                    </p>
                  </div>
                </div>

                {/* Triggered Rules */}
                {result.triggered_rules.length > 0 && (
                  <div>
                    <p className="mb-2 font-mono text-[10px] uppercase tracking-wider text-muted-foreground">
                      Triggered Rules
                    </p>
                    <div className="space-y-1">
                      {result.triggered_rules.slice(0, 5).map((rule, idx) => (
                        <div
                          key={idx}
                          className="rounded border border-border bg-muted/30 px-2 py-1 font-mono text-[10px] text-muted-foreground"
                        >
                          • {rule.replace(/_/g, " ")}
                        </div>
                      ))}
                      {result.triggered_rules.length > 5 && (
                        <p className="font-mono text-[10px] text-muted-foreground">
                          +{result.triggered_rules.length - 5} more rules
                        </p>
                      )}
                    </div>
                  </div>
                )}

                {/* LLM Explanation */}
                {result.explanation && (
                  <div>
                    <p className="mb-2 font-mono text-[10px] uppercase tracking-wider text-muted-foreground">
                      Analysis Explanation
                    </p>
                    <div className="rounded border border-border bg-muted/30 p-3">
                      <p className="font-mono text-[11px] leading-relaxed text-foreground">
                        {result.explanation}
                      </p>
                    </div>
                  </div>
                )}

                {/* Model Info */}
                <div className="rounded border border-border bg-muted/20 p-2">
                  <p className="font-mono text-[9px] text-muted-foreground">
                    Model: {result.detection_agent_analysis.model} | 
                    LLM: {result.detection_agent_analysis.llm_used ? "Yes" : "No"} | 
                    Mode: {result.detection_agent_analysis.scoring_mode}
                  </p>
                </div>
              </TabsContent>

              <TabsContent value="input" className="m-0">
                <div className="space-y-3">
                  {/* Stored Events Summary */}
                  {storedEvents && (
                    <div className="rounded border border-blue-500/30 bg-blue-500/10 p-3">
                      <div className="flex items-center gap-2 mb-2">
                        <FileJson className="h-4 w-4 text-blue-600" />
                        <span className="font-mono text-[10px] font-medium uppercase tracking-wider text-blue-600">
                          Stored Events from logs/ Directory
                        </span>
                      </div>
                      <div className="grid grid-cols-3 gap-2 text-[10px] mb-3">
                        <div>
                          <span className="text-blue-600/70">Total Events:</span>
                          <span className="ml-1 font-medium text-blue-600">{storedEvents.total_events || 0}</span>
                        </div>
                        <div>
                          <span className="text-blue-600/70">Network Events:</span>
                          <span className="ml-1 font-medium text-blue-600">{storedEvents.network_events_count || 0}</span>
                        </div>
                        <div>
                          <span className="text-blue-600/70">Files:</span>
                          <span className="ml-1 font-medium text-blue-600">{storedEvents.files_count || 0}</span>
                        </div>
                      </div>

                      {/* Date Selector */}
                      {storedEvents.events_by_date && Object.keys(storedEvents.events_by_date).length > 0 && (
                        <div className="space-y-1.5">
                          <label className="font-mono text-[10px] uppercase tracking-wider text-blue-600/70">
                            Select Date
                          </label>
                          <select
                            value={selectedDate}
                            onChange={(e) => setSelectedDate(e.target.value)}
                            className="w-full rounded border border-blue-500/30 bg-blue-500/5 px-2 py-1.5 font-mono text-xs text-blue-600 focus:outline-none focus:ring-1 focus:ring-blue-500"
                          >
                            <option value="">All Dates</option>
                            {Object.keys(storedEvents.events_by_date).map((date) => {
                              const dateData = storedEvents.events_by_date[date]
                              return (
                                <option key={date} value={date}>
                                  {date} ({dateData.event_count} events, {dateData.network_events.length} network)
                                </option>
                              )
                            })}
                          </select>
                        </div>
                      )}
                    </div>
                  )}

                  {/* Events Display by Date */}
                  {storedEvents && storedEvents.events_by_date && (
                    <div className="space-y-3">
                      {Object.entries(storedEvents.events_by_date)
                        .filter(([date]) => !selectedDate || date === selectedDate)
                        .map(([date, dateData]: [string, any]) => (
                          <div key={date} className="rounded border border-border bg-muted/30 p-3">
                            <div className="flex items-center justify-between mb-2">
                              <h4 className="font-mono text-[10px] font-medium uppercase tracking-wider text-muted-foreground">
                                {date} - {dateData.file}
                              </h4>
                              <span className="font-mono text-[10px] text-muted-foreground">
                                {dateData.event_count} events ({dateData.network_events.length} network)
                              </span>
                            </div>

                            {/* Network Events Preview */}
                            {dateData.network_events.length > 0 && (
                              <div className="mt-2 space-y-1">
                                <p className="font-mono text-[9px] uppercase tracking-wider text-muted-foreground">
                                  Network Events Preview (first 3)
                                </p>
                                {dateData.network_events.slice(0, 3).map((event: any, idx: number) => (
                                  <div key={idx} className="rounded border border-border bg-card p-2 font-mono text-[10px]">
                                    <div className="flex justify-between">
                                      <span className="text-muted-foreground">{event.event_type}</span>
                                      <span className="text-foreground">{event.timestamp?.slice(11, 19)}</span>
                                    </div>
                                    <div className="mt-1 text-muted-foreground">
                                      {event.user_id} → {event.metadata?.destination_ip || 'N/A'}
                                    </div>
                                  </div>
                                ))}
                                {dateData.network_events.length > 3 && (
                                  <p className="font-mono text-[10px] text-muted-foreground">
                                    +{dateData.network_events.length - 3} more network events
                                  </p>
                                )}
                              </div>
                            )}
                          </div>
                        ))}
                    </div>
                  )}

                  {/* Full JSON Display */}
                  {storedEvents && (
                    <>
                      <div className="max-h-[400px] overflow-auto rounded border border-zinc-800 bg-zinc-950">
                        <motion.pre
                          initial={{ opacity: 0 }}
                          animate={{ opacity: 1 }}
                          className="p-3 font-mono text-[11px] leading-relaxed text-zinc-300"
                        >
                          {JSON.stringify(storedEvents, null, 2)}
                        </motion.pre>
                      </div>

                      {/* Download Button */}
                      <Button
                        onClick={() => {
                          const blob = new Blob([JSON.stringify(storedEvents, null, 2)], { type: 'application/json' })
                          const url = URL.createObjectURL(blob)
                          const a = document.createElement('a')
                          a.href = url
                          a.download = `stored-events-${new Date().toISOString().slice(0, 19).replace(/:/g, '-')}.json`
                          a.click()
                          URL.revokeObjectURL(url)
                        }}
                        className="w-full gap-2 rounded border border-blue-500/50 bg-blue-500/10 font-mono text-[10px] font-medium uppercase text-blue-600 hover:bg-blue-500/20"
                      >
                        <FileJson className="h-3 w-3" />
                        Download Stored Events JSON
                      </Button>
                    </>
                  )}
                </div>
              </TabsContent>
            </Tabs>
          )}
        </CardContent>
      </Card>
    </motion.div>
  )
}
