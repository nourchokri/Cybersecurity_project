"use client"

import { useState } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { 
  Shield, 
  AlertTriangle, 
  CheckCircle, 
  Phone, 
  Brain,
  Zap,
  TrendingUp,
  Activity
} from "lucide-react"

interface DecisionOutput {
  action: string
  confidence: number
  reasoning: string
  source: string
}

interface ResponseDecision {
  event_id: string
  user_id: string
  timestamp: string
  risk_level: string
  final_action: string
  execution_status: string
  llm_weighted_decision: DecisionOutput
  llm_direct_decision: DecisionOutput
  rl_decision: DecisionOutput
  orchestrator_reasoning: string
  confidence: number
  risk_explanation: string
  action_explanation: string
  user_approval_required: boolean
  user_approval_status: string | null
  twilio_call_sid: string | null
}

const SAMPLE_EVENTS = {
  LOW: {
    event_id: "LOW_RISK_TEST",
    timestamp: new Date().toISOString(),
    user_id: "MJS0890",
    entity_id: "",
    base_score: 0.43,
    risk_adjustment: -0.3,
    adjusted_risk_score: 0.13,
    risk_level: "LOW",
    decision: "ALLOW",
    recommended_action: "log event for audit trail",
    risk_factors: [
      "Unusual behavior vs baseline (new device)",
      "High privilege + high sensitivity combination"
    ],
    mitigating_factors: [
      "Consistent with user's role and responsibilities"
    ],
    context_summary: {
      asset_sensitivity: "unavailable",
      asset_data_type: "unavailable",
      recent_incidents: "unavailable",
      triggered_rules_count: 1
    },
    confidence: "medium",
    computation_method: "llm_react_contextual",
    llm_driven: true,
    execution_logs: []
  },
  MEDIUM: {
    event_id: "MEDIUM_RISK_TEST",
    timestamp: new Date().toISOString(),
    user_id: "JDO1234",
    entity_id: "",
    base_score: 0.65,
    risk_adjustment: -0.1,
    adjusted_risk_score: 0.55,
    risk_level: "MEDIUM",
    decision: "ESCALATE",
    recommended_action: "require approval",
    risk_factors: [
      "Unusual behavior pattern",
      "Access to sensitive resource",
      "New location detected"
    ],
    mitigating_factors: [
      "User has legitimate access rights"
    ],
    context_summary: {
      asset_sensitivity: "high",
      recent_incidents: "none",
      triggered_rules_count: 2
    },
    confidence: "medium",
    computation_method: "llm_react_contextual",
    llm_driven: true,
    execution_logs: []
  },
  HIGH: {
    event_id: "HIGH_RISK_TEST",
    timestamp: new Date().toISOString(),
    user_id: "ATK9999",
    entity_id: "",
    base_score: 0.92,
    risk_adjustment: -0.07,
    adjusted_risk_score: 0.85,
    risk_level: "HIGH",
    decision: "BLOCK",
    recommended_action: "block immediately",
    risk_factors: [
      "Multiple failed login attempts",
      "Access from suspicious IP address",
      "Unusual time of access (3 AM)",
      "Attempting to access sensitive data"
    ],
    mitigating_factors: [],
    context_summary: {
      asset_sensitivity: "critical",
      recent_incidents: "multiple",
      triggered_rules_count: 4
    },
    confidence: "high",
    computation_method: "llm_react_contextual",
    llm_driven: true,
    execution_logs: []
  }
}

export default function ResponseAgentTest() {
  const [riskOutput, setRiskOutput] = useState<any | null>(null)
  const [decision, setDecision] = useState<ResponseDecision | null>(null)
  const [loading, setLoading] = useState(false)
  const [deciding, setDeciding] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [rlStats, setRlStats] = useState<any>(null)

  const loadRiskOutput = async (riskLevel: 'LOW' | 'MEDIUM' | 'HIGH') => {
    setLoading(true)
    setError(null)
    setDecision(null)
    setRiskOutput(SAMPLE_EVENTS[riskLevel])
    setLoading(false)
  }

  const makeDecision = async () => {
    if (!riskOutput) return
    
    setDeciding(true)
    setError(null)
    
    try {
      const response = await fetch('http://localhost:8000/api/v1/response/process/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(riskOutput)
      })
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`)
      }
      
      const data = await response.json()
      setDecision(data)
    } catch (err: any) {
      setError(err.message)
    } finally {
      setDeciding(false)
    }
  }

  const fetchRLStats = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/v1/response/rl/stats/')
      const data = await response.json()
      setRlStats(data)
    } catch (err: any) {
      console.error('Failed to fetch RL stats:', err)
    }
  }

  const getRiskBadge = (level: string) => {
    const colors = {
      LOW: 'bg-green-500',
      MEDIUM: 'bg-yellow-500',
      HIGH: 'bg-red-500'
    }
    return <Badge className={colors[level as keyof typeof colors]}>{level}</Badge>
  }

  const getActionBadge = (action: string) => {
    const colors = {
      ALLOW: 'bg-green-500',
      MONITOR: 'bg-blue-500',
      ESCALATE: 'bg-yellow-500',
      BLOCK: 'bg-red-500',
      MFA_CHALLENGE: 'bg-orange-500'
    }
    return <Badge className={colors[action as keyof typeof colors] || 'bg-gray-500'}>{action}</Badge>
  }

  const getStatusBadge = (status: string) => {
    const config = {
      LOGGED: { color: 'bg-gray-500', icon: Activity },
      PENDING_USER: { color: 'bg-yellow-500', icon: Phone },
      AUTO_EXECUTED: { color: 'bg-red-500', icon: Zap }
    }
    const { color, icon: Icon } = config[status as keyof typeof config] || config.LOGGED
    return (
      <Badge className={color}>
        <Icon className="w-3 h-3 mr-1" />
        {status}
      </Badge>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Shield className="w-6 h-6" />
            Response Agent - Hybrid Decision System
          </CardTitle>
          <CardDescription>
            Test the Response Agent with different risk levels. The agent combines LLM feature weighting, 
            LLM direct decision, and RL model to make final decisions.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex gap-4">
            <Button 
              onClick={() => loadRiskOutput('LOW')}
              disabled={loading || deciding}
              variant="outline"
              className="flex-1"
            >
              <CheckCircle className="w-4 h-4 mr-2" />
              Load LOW Risk
            </Button>
            <Button 
              onClick={() => loadRiskOutput('MEDIUM')}
              disabled={loading || deciding}
              variant="outline"
              className="flex-1"
            >
              <AlertTriangle className="w-4 h-4 mr-2" />
              Load MEDIUM Risk
            </Button>
            <Button 
              onClick={() => loadRiskOutput('HIGH')}
              disabled={loading || deciding}
              variant="outline"
              className="flex-1"
            >
              <Shield className="w-4 h-4 mr-2" />
              Load HIGH Risk
            </Button>
            <Button 
              onClick={fetchRLStats}
              variant="secondary"
            >
              <Brain className="w-4 h-4 mr-2" />
              RL Stats
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Error Display */}
      {error && (
        <Alert variant="destructive">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {/* Loading State */}
      {loading && (
        <Card>
          <CardContent className="py-8 text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto mb-4"></div>
            <p className="text-muted-foreground">Loading risk output...</p>
          </CardContent>
        </Card>
      )}

      {/* Risk Output Display */}
      {riskOutput && !decision && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center justify-between">
              <span>Risk Agent Output</span>
              {getRiskBadge(riskOutput.risk_level)}
            </CardTitle>
            <CardDescription>
              Event: {riskOutput.event_id} | User: {riskOutput.user_id}
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <p className="text-sm text-muted-foreground">Base Score</p>
                <p className="text-2xl font-bold">{riskOutput.base_score.toFixed(3)}</p>
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Adjusted Risk Score</p>
                <p className="text-2xl font-bold">{riskOutput.adjusted_risk_score.toFixed(3)}</p>
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Risk Adjustment</p>
                <p className="text-2xl font-bold">{riskOutput.risk_adjustment.toFixed(3)}</p>
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Confidence</p>
                <p className="text-2xl font-bold capitalize">{riskOutput.confidence}</p>
              </div>
            </div>

            <div>
              <h4 className="font-semibold mb-2 text-red-500">Risk Factors ({riskOutput.risk_factors.length})</h4>
              <ul className="list-disc list-inside space-y-1">
                {riskOutput.risk_factors.map((factor: string, i: number) => (
                  <li key={i} className="text-sm text-muted-foreground">{factor}</li>
                ))}
              </ul>
            </div>

            {riskOutput.mitigating_factors.length > 0 && (
              <div>
                <h4 className="font-semibold mb-2 text-green-500">Mitigating Factors ({riskOutput.mitigating_factors.length})</h4>
                <ul className="list-disc list-inside space-y-1">
                  {riskOutput.mitigating_factors.map((factor: string, i: number) => (
                    <li key={i} className="text-sm text-muted-foreground">{factor}</li>
                  ))}
                </ul>
              </div>
            )}

            <div>
              <h4 className="font-semibold mb-2">Context Summary</h4>
              <pre className="text-xs bg-muted p-3 rounded">
                {JSON.stringify(riskOutput.context_summary, null, 2)}
              </pre>
            </div>

            <Button 
              onClick={makeDecision}
              disabled={deciding}
              className="w-full"
              size="lg"
            >
              {deciding ? (
                <>
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                  Making Decision...
                </>
              ) : (
                <>
                  <Zap className="w-4 h-4 mr-2" />
                  Make Decision (Hybrid AI)
                </>
              )}
            </Button>
          </CardContent>
        </Card>
      )}

      {/* RL Stats */}
      {rlStats && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Brain className="w-5 h-5" />
              RL Model Statistics
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div>
                <p className="text-sm text-muted-foreground">Q-Table Size</p>
                <p className="text-2xl font-bold">{rlStats.q_table_size}</p>
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Training Samples</p>
                <p className="text-2xl font-bold">{rlStats.training_samples}</p>
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Learning Rate</p>
                <p className="text-2xl font-bold">{rlStats.learning_rate}</p>
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Epsilon</p>
                <p className="text-2xl font-bold">{rlStats.epsilon}</p>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Decision Results */}
      {decision && (
        <div className="space-y-4">
          {/* Summary Card */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center justify-between">
                <span>Final Decision</span>
                <div className="flex gap-2">
                  {getRiskBadge(decision.risk_level)}
                  {getActionBadge(decision.final_action)}
                  {getStatusBadge(decision.execution_status)}
                </div>
              </CardTitle>
              <CardDescription>
                Event: {decision.event_id} | User: {decision.user_id}
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <h4 className="font-semibold mb-2">Risk Explanation</h4>
                <p className="text-sm text-muted-foreground">{decision.risk_explanation}</p>
              </div>
              <div>
                <h4 className="font-semibold mb-2">Action Explanation</h4>
                <p className="text-sm text-muted-foreground">{decision.action_explanation}</p>
              </div>
              <div className="flex items-center gap-2">
                <TrendingUp className="w-4 h-4" />
                <span className="text-sm">Confidence: {(decision.confidence * 100).toFixed(1)}%</span>
              </div>
              {decision.user_approval_required && (
                <Alert>
                  <Phone className="w-4 h-4" />
                  <AlertDescription>
                    User approval required. Twilio call initiated.
                    {decision.twilio_call_sid && ` (Call SID: ${decision.twilio_call_sid})`}
                  </AlertDescription>
                </Alert>
              )}
            </CardContent>
          </Card>

          {/* Decision Breakdown */}
          <Card>
            <CardHeader>
              <CardTitle>Decision Breakdown</CardTitle>
              <CardDescription>Three parallel decision methods</CardDescription>
            </CardHeader>
            <CardContent>
              <Tabs defaultValue="weighted">
                <TabsList className="grid w-full grid-cols-4">
                  <TabsTrigger value="weighted">LLM Weighted</TabsTrigger>
                  <TabsTrigger value="direct">LLM Direct</TabsTrigger>
                  <TabsTrigger value="rl">RL Model</TabsTrigger>
                  <TabsTrigger value="orchestrator">Orchestrator</TabsTrigger>
                </TabsList>

                <TabsContent value="weighted" className="space-y-4">
                  <div className="flex items-center justify-between">
                    <span className="font-semibold">Action:</span>
                    {getActionBadge(decision.llm_weighted_decision.action)}
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="font-semibold">Confidence:</span>
                    <span>{(decision.llm_weighted_decision.confidence * 100).toFixed(1)}%</span>
                  </div>
                  <div>
                    <span className="font-semibold">Reasoning:</span>
                    <pre className="mt-2 text-xs bg-muted p-3 rounded whitespace-pre-wrap">
                      {decision.llm_weighted_decision.reasoning}
                    </pre>
                  </div>
                </TabsContent>

                <TabsContent value="direct" className="space-y-4">
                  <div className="flex items-center justify-between">
                    <span className="font-semibold">Action:</span>
                    {getActionBadge(decision.llm_direct_decision.action)}
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="font-semibold">Confidence:</span>
                    <span>{(decision.llm_direct_decision.confidence * 100).toFixed(1)}%</span>
                  </div>
                  <div>
                    <span className="font-semibold">Reasoning:</span>
                    <pre className="mt-2 text-xs bg-muted p-3 rounded whitespace-pre-wrap">
                      {decision.llm_direct_decision.reasoning}
                    </pre>
                  </div>
                </TabsContent>

                <TabsContent value="rl" className="space-y-4">
                  <div className="flex items-center justify-between">
                    <span className="font-semibold">Action:</span>
                    {getActionBadge(decision.rl_decision.action)}
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="font-semibold">Confidence:</span>
                    <span>{(decision.rl_decision.confidence * 100).toFixed(1)}%</span>
                  </div>
                  <div>
                    <span className="font-semibold">Reasoning:</span>
                    <pre className="mt-2 text-xs bg-muted p-3 rounded whitespace-pre-wrap">
                      {decision.rl_decision.reasoning}
                    </pre>
                  </div>
                </TabsContent>

                <TabsContent value="orchestrator" className="space-y-4">
                  <div>
                    <span className="font-semibold">Final Reasoning:</span>
                    <pre className="mt-2 text-xs bg-muted p-3 rounded whitespace-pre-wrap">
                      {decision.orchestrator_reasoning}
                    </pre>
                  </div>
                </TabsContent>
              </Tabs>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  )
}
