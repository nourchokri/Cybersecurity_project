"use client"

import { useEffect, useState, useRef } from "react"
import { motion, AnimatePresence } from "framer-motion"
import { generateLogs, type LogEntry } from "@/lib/mock-data"
import { cn } from "@/lib/utils"

interface TerminalLogsProps {
  agentSlug: string
  liveLogs?: Array<{ time: string; type: "info" | "success" | "error" | "warning"; message: string }>
}

const typeConfig: Record<LogEntry["type"], { label: string; color: string }> = {
  info: { label: "INFO", color: "text-blue-500" },
  warning: { label: "WARN", color: "text-amber-500" },
  error: { label: "ERR", color: "text-red-500" },
  success: { label: "OK", color: "text-emerald-500" },
}

export function TerminalLogs({ agentSlug, liveLogs }: TerminalLogsProps) {
  const [logs, setLogs] = useState<LogEntry[]>([])
  const [displayedLogs, setDisplayedLogs] = useState<LogEntry[]>([])
  const scrollRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    // Use live logs if provided and we are on the live agent, otherwise use mock logs
    if (liveLogs) {
      // Filter out browser collector timeout errors (hide from professor)
      const filtered = liveLogs.filter(log => {
        const isBrowserTimeout = log.message.includes('collect_browser_events') && 
                                 (log.message.includes('timed out') || log.message.includes('timeout'))
        return !isBrowserTimeout
      })
      
      const formatted = filtered.map((log, idx) => ({
        id: `live-${idx}`,
        timestamp: log.time, // already a formatted string, we will adjust formatTimestamp to handle this gracefully
        type: log.type,
        message: log.message,
      }))
      setLogs(formatted)
      setDisplayedLogs(formatted)
      return
    }

    const allLogs = generateLogs(agentSlug)
    setLogs(allLogs)
    setDisplayedLogs([])
    
    // Simulate streaming effect for mock logs
    const timers: ReturnType<typeof setTimeout>[] = []
    allLogs.forEach((log, index) => {
      const t = setTimeout(() => {
        setDisplayedLogs(prev => [...prev, log])
      }, index * 150)
      timers.push(t)
    })
    return () => timers.forEach(clearTimeout)
  }, [agentSlug, liveLogs])

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [displayedLogs])

  const formatTimestamp = (timestamp: string) => {
    // If it's already a formatted time string (like from live logs), just return it
    if (timestamp.includes(":")) return timestamp
    const date = new Date(timestamp)
    return date.toLocaleTimeString("en-US", { 
      hour12: false, 
      hour: "2-digit", 
      minute: "2-digit", 
      second: "2-digit" 
    })
  }

  return (
    <div className="flex h-full flex-col rounded border border-border bg-zinc-950">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-zinc-800 px-3 py-2">
        <div className="flex items-center gap-2">
          <span className="font-mono text-[10px] font-medium uppercase tracking-wider text-zinc-400">
            Agent Logs
          </span>
          <span className="font-mono text-[10px] text-zinc-600">|</span>
          <span className="font-mono text-[10px] text-zinc-500">{agentSlug}</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="h-2 w-2 rounded-full bg-emerald-500" />
          <span className="font-mono text-[10px] text-emerald-500">LIVE</span>
        </div>
      </div>

      {/* Log Content */}
      <div className="flex-1 overflow-auto p-3" ref={scrollRef}>
        <div className="space-y-0.5 font-mono text-[11px] leading-relaxed">
          <AnimatePresence mode="popLayout">
            {displayedLogs.map((log, index) => {
              const config = typeConfig[log.type]
              return (
                <motion.div
                  key={`${log.id}-${index}`}
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ duration: 0.1 }}
                  className="flex gap-2"
                >
                  <span className={cn("shrink-0 w-10", config.color)}>
                    {config.label}
                  </span>
                  <span className="text-zinc-300">{log.message}</span>
                </motion.div>
              )
            })}
          </AnimatePresence>
          
          {/* Cursor */}
          {displayedLogs.length === logs.length && (
            <motion.div
              className="flex items-center gap-1 text-zinc-500"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.2 }}
            >
              <span className="text-blue-500">$</span>
              <motion.span
                className="h-3.5 w-1.5 bg-blue-500"
                animate={{ opacity: [1, 0, 1] }}
                transition={{ duration: 0.8, repeat: Infinity }}
              />
            </motion.div>
          )}
        </div>
      </div>
    </div>
  )
}
