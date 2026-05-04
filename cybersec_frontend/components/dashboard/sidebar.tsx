"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import { cn } from "@/lib/utils"
import { 
  Home, 
  Database, 
  Brain, 
  AlertTriangle, 
  Shield, 
  FileText,
  Activity,
  Swords
} from "lucide-react"

const navItems = [
  { name: "Overview", href: "/", icon: Home },
  { name: "Data Agent", href: "/agents/data-agent", icon: Database },
  { name: "Attacker Agent", href: "/agents/attacker-agent", icon: Swords },
  { name: "Behavior Agent", href: "/agents/behavior-agent", icon: Brain },
  { name: "Risk Agent", href: "/agents/risk-behavior-agent", icon: AlertTriangle },
  { name: "Response Agent", href: "/agents/response-agent", icon: Shield },
  { name: "Reporting Agent", href: "/agents/reporting-agent", icon: FileText },
]

export function Sidebar() {
  const pathname = usePathname()

  return (
    <aside className="fixed left-0 top-0 z-40 h-screen w-64 border-r border-border bg-sidebar">
      <div className="flex h-full flex-col">
        {/* Logo */}
        <div className="flex h-16 items-center gap-3 border-b border-sidebar-border px-5">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-blue-600">
            <Activity className="h-5 w-5 text-white" />
          </div>
          <div className="flex flex-col">
            <span className="font-mono text-sm font-bold uppercase tracking-wider text-sidebar-foreground">CYBER AI</span>
            <span className="font-mono text-xs uppercase tracking-wide text-muted-foreground">Pipeline v2.1</span>
          </div>
        </div>

        {/* Navigation */}
        <nav className="flex-1 px-3 py-4">
          <div className="mb-3 px-2">
            <span className="font-mono text-xs font-medium uppercase tracking-wider text-muted-foreground">
              Navigation
            </span>
          </div>
          <div className="space-y-1">
            {navItems.map((item) => {
              const isActive = pathname === item.href || 
                (item.href !== "/" && pathname.startsWith(item.href))
              
              return (
                <Link
                  key={item.name}
                  href={item.href}
                  className={cn(
                    "group flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors",
                    isActive
                      ? "border-l-2 border-blue-500 bg-blue-500/10 text-blue-600 dark:text-blue-400"
                      : "text-muted-foreground hover:bg-muted hover:text-foreground"
                  )}
                >
                  <item.icon className={cn(
                    "h-5 w-5",
                    isActive 
                      ? "text-blue-600 dark:text-blue-400" 
                      : "text-muted-foreground group-hover:text-foreground"
                  )} />
                  <span>{item.name}</span>
                </Link>
              )
            })}
          </div>
        </nav>

        {/* Footer Status */}
        <div className="border-t border-sidebar-border p-4">
          <div className="rounded-lg border border-border bg-muted/50 p-3">
            <div className="flex items-center justify-between">
              <span className="font-mono text-xs uppercase tracking-wider text-muted-foreground">
                System
              </span>
              <span className="flex items-center gap-1.5 font-mono text-xs font-medium text-emerald-600">
                <span className="h-2 w-2 rounded-full bg-emerald-500" />
                ONLINE
              </span>
            </div>
            <div className="mt-2 flex items-center justify-between">
              <span className="font-mono text-xs text-muted-foreground">Agents</span>
              <span className="font-mono text-xs font-medium text-foreground">6/6</span>
            </div>
          </div>
        </div>
      </div>
    </aside>
  )
}
