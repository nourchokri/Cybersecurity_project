"use client"

import { motion } from "framer-motion"
import Link from "next/link"
import { agents, type AgentStatus } from "@/lib/mock-data"
import { cn } from "@/lib/utils"
import { 
  Database, 
  Brain, 
  AlertTriangle, 
  Swords,
  Shield,
  CheckCircle2,
  Loader2,
  Clock,
  AlertCircle
} from "lucide-react"

const agentIcons = {
  "data-agent": Database,
  "behavior-agent": Brain,
  "risk-behavior-agent": AlertTriangle,
  "attacker-agent": Swords,
  "response-agent": Shield,
}

const statusConfig: Record<AgentStatus, { 
  icon: typeof CheckCircle2
  color: string
  bgColor: string
  borderColor: string
  label: string
}> = {
  completed: {
    icon: CheckCircle2,
    color: "text-emerald-600",
    bgColor: "bg-emerald-500/10",
    borderColor: "border-emerald-500/30",
    label: "COMPLETE"
  },
  processing: {
    icon: Loader2,
    color: "text-blue-600",
    bgColor: "bg-blue-500/10",
    borderColor: "border-blue-500/30",
    label: "ACTIVE"
  },
  idle: {
    icon: Clock,
    color: "text-zinc-500",
    bgColor: "bg-zinc-500/10",
    borderColor: "border-zinc-500/30",
    label: "IDLE"
  },
  alert: {
    icon: AlertCircle,
    color: "text-red-600",
    bgColor: "bg-red-500/10",
    borderColor: "border-red-500/30",
    label: "ALERT"
  }
}

export type PipelineSource = "data-agent" | "attacker-agent"

interface PipelineVisualizationProps {
  agentStatuses?: Record<string, AgentStatus>
  pipelineSource?: PipelineSource
  onSourceChange?: (source: PipelineSource) => void
}

function AgentNode({ 
  agent, 
  currentStatus, 
  index, 
  isActive, 
  isSourceNode,
  dimmed
}: { 
  agent: typeof agents[0]
  currentStatus: AgentStatus
  index: number
  isActive: boolean
  isSourceNode: boolean
  dimmed: boolean
}) {
  const Icon = agentIcons[agent.slug as keyof typeof agentIcons]
  const config = statusConfig[currentStatus]
  const StatusIcon = config.icon
  const isProcessing = currentStatus === "processing"

  return (
    <Link href={`/agents/${agent.slug}`}>
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: index * 0.08 }}
        className={cn(
          "group relative flex h-28 w-36 cursor-pointer flex-col items-center justify-center rounded border-2 p-3 transition-all",
          dimmed 
            ? "border-zinc-700/30 bg-zinc-800/20 opacity-40" 
            : cn(config.bgColor, config.borderColor, "hover:border-blue-500/50"),
          isSourceNode && !dimmed && "ring-1 ring-blue-500/30"
        )}
      >
        {/* Icon */}
        <div className={cn(
          "mb-2 flex h-10 w-10 items-center justify-center rounded border",
          dimmed ? "border-zinc-700/30 bg-zinc-800/20" : cn(config.borderColor, config.bgColor)
        )}>
          <Icon className={cn("h-5 w-5", dimmed ? "text-zinc-600" : config.color)} />
        </div>

        {/* Agent Name */}
        <h3 className={cn(
          "text-center text-[11px] font-medium",
          dimmed ? "text-zinc-600" : "text-foreground"
        )}>
          {agent.name}
        </h3>

        {/* Status Badge */}
        <div className={cn(
          "mt-1.5 flex items-center gap-1 rounded px-1.5 py-0.5 font-mono text-[9px] font-medium uppercase tracking-wider",
          dimmed ? "bg-zinc-800/20 text-zinc-600" : cn(config.bgColor, config.color)
        )}>
          <StatusIcon className={cn(
            "h-2.5 w-2.5",
            isProcessing && !dimmed && "animate-spin"
          )} />
          {dimmed ? "INACTIVE" : config.label}
        </div>
      </motion.div>
    </Link>
  )
}

function Connector({ animated, dimmed, index }: { animated?: boolean; dimmed?: boolean; index: number }) {
  return (
    <div className={cn("relative mx-1 h-0.5 w-12", dimmed && "opacity-30")}>
      {/* Static line */}
      <div className="absolute inset-0 bg-border" />
      
      {/* Animated pulse */}
      {!dimmed && (
        <motion.div
          className="absolute inset-y-0 left-0 w-4 bg-blue-500"
          animate={{
            x: [0, 32, 0],
            opacity: [0.8, 0.3, 0.8],
          }}
          transition={{
            duration: 1.5,
            repeat: Infinity,
            ease: "easeInOut",
            delay: index * 0.2,
          }}
        />
      )}
    </div>
  )
}

export function PipelineVisualization({ agentStatuses, pipelineSource = "data-agent", onSourceChange }: PipelineVisualizationProps) {
  const dataAgent = agents.find(a => a.slug === "data-agent")!
  const attackerAgent = agents.find(a => a.slug === "attacker-agent")!
  
  // Downstream agents (after the source)
  const downstreamSlugs = ["behavior-agent", "risk-behavior-agent", "response-agent"]
  const downstreamAgents = downstreamSlugs.map(slug => agents.find(a => a.slug === slug)!).filter(Boolean)

  const isDataActive = pipelineSource === "data-agent"
  const isAttackerActive = pipelineSource === "attacker-agent"

  const getStatus = (slug: string): AgentStatus => {
    return agentStatuses?.[slug] ?? "idle"
  }

  return (
    <div className="relative w-full overflow-x-auto py-4">
      <div className="flex min-w-max items-center justify-center gap-0 px-4">
        {/* Source Selection - Two parallel entry points */}
        <div className="flex flex-col items-center gap-2">
          {/* Data Agent - Top */}
          <div 
            className="cursor-pointer" 
            onClick={(e) => { e.preventDefault(); onSourceChange?.("data-agent") }}
          >
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              className={cn(
                "group relative flex h-[52px] w-36 cursor-pointer flex-col items-center justify-center rounded border-2 p-2 transition-all",
                isDataActive 
                  ? cn(
                      statusConfig[getStatus("data-agent")].bgColor,
                      statusConfig[getStatus("data-agent")].borderColor,
                      "ring-2 ring-blue-500/40"
                    )
                  : "border-zinc-700/30 bg-zinc-800/20 opacity-50 hover:opacity-70"
              )}
            >
              <div className="flex items-center gap-2">
                <Database className={cn(
                  "h-4 w-4",
                  isDataActive ? statusConfig[getStatus("data-agent")].color : "text-zinc-600"
                )} />
                <span className={cn(
                  "text-[11px] font-medium",
                  isDataActive ? "text-foreground" : "text-zinc-600"
                )}>
                  Data Agent
                </span>
              </div>
              {isDataActive && (
                <div className={cn(
                  "mt-1 flex items-center gap-1 rounded px-1.5 py-0.5 font-mono text-[8px] font-medium uppercase tracking-wider",
                  statusConfig[getStatus("data-agent")].bgColor,
                  statusConfig[getStatus("data-agent")].color
                )}>
                  {(() => {
                    const s = getStatus("data-agent")
                    const SIcon = statusConfig[s].icon
                    return <><SIcon className={cn("h-2 w-2", s === "processing" && "animate-spin")} /><span>{statusConfig[s].label}</span></>
                  })()}
                </div>
              )}
            </motion.div>
          </div>

          {/* Attacker Agent - Bottom */}
          <div 
            className="cursor-pointer"
            onClick={(e) => { e.preventDefault(); onSourceChange?.("attacker-agent") }}
          >
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.05 }}
              className={cn(
                "group relative flex h-[52px] w-36 cursor-pointer flex-col items-center justify-center rounded border-2 p-2 transition-all",
                isAttackerActive 
                  ? cn(
                      statusConfig[getStatus("attacker-agent")].bgColor,
                      statusConfig[getStatus("attacker-agent")].borderColor,
                      "ring-2 ring-red-500/40"
                    )
                  : "border-zinc-700/30 bg-zinc-800/20 opacity-50 hover:opacity-70"
              )}
            >
              <div className="flex items-center gap-2">
                <Swords className={cn(
                  "h-4 w-4",
                  isAttackerActive ? "text-red-500" : "text-zinc-600"
                )} />
                <span className={cn(
                  "text-[11px] font-medium",
                  isAttackerActive ? "text-foreground" : "text-zinc-600"
                )}>
                  Attacker Agent
                </span>
              </div>
              {isAttackerActive && (
                <div className={cn(
                  "mt-1 flex items-center gap-1 rounded px-1.5 py-0.5 font-mono text-[8px] font-medium uppercase tracking-wider",
                  statusConfig[getStatus("attacker-agent")].bgColor,
                  statusConfig[getStatus("attacker-agent")].color
                )}>
                  {(() => {
                    const s = getStatus("attacker-agent")
                    const SIcon = statusConfig[s].icon
                    return <><SIcon className={cn("h-2 w-2", s === "processing" && "animate-spin")} /><span>{statusConfig[s].label}</span></>
                  })()}
                </div>
              )}
            </motion.div>
          </div>
        </div>

        {/* Merge Connector */}
        <div className="relative mx-1 flex h-[110px] w-16 flex-col items-end justify-center">
          {/* Top line from Data Agent */}
          <svg className="absolute inset-0 h-full w-full" viewBox="0 0 64 110" fill="none">
            <path
              d={`M 0 28 Q 32 28 52 55`}
              stroke={isDataActive ? "rgb(59, 130, 246)" : "rgb(63, 63, 70)"}
              strokeWidth="2"
              strokeOpacity={isDataActive ? 0.6 : 0.3}
              fill="none"
            />
            <path
              d={`M 0 82 Q 32 82 52 55`}
              stroke={isAttackerActive ? "rgb(239, 68, 68)" : "rgb(63, 63, 70)"}
              strokeWidth="2"
              strokeOpacity={isAttackerActive ? 0.6 : 0.3}
              fill="none"
            />
            <line 
              x1="52" y1="55" x2="64" y2="55" 
              stroke={isDataActive ? "rgb(59, 130, 246)" : isAttackerActive ? "rgb(239, 68, 68)" : "rgb(63, 63, 70)"} 
              strokeWidth="2"
              strokeOpacity={0.6}
            />
          </svg>
          {/* Animated dot on active path */}
          {(isDataActive || isAttackerActive) && (
            <motion.div
              className={cn(
                "absolute h-2 w-2 rounded-full",
                isDataActive ? "bg-blue-500" : "bg-red-500"
              )}
              animate={{
                offsetDistance: ["0%", "100%"],
                opacity: [1, 0.4, 1],
              }}
              transition={{
                duration: 2,
                repeat: Infinity,
                ease: "easeInOut",
              }}
              style={{
                right: 0,
                top: "50%",
                transform: "translateY(-50%)",
              }}
            />
          )}
        </div>

        {/* Downstream Agents */}
        {downstreamAgents.map((agent, index) => {
          const currentStatus = getStatus(agent.slug)
          const config = statusConfig[currentStatus]
          const Icon = agentIcons[agent.slug as keyof typeof agentIcons]
          const StatusIcon = config.icon
          const isProcessing = currentStatus === "processing"

          return (
            <div key={agent.id} className="flex items-center">
              <Link href={`/agents/${agent.slug}`}>
                <motion.div
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: (index + 2) * 0.08 }}
                  className={cn(
                    "group relative flex h-28 w-36 cursor-pointer flex-col items-center justify-center rounded border-2 p-3 transition-all hover:border-blue-500/50",
                    config.bgColor,
                    config.borderColor
                  )}
                >
                  <div className={cn(
                    "mb-2 flex h-10 w-10 items-center justify-center rounded border",
                    config.borderColor,
                    config.bgColor
                  )}>
                    <Icon className={cn("h-5 w-5", config.color)} />
                  </div>
                  <h3 className="text-center text-[11px] font-medium text-foreground">
                    {agent.name}
                  </h3>
                  <div className={cn(
                    "mt-1.5 flex items-center gap-1 rounded px-1.5 py-0.5 font-mono text-[9px] font-medium uppercase tracking-wider",
                    config.bgColor,
                    config.color
                  )}>
                    <StatusIcon className={cn(
                      "h-2.5 w-2.5",
                      isProcessing && "animate-spin"
                    )} />
                    {config.label}
                  </div>
                </motion.div>
              </Link>

              {/* Connector Line */}
              {index < downstreamAgents.length - 1 && (
                <Connector index={index + 2} />
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}
