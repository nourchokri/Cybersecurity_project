"use client"

import { useEffect, useState } from "react"
import { Card, CardContent, CardHeader } from "@/components/ui/card"
import { AlertTriangle, Shield } from "lucide-react"

interface AttackTheaterProps {
  isActive: boolean
  lastAttack?: {
    technique: string
    attack_name: string
  }
}

export function AttackTheater({ isActive, lastAttack }: AttackTheaterProps) {
  const [isAttacking, setIsAttacking] = useState(false)

  useEffect(() => {
    if (lastAttack) {
      // Flash red when attack happens
      setIsAttacking(true)
      setTimeout(() => setIsAttacking(false), 2000)
    }
  }, [lastAttack])

  return (
    <Card className={`transition-all duration-500 ${isAttacking ? 'border-red-500 bg-red-500/10' : 'border-border'}`}>
      <CardHeader className="border-b border-border p-3">
        <div className="flex items-center justify-between">
          <span className="font-mono text-[10px] font-medium uppercase tracking-wider text-muted-foreground">
            Attack Simulation Status
          </span>
          {isAttacking && (
            <div className="flex items-center gap-2 text-red-500 animate-pulse">
              <AlertTriangle className="h-4 w-4" />
              <span className="text-xs font-bold">ATTACK IN PROGRESS</span>
            </div>
          )}
        </div>
      </CardHeader>
      <CardContent className="p-6">
        <div className={`rounded-lg border-2 p-8 text-center transition-all duration-500 ${
          isAttacking 
            ? 'border-red-500 bg-red-500/20 shadow-lg shadow-red-500/50' 
            : 'border-border bg-muted/30'
        }`}>
          <div className={`mb-4 flex justify-center transition-all duration-500 ${isAttacking ? 'animate-bounce' : ''}`}>
            {isAttacking ? (
              <AlertTriangle className={`h-16 w-16 text-red-500`} />
            ) : (
              <Shield className="h-16 w-16 text-muted-foreground" />
            )}
          </div>
          
          {lastAttack ? (
            <div className="space-y-2">
              <div className={`text-lg font-bold transition-colors ${isAttacking ? 'text-red-500' : 'text-foreground'}`}>
                {lastAttack.attack_name}
              </div>
              <div className="text-sm text-muted-foreground">
                <span className="font-mono">{lastAttack.technique}</span>
              </div>
              {isAttacking && (
                <div className="mt-4 text-xs text-red-500 font-bold animate-pulse">
                  SIMULATED ATTACK DETECTED
                </div>
              )}
            </div>
          ) : (
            <div className="space-y-2">
              <div className="text-lg font-bold text-muted-foreground">
                System Monitoring
              </div>
              <div className="text-sm text-muted-foreground">
                Waiting for attack simulation...
              </div>
            </div>
          )}
        </div>

        {isActive && !isAttacking && (
          <div className="mt-4 text-center text-xs text-muted-foreground">
            <div className="inline-flex items-center gap-2">
              <div className="w-2 h-2 bg-emerald-500 rounded-full animate-pulse"></div>
              Agent running - monitoring for attacks
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
