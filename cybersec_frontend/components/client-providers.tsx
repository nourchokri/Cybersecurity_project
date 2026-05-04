"use client"

import { PipelineProvider } from "@/lib/pipeline-store"

export function ClientProviders({ children }: { children: React.ReactNode }) {
  return (
    <PipelineProvider>
      {children}
    </PipelineProvider>
  )
}
