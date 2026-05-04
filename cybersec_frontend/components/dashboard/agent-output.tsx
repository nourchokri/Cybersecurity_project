"use client"

import { useState } from "react"
import { motion } from "framer-motion"
import { agentOutputs } from "@/lib/mock-data"
import { cn } from "@/lib/utils"
import { Card, CardContent, CardHeader } from "@/components/ui/card"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"

interface AgentOutputProps {
  agentSlug: string
}

export function AgentOutput({ agentSlug }: AgentOutputProps) {
  const output = agentOutputs[agentSlug]
  const [activeTab, setActiveTab] = useState("summary")

  if (!output) {
    return (
      <Card className="h-full rounded border-border">
        <CardContent className="flex h-full items-center justify-center">
          <p className="font-mono text-xs text-muted-foreground">NO DATA AVAILABLE</p>
        </CardContent>
      </Card>
    )
  }

  const jsonData = output.json as Record<string, unknown>

  // Extract highlighted fields
  const highlightedFields = ["risk_score", "decision", "user_id", "event_id"]
  const highlights = highlightedFields
    .filter(field => field in jsonData)
    .map(field => ({ key: field, value: jsonData[field] }))

  const getValueColor = (key: string, value: unknown) => {
    if (key === "risk_score" && typeof value === "number") {
      if (value >= 80) return "text-red-500"
      if (value >= 50) return "text-amber-500"
      return "text-emerald-500"
    }
    if (key === "decision") {
      if (value === "block_and_alert" || value === "escalate") return "text-red-500"
      if (value === "monitor") return "text-amber-500"
      return "text-emerald-500"
    }
    return "text-blue-500"
  }

  return (
    <Card className="flex h-full flex-col overflow-hidden rounded border-border">
      <CardHeader className="shrink-0 border-b border-border p-3">
        <div className="flex items-center justify-between">
          <span className="font-mono text-[10px] font-medium uppercase tracking-wider text-muted-foreground">
            Processed Output
          </span>
          <span className="rounded border border-emerald-500/30 bg-emerald-500/10 px-1.5 py-0.5 font-mono text-[9px] font-medium uppercase text-emerald-600">
            Complete
          </span>
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
            <TabsTrigger value="explanation" className="h-6 rounded px-2 font-mono text-[10px] uppercase tracking-wider">
              Details
            </TabsTrigger>
          </TabsList>

          <div className="flex-1 overflow-auto p-3">
            <TabsContent value="summary" className="m-0 h-full">
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="space-y-4"
              >
                <p className="text-xs leading-relaxed text-muted-foreground">
                  {output.summary}
                </p>

                {highlights.length > 0 && (
                  <div className="space-y-2 rounded border border-border bg-muted/30 p-3">
                    <h4 className="font-mono text-[10px] font-medium uppercase tracking-wider text-muted-foreground">
                      Key Metrics
                    </h4>
                    <div className="grid grid-cols-2 gap-2">
                      {highlights.map(({ key, value }) => (
                        <div key={key} className="rounded border border-border bg-card p-2">
                          <p className="font-mono text-[9px] uppercase tracking-wider text-muted-foreground">
                            {key.replace(/_/g, " ")}
                          </p>
                          <p className={cn(
                            "mt-0.5 font-mono text-sm font-semibold",
                            getValueColor(key, value)
                          )}>
                            {String(value)}
                          </p>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </motion.div>
            </TabsContent>

            <TabsContent value="json" className="m-0 h-full">
              <div className="h-[280px] overflow-auto rounded border border-zinc-800 bg-zinc-950">
                <motion.pre
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  className="p-3 font-mono text-[11px] leading-relaxed text-zinc-300"
                >
                  {JSON.stringify(output.json, null, 2)}
                </motion.pre>
              </div>
            </TabsContent>

            <TabsContent value="explanation" className="m-0 h-full">
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="rounded border border-border bg-muted/30 p-3"
              >
                <p className="text-xs leading-relaxed text-muted-foreground">
                  {output.explanation}
                </p>
              </motion.div>
            </TabsContent>
          </div>
        </Tabs>
      </CardContent>
    </Card>
  )
}
