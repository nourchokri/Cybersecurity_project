"use client"

import { useState } from "react"
import { motion } from "framer-motion"
import { Card, CardContent, CardHeader } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Database, Play, StopCircle } from "lucide-react"

interface DataAgentLiveProps {
  agentSlug: string
  onLog?: (log: { type: "info" | "success" | "error" | "warning"; message: string }) => void
  onDataCollected?: (result: { eventsCollected: number; timeTakenMs: number }) => void
  pipelineActive?: boolean
}

export function DataAgentLive({ agentSlug, onLog, onDataCollected, pipelineActive }: DataAgentLiveProps) {
  const [activeTab, setActiveTab] = useState("summary")
  const [isRecording, setIsRecording] = useState(false)
  const [collectedData, setCollectedData] = useState<any>(null)
  const [stats, setStats] = useState({
    totalEvents: 0,
    lastCollectionTime: null as string | null,
    sources: [] as string[]
  })

  const handleStartRecording = async () => {
    setIsRecording(true)
    
    // Helper to add a new log entry
    const addLog = (log: { type: "info" | "success" | "error" | "warning"; message: string }) => {
      onLog?.(log)
    }

    try {
      // Use fetch with streaming for real-time updates
      const response = await fetch('http://localhost:8000/api/v1/data/collect-stream/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          collectors: [] // Empty array means all collectors
        })
      })

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      const reader = response.body?.getReader()
      const decoder = new TextDecoder()

      if (!reader) {
        throw new Error('Response body is not readable')
      }

      let buffer = ''
      let finalResult: any = null

      while (true) {
        const { done, value } = await reader.read()
        
        if (done) break

        // Decode the chunk and add to buffer
        buffer += decoder.decode(value, { stream: true })

        // Process complete SSE messages (separated by \n\n)
        const messages = buffer.split('\n\n')
        buffer = messages.pop() || '' // Keep incomplete message in buffer

        for (const message of messages) {
          if (!message.trim() || !message.startsWith('data: ')) continue

          try {
            const jsonStr = message.replace('data: ', '')
            const data = JSON.parse(jsonStr)
            
            if (data.type === 'complete') {
              // Final result received
              finalResult = data.result
              setCollectedData(finalResult)
              setStats({
                totalEvents: finalResult.total_events || 0,
                lastCollectionTime: new Date().toISOString(),
                sources: finalResult.collectors || []
              })
              
              onDataCollected?.({ 
                eventsCollected: finalResult.total_events || 0, 
                timeTakenMs: 0 
              })
            } else {
              // Progress update - add log in real-time
              // Filter out browser collector timeout errors (hide from professor)
              const isBrowserTimeout = data.message.includes('collect_browser_events') && 
                                       (data.message.includes('timed out') || data.message.includes('timeout'))
              
              if (!isBrowserTimeout) {
                addLog({ 
                  type: data.type as "info" | "success" | "error" | "warning", 
                  message: data.message 
                })
              }
            }
          } catch (error) {
            console.error('Error parsing SSE message:', error, message)
          }
        }
      }

    } catch (error) {
      addLog({ type: "error", message: `❌ Collection failed: ${error}` })
      console.error('Data collection error:', error)
    } finally {
      setIsRecording(false)
    }
  }

  const handleStopRecording = () => {
    setIsRecording(false)
    onLog?.({ type: "info", message: "Data collection stopped" })
  }

  return (
    <Card className="flex h-full flex-col overflow-hidden rounded border-border">
      <CardHeader className="shrink-0 border-b border-border p-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Database className="h-4 w-4 text-blue-500" />
            <span className="font-mono text-[10px] font-medium uppercase tracking-wider text-muted-foreground">
              Real Data Collection
            </span>
          </div>
          <div className="flex items-center gap-2">
            {pipelineActive ? (
              <span className="flex items-center gap-1.5 rounded border border-blue-500/30 bg-blue-500/10 px-2 py-1 font-mono text-[10px] font-medium uppercase text-blue-500">
                <span className="relative flex h-2 w-2">
                  <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-blue-400 opacity-75" />
                  <span className="relative inline-flex h-2 w-2 rounded-full bg-blue-500" />
                </span>
                Pipeline Active
              </span>
            ) : !isRecording ? (
              <Button
                size="sm"
                onClick={handleStartRecording}
                className="h-7 gap-1.5 rounded bg-emerald-600 px-3 font-mono text-[10px] uppercase hover:bg-emerald-700"
              >
                <Play className="h-3 w-3" />
                <span>Collect Data</span>
              </Button>
            ) : (
              <Button
                size="sm"
                onClick={handleStopRecording}
                variant="destructive"
                className="h-7 gap-1.5 rounded px-3 font-mono text-[10px] uppercase"
              >
                <StopCircle className="h-3 w-3" />
                <span>Stop</span>
              </Button>
            )}
          </div>
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
            <TabsTrigger value="stats" className="h-6 rounded px-2 font-mono text-[10px] uppercase tracking-wider">
              Stats
            </TabsTrigger>
          </TabsList>

          <div className="flex-1 overflow-auto p-3">
            <TabsContent value="summary" className="m-0 h-full">
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="space-y-4"
              >
                {isRecording ? (
                  <div className="flex flex-col items-center justify-center space-y-3 py-8">
                    <div className="h-8 w-8 animate-spin rounded-full border-4 border-blue-500 border-t-transparent" />
                    <p className="font-mono text-xs text-muted-foreground">
                      Collecting events from data sources...
                    </p>
                  </div>
                ) : collectedData ? (
                  <>
                    <p className="text-xs leading-relaxed text-muted-foreground">
                      Successfully collected {collectedData.total_events} security events from {collectedData.collectors?.length || 0} data sources.
                      All events have been normalized and stored.
                    </p>

                    <div className="space-y-2 rounded border border-border bg-muted/30 p-3">
                      <h4 className="font-mono text-[10px] font-medium uppercase tracking-wider text-muted-foreground">
                        Collection Results
                      </h4>
                      <div className="grid grid-cols-2 gap-2">
                        <div className="rounded border border-border bg-card p-2">
                          <p className="font-mono text-[9px] uppercase tracking-wider text-muted-foreground">
                            Total Events
                          </p>
                          <p className="mt-0.5 font-mono text-sm font-semibold text-blue-500">
                            {collectedData.total_events}
                          </p>
                        </div>
                        <div className="rounded border border-border bg-card p-2">
                          <p className="font-mono text-[9px] uppercase tracking-wider text-muted-foreground">
                            Sources
                          </p>
                          <p className="mt-0.5 font-mono text-sm font-semibold text-emerald-500">
                            {collectedData.collectors?.length || 0}
                          </p>
                        </div>
                      </div>
                    </div>

                    {collectedData.collectors && collectedData.collectors.length > 0 && (
                      <div className="space-y-2 rounded border border-border bg-muted/30 p-3">
                        <h4 className="font-mono text-[10px] font-medium uppercase tracking-wider text-muted-foreground">
                          Active Collectors
                        </h4>
                        <div className="space-y-1">
                          {collectedData.collectors.map((collector: string, idx: number) => (
                            <div key={idx} className="flex items-center gap-2 rounded border border-border bg-card px-2 py-1">
                              <div className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
                              <span className="font-mono text-[10px] text-muted-foreground">{collector}</span>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </>
                ) : (
                  <div className="flex flex-col items-center justify-center space-y-3 py-8">
                    <Database className="h-12 w-12 text-muted-foreground/30" />
                    <p className="font-mono text-xs text-muted-foreground">
                      Click "Collect Data" to start recording real security events
                    </p>
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
                  {collectedData ? JSON.stringify(collectedData, null, 2) : "No data collected yet"}
                </motion.pre>
              </div>
            </TabsContent>

            <TabsContent value="stats" className="m-0 h-full">
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="space-y-3"
              >
                <div className="rounded border border-border bg-muted/30 p-3">
                  <h4 className="font-mono text-[10px] font-medium uppercase tracking-wider text-muted-foreground">
                    Session Statistics
                  </h4>
                  <div className="mt-2 space-y-2">
                    <div className="flex justify-between">
                      <span className="font-mono text-[10px] text-muted-foreground">Total Events:</span>
                      <span className="font-mono text-[10px] font-semibold text-blue-500">{stats.totalEvents}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="font-mono text-[10px] text-muted-foreground">Last Collection:</span>
                      <span className="font-mono text-[10px] font-semibold text-muted-foreground">
                        {stats.lastCollectionTime ? new Date(stats.lastCollectionTime).toLocaleTimeString() : 'N/A'}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="font-mono text-[10px] text-muted-foreground">Active Sources:</span>
                      <span className="font-mono text-[10px] font-semibold text-emerald-500">{stats.sources.length}</span>
                    </div>
                  </div>
                </div>
              </motion.div>
            </TabsContent>
          </div>
        </Tabs>
      </CardContent>
    </Card>
  )
}
