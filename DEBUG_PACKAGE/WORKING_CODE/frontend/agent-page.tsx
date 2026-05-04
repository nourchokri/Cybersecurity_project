"use client"

import { use, useState, useCallback } from "react"
import { motion } from "framer-motion"
import { notFound } from "next/navigation"
import Link from "next/link"
import { agents } from "@/lib/mock-data"
import { AgentInfo } from "@/components/dashboard/agent-info"
import { AgentOutput } from "@/components/dashboard/agent-output"
import { TerminalLogs } from "@/components/dashboard/terminal-logs"
import { RiskAgentLiveOutput } from "@/components/dashboard/risk-agent-live"
import { BehaviorAgentLive } from "@/components/dashboard/behavior-agent-live"
import { DataAgentLive } from "@/components/dashboard/data-agent-live"
import { Button } from "@/components/ui/button"
import { ChevronLeft, ChevronRight } from "lucide-react"

interface AgentPageProps {
  params: Promise<{ slug: string }>
}

export default function AgentPage({ params }: AgentPageProps) {
  const { slug } = use(params)
  const agentIndex = agents.findIndex(a => a.slug === slug)
  const agent = agents[agentIndex]

  const [liveLogs, setLiveLogs] = useState<Array<{ time: string; type: "info" | "success" | "error" | "warning"; message: string }>>([])
  const [dynamicMetrics, setDynamicMetrics] = useState({
    eventsProcessed: agent?.metrics.eventsProcessed || 0,
    alertsGenerated: agent?.metrics.alertsGenerated || 0,
    avgProcessingTime: agent?.metrics.avgProcessingTime || "0ms"
  })
  
  const handleLog = useCallback((log: { type: "info" | "success" | "error" | "warning"; message: string }) => {
    const time = new Date().toLocaleTimeString("en-US", {
      hour12: false,
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    })
    setLiveLogs(prev => [...prev, { time, ...log }])
  }, [])

  const handleAnalysisComplete = useCallback((result: { timeTakenMs: number; isAlert: boolean }) => {
    setDynamicMetrics(prev => {
      const prevMs = parseInt(prev.avgProcessingTime) || result.timeTakenMs
      const newAvg = Math.round((prevMs + result.timeTakenMs) / 2)
      return {
        eventsProcessed: prev.eventsProcessed + 1,
        alertsGenerated: prev.alertsGenerated + (result.isAlert ? 1 : 0),
        avgProcessingTime: `${newAvg}ms`
      }
    })
  }, [])

  if (!agent) {
    notFound()
  }

  const prevAgent = agentIndex > 0 ? agents[agentIndex - 1] : null
  const nextAgent = agentIndex < agents.length - 1 ? agents[agentIndex + 1] : null

  return (
    <div className="flex h-[calc(100vh-3.5rem)] flex-col">
      {/* Header with Navigation */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        className="flex shrink-0 items-center justify-between border-b border-border px-6 py-3"
      >
        <div className="flex items-center gap-3">
          <Link href="/">
            <Button variant="ghost" size="sm" className="h-8 gap-1.5 rounded-md px-3 text-sm">
              <ChevronLeft className="h-4 w-4" />
              Pipeline
            </Button>
          </Link>
          <div className="h-4 w-px bg-border" />
          <div>
            <h1 className="text-base font-semibold">{agent.name}</h1>
            <p className="font-mono text-[10px] uppercase tracking-wider text-muted-foreground">{agent.role}</p>
          </div>
        </div>

        <div className="flex items-center gap-1">
          {prevAgent && (
            <Link href={`/agents/${prevAgent.slug}`}>
              <Button variant="ghost" size="sm" className="h-8 gap-1.5 rounded-md px-3 text-sm">
                <ChevronLeft className="h-4 w-4" />
                <span className="hidden sm:inline">{prevAgent.name}</span>
              </Button>
            </Link>
          )}
          {nextAgent && (
            <Link href={`/agents/${nextAgent.slug}`}>
              <Button variant="ghost" size="sm" className="h-8 gap-1.5 rounded-md px-3 text-sm">
                <span className="hidden sm:inline">{nextAgent.name}</span>
                <ChevronRight className="h-3 w-3" />
              </Button>
            </Link>
          )}
        </div>
      </motion.div>

      {/* 3-Column Layout */}
      <div className="grid flex-1 grid-cols-1 gap-4 overflow-hidden p-4 lg:grid-cols-12">
        {/* Left Panel - Agent Info */}
        <motion.div
          initial={{ opacity: 0, x: -10 }}
          animate={{ opacity: 1, x: 0 }}
          className="overflow-y-auto lg:col-span-3"
        >
          <AgentInfo 
            agentSlug={slug} 
            metricsOverride={
              slug === "risk-behavior-agent" || slug === "behavior-agent"
                ? dynamicMetrics
                : undefined
            } 
          />
        </motion.div>

        {/* Center Panel - AI Output / Live Analysis */}
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.05 }}
          className="overflow-y-auto lg:col-span-5"
        >
          {slug === "risk-behavior-agent" ? (
            <RiskAgentLiveOutput agentSlug={slug} onLog={handleLog} onAnalysisComplete={handleAnalysisComplete} />
          ) : slug === "behavior-agent" ? (
            <BehaviorAgentLive agentSlug={slug} onLog={handleLog} onAnalysisComplete={handleAnalysisComplete} />
          ) : slug === "data-agent" ? (
            <DataAgentLive agentSlug={slug} onLog={handleLog} />
          ) : (
            <AgentOutput agentSlug={slug} />
          )}
        </motion.div>

        {/* Right Panel - Terminal Logs */}
        <motion.div
          initial={{ opacity: 0, x: 10 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 0.1 }}
          className="h-full min-h-[400px] lg:col-span-4"
        >
          <TerminalLogs agentSlug={slug} liveLogs={(slug === "risk-behavior-agent" || slug === "behavior-agent" || slug === "data-agent") && liveLogs.length > 0 ? liveLogs : undefined} />
        </motion.div>
      </div>
    </div>
  )
}
