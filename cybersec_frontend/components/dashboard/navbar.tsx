"use client"

import { useTheme } from "next-themes"
import { Moon, Sun, User, Bell } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Avatar, AvatarFallback } from "@/components/ui/avatar"
import { getSystemStatus, type SystemStatus } from "@/lib/mock-data"
import { cn } from "@/lib/utils"
import { useEffect, useState } from "react"

const statusConfig: Record<SystemStatus, { label: string; color: string; borderColor: string }> = {
  active: { 
    label: "ACTIVE", 
    color: "bg-emerald-500", 
    borderColor: "border-emerald-500/30 text-emerald-600 dark:text-emerald-400"
  },
  idle: { 
    label: "IDLE", 
    color: "bg-amber-500", 
    borderColor: "border-amber-500/30 text-amber-600 dark:text-amber-400"
  },
  alert: { 
    label: "ALERT", 
    color: "bg-red-500", 
    borderColor: "border-red-500/30 text-red-600 dark:text-red-400"
  },
}

export function Navbar() {
  const { theme, setTheme } = useTheme()
  const [mounted, setMounted] = useState(false)
  const status = getSystemStatus()
  const config = statusConfig[status]

  const [currentTime, setCurrentTime] = useState("")

  useEffect(() => {
    setMounted(true)
    const update = () =>
      setCurrentTime(
        new Date().toLocaleTimeString("en-US", {
          hour12: false,
          hour: "2-digit",
          minute: "2-digit",
          second: "2-digit",
        })
      )
    update()
    const interval = setInterval(update, 1000)
    return () => clearInterval(interval)
  }, [])

  return (
    <header className="sticky top-0 z-30 flex h-14 items-center justify-between border-b border-border bg-card px-6">
      {/* Left side - Status & Time */}
      <div className="flex items-center gap-4">
        <div className={cn(
          "flex items-center gap-2 rounded-md border px-3 py-1.5 font-mono text-xs font-medium uppercase tracking-wider",
          config.borderColor
        )}>
          <span className="relative flex h-1.5 w-1.5">
            <span className={cn(
              "absolute inline-flex h-full w-full animate-ping rounded-full opacity-75",
              config.color
            )} />
            <span className={cn(
              "relative inline-flex h-1.5 w-1.5 rounded-full",
              config.color
            )} />
          </span>
          {config.label}
        </div>
        <div className="hidden items-center gap-2 font-mono text-xs text-muted-foreground sm:flex">
          <span className="uppercase tracking-wider">UTC</span>
          <span className="font-medium text-foreground">{currentTime}</span>
        </div>
      </div>

      {/* Right side - Actions */}
      <div className="flex items-center gap-2">
        {/* Notifications */}
        <Button
          variant="ghost"
          size="icon"
          className="relative h-9 w-9 rounded-md"
        >
          <Bell className="h-[18px] w-[18px]" />
          <span className="absolute -right-0.5 -top-0.5 flex h-4 w-4 items-center justify-center rounded-full bg-red-500 font-mono text-[9px] font-bold text-white">
            3
          </span>
          <span className="sr-only">Notifications</span>
        </Button>

        {/* Theme Toggle */}
        <Button
          variant="ghost"
          size="icon"
          onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
          className="h-9 w-9 rounded-md"
        >
          {mounted && (
            <>
              <Sun className="h-[18px] w-[18px] rotate-0 scale-100 transition-all dark:-rotate-90 dark:scale-0" />
              <Moon className="absolute h-[18px] w-[18px] rotate-90 scale-0 transition-all dark:rotate-0 dark:scale-100" />
            </>
          )}
          <span className="sr-only">Toggle theme</span>
        </Button>

        {/* Divider */}
        <div className="h-6 w-px bg-border" />

        {/* User */}
        <div className="flex items-center gap-2">
          <div className="hidden text-right sm:block">
            <p className="text-sm font-medium">SOC Admin</p>
            <p className="font-mono text-xs text-muted-foreground">admin@soc.local</p>
          </div>
          <Avatar className="h-8 w-8 rounded-md border border-border">
            <AvatarFallback className="rounded-md bg-muted text-xs font-medium">
              SA
            </AvatarFallback>
          </Avatar>
        </div>
      </div>
    </header>
  )
}
