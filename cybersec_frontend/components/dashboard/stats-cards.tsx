"use client"

import * as React from "react"
import { motion } from "framer-motion"
import { Card, CardContent } from "@/components/ui/card"
import { agents } from "@/lib/mock-data"
import { 
  Activity, 
  ShieldCheck, 
  AlertTriangle, 
  Clock 
} from "lucide-react"
import { cn } from "@/lib/utils"

const getStats = () => [
  {
    label: "EVENTS PROCESSED",
    value: agents.reduce((acc, a) => acc + a.metrics.eventsProcessed, 0).toLocaleString(),
    icon: Activity,
    color: "text-blue-600",
    borderColor: "border-blue-500/30",
    bgColor: "bg-blue-500/10",
  },
  {
    label: "AGENTS ONLINE",
    value: agents.filter(a => a.status === "processing" || a.status === "completed").length + "/" + agents.length,
    icon: ShieldCheck,
    color: "text-emerald-600",
    borderColor: "border-emerald-500/30",
    bgColor: "bg-emerald-500/10",
  },
  {
    label: "ALERTS",
    value: agents.reduce((acc, a) => acc + a.metrics.alertsGenerated, 0).toString(),
    icon: AlertTriangle,
    color: "text-amber-600",
    borderColor: "border-amber-500/30",
    bgColor: "bg-amber-500/10",
  },
  {
    label: "AVG RESPONSE",
    value: "177ms",
    icon: Clock,
    color: "text-zinc-600 dark:text-zinc-400",
    borderColor: "border-zinc-500/30",
    bgColor: "bg-zinc-500/10",
  },
]

export function StatsCards() {
  const [mounted, setMounted] = React.useState(false)
  
  React.useEffect(() => {
    setMounted(true)
  }, [])
  
  const stats = getStats()
  
  if (!mounted) {
    return (
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {stats.map((stat) => (
          <Card key={stat.label} className="rounded border-border">
            <CardContent className="p-3">
              <div className="flex items-start justify-between">
                <div>
                  <p className="font-mono text-[10px] font-medium uppercase tracking-wider text-muted-foreground">
                    {stat.label}
                  </p>
                  <p className="mt-1 font-mono text-xl font-bold">—</p>
                </div>
                <div className={cn(
                  "flex h-8 w-8 items-center justify-center rounded border",
                  stat.borderColor,
                  stat.bgColor
                )}>
                  <stat.icon className={cn("h-4 w-4", stat.color)} />
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    )
  }
  
  return (
    <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
      {stats.map((stat, index) => (
        <motion.div
          key={stat.label}
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: index * 0.05 }}
        >
          <Card className="rounded border-border">
            <CardContent className="p-3">
              <div className="flex items-start justify-between">
                <div>
                  <p className="font-mono text-[10px] font-medium uppercase tracking-wider text-muted-foreground">
                    {stat.label}
                  </p>
                  <p className="mt-1 font-mono text-xl font-bold">{stat.value}</p>
                </div>
                <div className={cn(
                  "flex h-8 w-8 items-center justify-center rounded border",
                  stat.borderColor,
                  stat.bgColor
                )}>
                  <stat.icon className={cn("h-4 w-4", stat.color)} />
                </div>
              </div>
            </CardContent>
          </Card>
        </motion.div>
      ))}
    </div>
  )
}
