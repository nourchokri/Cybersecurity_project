"use client"

import { useState, useEffect, useRef } from "react"
import { Card, CardContent, CardHeader } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { 
  Loader2,
  Target,
  AlertTriangle,
  Activity,
  Zap
} from "lucide-react"
import {
  getAttackerStats,
  getAttackHistory,
  getAttackerLogs,
  simulateAttack,
  type AttackerStats,
  type AttackHistoryItem
} from "@/lib/api"

interface AttackerAgentLiveProps {
  agentSlug: string
  onLog?: (log: { type: "info" | "success" | "error" | "warning"; message: string }) => void
  pipelineActive?: boolean
}

export function AttackerAgentLive({ agentSlug, onLog, pipelineActive }: AttackerAgentLiveProps) {
  const [stats, setStats] = useState<AttackerStats | null>(null)
  const [history, setHistory] = useState<AttackHistoryItem[]>([])
  const [loading, setLoading] = useState(false)
  const [simulating, setSimulating] = useState(false)
  const logPollingRef = useRef<NodeJS.Timeout | null>(null)
  const statsPollingRef = useRef<NodeJS.Timeout | null>(null)
  const lastLogTimestampRef = useRef<string | null>(null)

  useEffect(() => {
    loadData()
    
    // Start polling for logs when component mounts
    startLogPolling()
    
    // Cleanup on unmount
    return () => {
      if (logPollingRef.current) {
        clearInterval(logPollingRef.current)
      }
      if (statsPollingRef.current) {
        clearInterval(statsPollingRef.current)
      }
    }
  }, [])

  const loadData = async () => {
    setLoading(true)
    try {
      const [statsRes, historyRes] = await Promise.all([
        getAttackerStats(),
        getAttackHistory(10)
      ])
      
      setStats(statsRes)
      setHistory(historyRes.attacks || [])

      // Sync simulating state from backend
      if (statsRes.simulating) {
        setSimulating(true)
      }
    } catch (error) {
      // Silently fail on initial load - backend might not be ready yet
      console.error('Failed to load data:', error)
    } finally {
      setLoading(false)
    }
  }

  const startLogPolling = () => {
    // Poll logs every 2 seconds
    logPollingRef.current = setInterval(async () => {
      try {
        const logsRes = await getAttackerLogs(50)
        if (logsRes.ok && logsRes.logs.length > 0) {
          // Filter to only new logs (after last timestamp)
          const newLogs = lastLogTimestampRef.current 
            ? logsRes.logs.filter(log => log.timestamp > lastLogTimestampRef.current!)
            : logsRes.logs
          
          // Send new logs to parent component for display
          newLogs.forEach(log => {
            const logType = log.level === 'ERROR' ? 'error' : 
                           log.level === 'WARNING' ? 'warning' : 
                           log.level === 'INFO' ? 'info' : 'info'
            onLog?.({ type: logType, message: log.message })
          })
          
          // Update last timestamp
          if (logsRes.logs.length > 0) {
            lastLogTimestampRef.current = logsRes.logs[logsRes.logs.length - 1].timestamp
          }
        }
      } catch (error) {
        // Silently fail - don't spam errors
        console.error('Failed to fetch logs:', error)
      }
    }, 2000)
  }

  // Poll stats while simulating to detect completion
  const startSimulationPolling = () => {
    statsPollingRef.current = setInterval(async () => {
      try {
        const [statsRes, historyRes] = await Promise.all([
          getAttackerStats(),
          getAttackHistory(10)
        ])
        setStats(statsRes)
        setHistory(historyRes.attacks || [])

        // Check if simulation finished
        if (!statsRes.simulating) {
          setSimulating(false)
          onLog?.({ type: "success", message: "Attack simulation completed!" })
          if (statsPollingRef.current) {
            clearInterval(statsPollingRef.current)
            statsPollingRef.current = null
          }
        }
      } catch (error) {
        console.error('Failed to poll stats:', error)
      }
    }, 3000)
  }

  const handleSimulateAttack = async () => {
    setSimulating(true)
    onLog?.({ type: "info", message: "🎯 Starting single attack simulation (5 phases)..." })
    try {
      const result = await simulateAttack()
      if (result.ok) {
        onLog?.({ type: "success", message: "Attack simulation triggered — running 5 phases..." })
        // Start polling to detect when simulation finishes
        startSimulationPolling()
      } else {
        onLog?.({ type: "error", message: `Failed to simulate attack: ${result.error}` })
        setSimulating(false)
      }
    } catch (error) {
      onLog?.({ type: "error", message: `Simulate attack error: ${error instanceof Error ? error.message : 'Unknown error'}` })
      setSimulating(false)
    }
  }

  return (
    <div className="space-y-4">
      {/* LLM-Powered Agent Control */}
      <Card>
        <CardHeader className="border-b border-border p-3">
          <div className="flex items-center justify-between">
            <span className="font-mono text-[10px] font-medium uppercase tracking-wider text-muted-foreground">
              LLM-Powered Autonomous Agent
            </span>
            <Activity className="h-4 w-4 text-blue-500" />
          </div>
        </CardHeader>
        <CardContent className="p-4 space-y-3">
          <p className="text-xs text-muted-foreground">
            Runs a single 5-phase attack cycle: Observe → List → Analyze → Choose → Inject
          </p>
          {pipelineActive && (
            <div className="flex items-center gap-2 rounded border border-blue-500/30 bg-blue-500/10 p-2">
              <span className="relative flex h-2 w-2">
                <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-blue-400 opacity-75" />
                <span className="relative inline-flex h-2 w-2 rounded-full bg-blue-500" />
              </span>
              <span className="font-mono text-[11px] text-blue-500">Running via pipeline — check logs panel for real-time updates</span>
            </div>
          )}
          <div className="pt-2">
            <Button
              onClick={handleSimulateAttack}
              disabled={simulating || pipelineActive}
              className="w-full gap-2 bg-red-600 hover:bg-red-700 text-white font-semibold disabled:opacity-50"
              size="sm"
            >
              {pipelineActive ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  <span>Running via Pipeline...</span>
                </>
              ) : simulating ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  <span>Simulating Attack...</span>
                </>
              ) : (
                <>
                  <Zap className="h-4 w-4" />
                  <span>Simulate Attack</span>
                </>
              )}
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Recent History */}
      <Card>
        <CardHeader className="border-b border-border p-3">
          <div className="flex items-center justify-between">
            <span className="font-mono text-[10px] font-medium uppercase tracking-wider text-muted-foreground">
              Recent Attacks ({history.length})
            </span>
            <AlertTriangle className="h-4 w-4 text-amber-500" />
          </div>
        </CardHeader>
        <CardContent className="p-4">
          {history.length === 0 ? (
            <p className="text-center text-xs text-muted-foreground py-4">No attacks injected yet</p>
          ) : (
            <div className="space-y-2">
              {history.slice(0, 5).map((attack, idx) => (
                <div key={idx} className="rounded border border-border bg-muted/30 p-2">
                  <div className="flex items-center justify-between mb-1">
                    <span className="font-mono text-xs font-medium">{attack.attack_name}</span>
                    <span className={`rounded border px-1 py-0.5 font-mono text-[9px] font-bold uppercase ${
                      attack.severity === 'high' ? 'border-red-500/30 bg-red-500/10 text-red-600' :
                      attack.severity === 'medium' ? 'border-amber-500/30 bg-amber-500/10 text-amber-600' :
                      'border-blue-500/30 bg-blue-500/10 text-blue-600'
                    }`}>
                      {attack.severity}
                    </span>
                  </div>
                  <div className="flex items-center gap-3 text-[10px] text-muted-foreground">
                    <span>User: <span className="font-mono text-foreground">{attack.user_id}</span></span>
                    <span>Events: <span className="font-mono text-foreground">{attack.event_count}</span></span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
