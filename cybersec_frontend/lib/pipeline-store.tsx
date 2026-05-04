"use client"

import React, { createContext, useContext, useState, useCallback, useRef } from "react"
import type { AgentStatus } from "@/lib/mock-data"
import type { SessionInput, BehaviorAnomalyResult, DecisionOutput } from "@/lib/api"

// ─── Types ────────────────────────────────────────────────────────
export interface PipelineLogEntry {
  id: string
  time: string
  type: "info" | "success" | "error" | "warning"
  message: string
  agentSlug: string  // which agent produced this log
}

export interface PipelineState {
  /** Is a pipeline currently running from the Overview page? */
  pipelineRunning: boolean
  /** Which agents are currently part of the running pipeline */
  pipelineAgents: Set<string>
  /** Status of each agent in the pipeline */
  agentStatuses: Record<string, AgentStatus>
  /** All logs produced during pipeline runs, keyed by agent slug */
  agentLogs: Record<string, PipelineLogEntry[]>
  /** Global log counter for unique IDs */
  logCounter: number
  /** The final result payload of a completed pipeline run */
  pipelineResult: {
    session: SessionInput
    behaviorResult: BehaviorAnomalyResult
    riskResult?: DecisionOutput
    responseResult?: any  // Response Agent decision
  } | null
}

export interface PipelineActions {
  /** Mark the pipeline as running with a set of agents */
  startPipeline: (agents: string[]) => void
  /** Mark the pipeline as stopped */
  stopPipeline: () => void
  /** Update pipeline result */
  setPipelineResult: (result: PipelineState["pipelineResult"]) => void
  /** Update the status of a specific agent */
  setAgentStatus: (agentSlug: string, status: AgentStatus) => void
  /** Batch-update agent statuses (accepts object or callback) */
  setAgentStatuses: (statusesOrUpdater: Record<string, AgentStatus> | ((prev: Record<string, AgentStatus>) => Record<string, AgentStatus>)) => void
  /** Add a log entry for a specific agent */
  addLog: (agentSlug: string, log: { type: "info" | "success" | "error" | "warning"; message: string }) => void
  /** Clear logs for a specific agent */
  clearAgentLogs: (agentSlug: string) => void
  /** Clear all logs */
  clearAllLogs: () => void
  /** Check if a specific agent is currently running as part of the pipeline */
  isAgentInPipeline: (agentSlug: string) => boolean
  /** Get logs for a specific agent */
  getAgentLogs: (agentSlug: string) => PipelineLogEntry[]
}

const defaultStatuses: Record<string, AgentStatus> = {
  'data-agent': 'idle',
  'attacker-agent': 'idle',
  'behavior-agent': 'idle',
  'risk-behavior-agent': 'idle',
  'response-agent': 'idle',
  'reporting-agent': 'idle'
}

// ─── Context ──────────────────────────────────────────────────────
const PipelineContext = createContext<(PipelineState & PipelineActions) | null>(null)

// ─── Provider ─────────────────────────────────────────────────────
export function PipelineProvider({ children }: { children: React.ReactNode }) {
  const [pipelineRunning, setPipelineRunning] = useState(false)
  const [pipelineAgents, setPipelineAgents] = useState<Set<string>>(new Set())
  const [agentStatuses, setAgentStatusesState] = useState<Record<string, AgentStatus>>(defaultStatuses)
  const [agentLogs, setAgentLogs] = useState<Record<string, PipelineLogEntry[]>>({})
  const [pipelineResult, setPipelineResult] = useState<PipelineState["pipelineResult"]>(null)
  const logCounterRef = useRef(0)

  const startPipeline = useCallback((agents: string[]) => {
    setPipelineRunning(true)
    setPipelineAgents(new Set(agents))
  }, [])

  const stopPipeline = useCallback(() => {
    setPipelineRunning(false)
    setPipelineAgents(new Set())
  }, [])

  const setAgentStatus = useCallback((agentSlug: string, status: AgentStatus) => {
    setAgentStatusesState(prev => ({ ...prev, [agentSlug]: status }))
  }, [])

  const setAgentStatuses = useCallback((statusesOrUpdater: Record<string, AgentStatus> | ((prev: Record<string, AgentStatus>) => Record<string, AgentStatus>)) => {
    if (typeof statusesOrUpdater === 'function') {
      setAgentStatusesState(statusesOrUpdater)
    } else {
      setAgentStatusesState(prev => ({ ...prev, ...statusesOrUpdater }))
    }
  }, [])

  const addLog = useCallback((agentSlug: string, log: { type: "info" | "success" | "error" | "warning"; message: string }) => {
    const time = new Date().toLocaleTimeString("en-US", {
      hour12: false,
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    })
    logCounterRef.current += 1
    const entry: PipelineLogEntry = {
      id: `pipeline-${agentSlug}-${logCounterRef.current}`,
      time,
      agentSlug,
      ...log,
    }
    setAgentLogs(prev => ({
      ...prev,
      [agentSlug]: [...(prev[agentSlug] || []), entry],
    }))
  }, [])

  const clearAgentLogs = useCallback((agentSlug: string) => {
    setAgentLogs(prev => ({ ...prev, [agentSlug]: [] }))
  }, [])

  const clearAllLogs = useCallback(() => {
    setAgentLogs({})
  }, [])

  const isAgentInPipeline = useCallback((agentSlug: string) => {
    return pipelineRunning && pipelineAgents.has(agentSlug)
  }, [pipelineRunning, pipelineAgents])

  const getAgentLogs = useCallback((agentSlug: string) => {
    return agentLogs[agentSlug] || []
  }, [agentLogs])

  const value: PipelineState & PipelineActions = {
    pipelineRunning,
    pipelineAgents,
    agentStatuses,
    agentLogs,
    pipelineResult,
    logCounter: logCounterRef.current,
    startPipeline,
    stopPipeline,
    setPipelineResult,
    setAgentStatus,
    setAgentStatuses,
    addLog,
    clearAgentLogs,
    clearAllLogs,
    isAgentInPipeline,
    getAgentLogs,
  }

  return (
    <PipelineContext.Provider value={value}>
      {children}
    </PipelineContext.Provider>
  )
}

// ─── Hook ─────────────────────────────────────────────────────────
export function usePipeline() {
  const ctx = useContext(PipelineContext)
  if (!ctx) {
    throw new Error("usePipeline must be used within a PipelineProvider")
  }
  return ctx
}
