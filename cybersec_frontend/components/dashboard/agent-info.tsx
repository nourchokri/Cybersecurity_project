"use client"

import { motion } from "framer-motion"
import { agents } from "@/lib/mock-data"
import { cn } from "@/lib/utils"
import { Card, CardContent, CardHeader } from "@/components/ui/card"
import { 
  Database, 
  Brain, 
  AlertTriangle, 
  Shield, 
  FileText,
  ArrowRight,
  Activity,
  Zap,
  Swords
} from "lucide-react"

interface AgentInfoProps {
  agentSlug: string
  statusOverride?: "idle" | "processing" | "completed" | "alert"
  metricsOverride?: {
    eventsProcessed: number
    alertsGenerated: number
    avgProcessingTime: string
  }
}

const agentIcons = {
  "data-agent": Database,
  "attacker-agent": Swords,
  "behavior-agent": Brain,
  "risk-behavior-agent": AlertTriangle,
  "response-agent": Shield,
  "reporting-agent": FileText,
}

const statusConfig = {
  completed: { label: "COMPLETED", color: "text-emerald-600 border-emerald-500/30 bg-emerald-500/10" },
  processing: { label: "PROCESSING", color: "text-blue-600 border-blue-500/30 bg-blue-500/10" },
  idle: { label: "IDLE", color: "text-zinc-500 border-zinc-500/30 bg-zinc-500/10" },
  alert: { label: "ALERT", color: "text-red-600 border-red-500/30 bg-red-500/10" },
}

export function AgentInfo({ agentSlug, statusOverride, metricsOverride }: AgentInfoProps) {
  const agent = agents.find(a => a.slug === agentSlug)

  if (!agent) {
    return (
      <Card className="rounded border-border">
        <CardContent className="flex h-full items-center justify-center py-8">
          <p className="font-mono text-xs text-muted-foreground">AGENT NOT FOUND</p>
        </CardContent>
      </Card>
    )
  }

  const Icon = agentIcons[agent.slug as keyof typeof agentIcons]
  const effectiveStatus = statusOverride || agent.status
  const status = statusConfig[effectiveStatus]
  const metricsToUse = metricsOverride || agent.metrics

  return (
    <motion.div
      initial={{ opacity: 0, x: -20 }}
      animate={{ opacity: 1, x: 0 }}
      className="space-y-3"
    >
      {/* Agent Header Card */}
      <Card className="overflow-hidden rounded border-border">
        <CardHeader className="border-b border-border p-3">
          <div className="flex items-start gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded border border-blue-500/30 bg-blue-500/10">
              <Icon className="h-5 w-5 text-blue-600" />
            </div>
            <div className="flex-1 min-w-0">
              <h2 className="text-sm font-semibold text-foreground">{agent.name}</h2>
              <p className="font-mono text-[10px] uppercase tracking-wider text-muted-foreground">{agent.role}</p>
            </div>
          </div>
        </CardHeader>
        <CardContent className="p-3">
          <p className="text-xs leading-relaxed text-muted-foreground">
            {agent.description}
          </p>
        </CardContent>
      </Card>

      {/* Status Card */}
      <Card className="rounded border-border">
        <CardHeader className="p-3 pb-2">
          <span className="font-mono text-[10px] font-medium uppercase tracking-wider text-muted-foreground">
            Status
          </span>
        </CardHeader>
        <CardContent className="p-3 pt-0">
          <div className="flex items-center justify-between">
            <span className={cn(
              "rounded border px-2.5 py-1 font-mono text-xs font-medium uppercase tracking-wider",
              status.color
            )}>
              {status.label}
            </span>
            <span className="font-mono text-xs text-muted-foreground">
              {agent.lastUpdated}
            </span>
          </div>
        </CardContent>
      </Card>

      {/* Data Flow Card */}
      <Card className="rounded border-border">
        <CardHeader className="p-3 pb-2">
          <span className="font-mono text-[10px] font-medium uppercase tracking-wider text-muted-foreground">
            Data Flow
          </span>
        </CardHeader>
        <CardContent className="space-y-2 p-3 pt-0">
          <div className="flex items-center gap-2 rounded border border-border bg-muted/30 p-2">
            <ArrowRight className="h-3 w-3 text-blue-500" />
            <div className="flex-1">
              <p className="font-mono text-[9px] uppercase tracking-wider text-muted-foreground">Input</p>
              <p className="text-xs font-medium">{agent.inputType}</p>
            </div>
          </div>
          <div className="flex items-center gap-2 rounded border border-border bg-muted/30 p-2">
            <ArrowRight className="h-3 w-3 text-emerald-500" />
            <div className="flex-1">
              <p className="font-mono text-[9px] uppercase tracking-wider text-muted-foreground">Output</p>
              <p className="text-xs font-medium">{agent.outputType}</p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Metrics Card */}
      <Card className="rounded border-border">
        <CardHeader className="p-3 pb-2">
          <span className="font-mono text-[10px] font-medium uppercase tracking-wider text-muted-foreground">
            Metrics
          </span>
        </CardHeader>
        <CardContent className="p-3 pt-0">
          <div className="space-y-2">
            <div className="flex items-center justify-between rounded border border-border bg-muted/30 p-2">
              <div className="flex items-center gap-2">
                <Activity className="h-3 w-3 text-blue-500" />
                <span className="font-mono text-[10px] uppercase tracking-wider text-muted-foreground">Events</span>
              </div>
              <span className="font-mono text-xs font-semibold" suppressHydrationWarning>
                {metricsToUse.eventsProcessed.toLocaleString()}
              </span>
            </div>
            <div className="flex items-center justify-between rounded border border-border bg-muted/30 p-2">
              <div className="flex items-center gap-2">
                <AlertTriangle className="h-3 w-3 text-amber-500" />
                <span className="font-mono text-[10px] uppercase tracking-wider text-muted-foreground">Alerts</span>
              </div>
              <span className="font-mono text-xs font-semibold">
                {metricsToUse.alertsGenerated}
              </span>
            </div>
            <div className="flex items-center justify-between rounded border border-border bg-muted/30 p-2">
              <div className="flex items-center gap-2">
                <Zap className="h-3 w-3 text-emerald-500" />
                <span className="font-mono text-[10px] uppercase tracking-wider text-muted-foreground">Avg Time</span>
              </div>
              <span className="font-mono text-xs font-semibold">
                {metricsToUse.avgProcessingTime}
              </span>
            </div>
          </div>
        </CardContent>
      </Card>
    </motion.div>
  )
}
