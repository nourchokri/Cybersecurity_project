export type AgentStatus = "idle" | "processing" | "completed" | "alert"

export interface Agent {
  id: string
  name: string
  slug: string
  role: string
  description: string
  inputType: string
  outputType: string
  status: AgentStatus
  lastUpdated: string
  metrics: {
    eventsProcessed: number
    alertsGenerated: number
    avgProcessingTime: string
  }
}

export interface LogEntry {
  id: string
  timestamp: string
  type: "info" | "warning" | "error" | "success"
  message: string
}

export interface AgentOutput {
  summary: string
  json: object
  explanation: string
}

export const agents: Agent[] = [
  {
    id: "1",
    name: "Data Agent",
    slug: "data-agent",
    role: "Data Collection & Normalization",
    description: "Collects and normalizes security data from multiple sources including SIEM, firewalls, endpoint detection systems, and network traffic analyzers.",
    inputType: "Raw Security Events",
    outputType: "Normalized Event Data",
    status: "idle",
    lastUpdated: "2 mins ago",
    metrics: {
      eventsProcessed: 15420,
      alertsGenerated: 0,
      avgProcessingTime: "12ms"
    }
  },
  {
    id: "2",
    name: "Attacker Agent",
    slug: "attacker-agent",
    role: "Attack Simulation & Testing",
    description: "Simulates realistic attack patterns using LLM-powered intelligence to test security detection capabilities and generate training data.",
    inputType: "System Context & Collected Data",
    outputType: "Simulated Attack Events",
    status: "idle",
    lastUpdated: "5 mins ago",
    metrics: {
      eventsProcessed: 0,
      alertsGenerated: 0,
      avgProcessingTime: "0ms"
    }
  },
  {
    id: "3",
    name: "Behavior Agent",
    slug: "behavior-agent",
    role: "Behavioral Analysis",
    description: "Analyzes user and entity behavior patterns using machine learning models to detect anomalies and deviations from baseline activity.",
    inputType: "Normalized Event Data",
    outputType: "Behavioral Patterns",
    status: "processing",
    lastUpdated: "Just now",
    metrics: {
      eventsProcessed: 8750,
      alertsGenerated: 23,
      avgProcessingTime: "45ms"
    }
  },
  {
    id: "4",
    name: "Risk & Behavior Agent",
    slug: "risk-behavior-agent",
    role: "Risk Assessment & Scoring",
    description: "Combines behavioral analysis with contextual risk factors to assign threat scores and prioritize security incidents.",
    inputType: "Behavioral Patterns",
    outputType: "Risk Scores & Classifications",
    status: "processing",
    lastUpdated: "Just now",
    metrics: {
      eventsProcessed: 6200,
      alertsGenerated: 15,
      avgProcessingTime: "78ms"
    }
  },
  {
    id: "5",
    name: "Response Agent",
    slug: "response-agent",
    role: "Automated Response & Orchestration",
    description: "Executes automated response actions based on risk scores and predefined playbooks. Coordinates with security tools for containment.",
    inputType: "Risk Scores",
    outputType: "Response Actions",
    status: "idle",
    lastUpdated: "5 mins ago",
    metrics: {
      eventsProcessed: 450,
      alertsGenerated: 8,
      avgProcessingTime: "250ms"
    }
  },
  {
    id: "6",
    name: "Reporting Agent",
    slug: "reporting-agent",
    role: "Reporting & Compliance",
    description: "Generates comprehensive security reports, compliance documentation, and executive summaries for stakeholders.",
    inputType: "All Agent Data",
    outputType: "Reports & Dashboards",
    status: "idle",
    lastUpdated: "10 mins ago",
    metrics: {
      eventsProcessed: 1200,
      alertsGenerated: 0,
      avgProcessingTime: "500ms"
    }
  }
]

export const agentOutputs: Record<string, AgentOutput> = {
  "data-agent": {
    summary: "Successfully ingested 15,420 security events from 12 data sources. All events normalized and enriched with geolocation and threat intelligence data.",
    json: {
      event_id: "EVT-2024-001542",
      user_id: "USR-4521",
      source_ip: "192.168.1.105",
      destination_ip: "10.0.0.50",
      event_type: "authentication_attempt",
      timestamp: "2024-01-15T14:32:15Z",
      normalized: true,
      enrichment: {
        geo_location: "New York, US",
        threat_score: 0.12,
        reputation: "clean"
      }
    },
    explanation: "The Data Agent has successfully collected raw security events from firewalls, SIEM systems, and endpoint detection tools. Each event has been normalized to a standard schema and enriched with contextual information including IP reputation, geolocation, and preliminary threat indicators."
  },
  "behavior-agent": {
    summary: "Detected 23 behavioral anomalies across 8,750 analyzed events. 3 high-priority deviations flagged for immediate review.",
    json: {
      analysis_id: "BHA-2024-0892",
      user_id: "USR-4521",
      baseline_deviation: 0.78,
      anomaly_type: "unusual_access_pattern",
      risk_indicators: [
        "off_hours_access",
        "new_device",
        "geographic_anomaly"
      ],
      confidence: 0.92,
      decision: "escalate"
    },
    explanation: "The Behavior Agent identified significant deviations from the user's established baseline. The combination of off-hours access from a new device in an unusual geographic location triggered multiple risk indicators, resulting in an escalation recommendation."
  },
  "risk-behavior-agent": {
    summary: "Calculated risk scores for 6,200 events. 15 events classified as high-risk requiring immediate attention.",
    json: {
      assessment_id: "RSK-2024-1105",
      event_id: "EVT-2024-001542",
      user_id: "USR-4521",
      risk_score: 87,
      risk_level: "high",
      contributing_factors: {
        behavioral_score: 0.78,
        asset_criticality: 0.9,
        threat_context: 0.65
      },
      decision: "block_and_alert",
      recommended_actions: [
        "suspend_session",
        "require_mfa",
        "notify_soc"
      ]
    },
    explanation: "The Risk & Behavior Agent combined behavioral analysis with contextual factors including asset criticality and current threat landscape. The resulting risk score of 87/100 exceeds the high-risk threshold, triggering automated response recommendations."
  },
  "response-agent": {
    summary: "Executed 8 automated response actions including 3 session terminations and 5 MFA challenges. All actions logged for audit.",
    json: {
      response_id: "RSP-2024-0341",
      event_id: "EVT-2024-001542",
      user_id: "USR-4521",
      actions_taken: [
        {
          action: "session_terminated",
          timestamp: "2024-01-15T14:32:45Z",
          status: "completed"
        },
        {
          action: "mfa_challenge_sent",
          timestamp: "2024-01-15T14:32:46Z",
          status: "pending"
        },
        {
          action: "soc_notification",
          timestamp: "2024-01-15T14:32:47Z",
          status: "completed"
        }
      ],
      decision: "contained",
      playbook_id: "PB-HIGH-RISK-001"
    },
    explanation: "The Response Agent executed the high-risk containment playbook, immediately terminating the suspicious session and requiring multi-factor authentication for re-access. SOC team has been notified for manual review."
  },
  "reporting-agent": {
    summary: "Generated 12 reports including daily security summary, compliance audit trail, and executive dashboard updates.",
    json: {
      report_id: "RPT-2024-0156",
      report_type: "security_summary",
      period: "2024-01-15",
      metrics: {
        total_events: 15420,
        anomalies_detected: 23,
        high_risk_events: 15,
        responses_executed: 8,
        false_positives: 2
      },
      compliance_status: {
        soc2: "compliant",
        gdpr: "compliant",
        hipaa: "review_required"
      },
      decision: "report_generated"
    },
    explanation: "The Reporting Agent compiled all security activities into comprehensive reports for various stakeholders. Executive summary highlights key metrics while detailed logs are available for compliance auditors."
  },
  "attacker-agent": {
    summary: "LLM-powered adversarial agent simulating realistic attack patterns for security testing. Injected 15 attacks across multiple MITRE ATT&CK techniques.",
    json: {
      agent_id: "ATK-2024-0892",
      mode: "intelligent_simulation",
      llm_model: "Llama-3.1-70B-Instruct",
      attacks_injected: 15,
      attack_categories: {
        data_exfiltration: 5,
        credential_theft: 4,
        sabotage: 3,
        reconnaissance: 3
      },
      mitre_techniques: [
        "T1052.001",
        "T1048.003",
        "T1567.002",
        "T1003",
        "T1056.001"
      ],
      events_generated: 45,
      all_simulated: true,
      decision: "testing_complete"
    },
    explanation: "The Attacker Agent uses LLM reasoning to generate context-aware attack simulations. All generated events are marked as simulated (is_simulated=true) to distinguish them from real threats. The agent analyzes system context to inject realistic attacks that test detection capabilities."
  }
}

export const generateLogs = (agentSlug: string): LogEntry[] => {
  const baseTimestamp = Date.now()
  const logTemplates: Record<string, LogEntry[]> = {
    "data-agent": [
      { id: "data-1", timestamp: new Date(baseTimestamp - 120000).toISOString(), type: "info", message: "INIT Data_Agent initialized" },
      { id: "data-2", timestamp: new Date(baseTimestamp - 115000).toISOString(), type: "info", message: "CONN source=splunk_enterprise status=connected" },
      { id: "data-3", timestamp: new Date(baseTimestamp - 110000).toISOString(), type: "info", message: "CONN source=paloalto_pa5200 status=connected" },
      { id: "data-4", timestamp: new Date(baseTimestamp - 100000).toISOString(), type: "success", message: "INGEST batch=001 events=1542 status=received" },
      { id: "data-5", timestamp: new Date(baseTimestamp - 90000).toISOString(), type: "info", message: "NORM schema_version=2.1 processing..." },
      { id: "data-6", timestamp: new Date(baseTimestamp - 80000).toISOString(), type: "success", message: "ENRICH geoip=complete threat_intel=complete" },
      { id: "data-7", timestamp: new Date(baseTimestamp - 70000).toISOString(), type: "warning", message: "SCALE event_volume=high workers=+2" },
      { id: "data-8", timestamp: new Date(baseTimestamp - 60000).toISOString(), type: "success", message: "INGEST batch=002 events=2105 status=received" },
      { id: "data-9", timestamp: new Date(baseTimestamp - 50000).toISOString(), type: "info", message: "PROC rate=128/s queue_depth=42" },
      { id: "data-10", timestamp: new Date(baseTimestamp - 40000).toISOString(), type: "success", message: "DONE total=15420 forwarded=true" }
    ],
    "behavior-agent": [
      { id: "behav-1", timestamp: new Date(baseTimestamp - 100000).toISOString(), type: "info", message: "INIT Behavior_Agent online" },
      { id: "behav-2", timestamp: new Date(baseTimestamp - 95000).toISOString(), type: "info", message: "LOAD model=behavioral_v2.4.1" },
      { id: "behav-3", timestamp: new Date(baseTimestamp - 90000).toISOString(), type: "success", message: "LOAD model_status=ready inference=enabled" },
      { id: "behav-4", timestamp: new Date(baseTimestamp - 80000).toISOString(), type: "info", message: "ANALYZE user=USR-4521 baseline=loaded" },
      { id: "behav-5", timestamp: new Date(baseTimestamp - 70000).toISOString(), type: "warning", message: "ANOMALY type=off_hours_access deviation=0.72" },
      { id: "behav-6", timestamp: new Date(baseTimestamp - 65000).toISOString(), type: "warning", message: "ANOMALY type=new_device risk_factor=0.65" },
      { id: "behav-7", timestamp: new Date(baseTimestamp - 60000).toISOString(), type: "error", message: "ALERT user=USR-4521 confidence=0.92 level=HIGH" },
      { id: "behav-8", timestamp: new Date(baseTimestamp - 50000).toISOString(), type: "info", message: "ESCALATE target=risk_agent priority=1" },
      { id: "behav-9", timestamp: new Date(baseTimestamp - 40000).toISOString(), type: "info", message: "STATS processed=8750 anomalies=23" },
      { id: "behav-10", timestamp: new Date(baseTimestamp - 30000).toISOString(), type: "success", message: "SYNC patterns_updated=true" }
    ],
    "risk-behavior-agent": [
      { id: "risk-1", timestamp: new Date(baseTimestamp - 80000).toISOString(), type: "info", message: "INIT Risk_Engine started" },
      { id: "risk-2", timestamp: new Date(baseTimestamp - 75000).toISOString(), type: "info", message: "FEED threat_intel=updated sources=12" },
      { id: "risk-3", timestamp: new Date(baseTimestamp - 70000).toISOString(), type: "info", message: "CALC event=EVT-001542 factors=loading" },
      { id: "risk-4", timestamp: new Date(baseTimestamp - 65000).toISOString(), type: "info", message: "FACTOR behavioral_score=0.78" },
      { id: "risk-5", timestamp: new Date(baseTimestamp - 60000).toISOString(), type: "info", message: "FACTOR asset_criticality=0.90" },
      { id: "risk-6", timestamp: new Date(baseTimestamp - 55000).toISOString(), type: "warning", message: "SCORE risk=87 threshold=70 status=EXCEEDED" },
      { id: "risk-7", timestamp: new Date(baseTimestamp - 50000).toISOString(), type: "error", message: "DECISION action=block_and_alert priority=CRITICAL" },
      { id: "risk-8", timestamp: new Date(baseTimestamp - 45000).toISOString(), type: "info", message: "DISPATCH target=response_agent" },
      { id: "risk-9", timestamp: new Date(baseTimestamp - 40000).toISOString(), type: "success", message: "ACK response_agent=acknowledged" },
      { id: "risk-10", timestamp: new Date(baseTimestamp - 35000).toISOString(), type: "info", message: "STATS high_risk_today=15" }
    ],
    "response-agent": [
      { id: "resp-1", timestamp: new Date(baseTimestamp - 60000).toISOString(), type: "info", message: "INIT Response_Orchestrator ready" },
      { id: "resp-2", timestamp: new Date(baseTimestamp - 55000).toISOString(), type: "info", message: "RECV alert=RSK-2024-1105 severity=HIGH" },
      { id: "resp-3", timestamp: new Date(baseTimestamp - 50000).toISOString(), type: "info", message: "PLAYBOOK id=PB-HIGH-RISK-001 loading..." },
      { id: "resp-4", timestamp: new Date(baseTimestamp - 45000).toISOString(), type: "warning", message: "EXEC action=session_terminate target=USR-4521" },
      { id: "resp-5", timestamp: new Date(baseTimestamp - 42000).toISOString(), type: "success", message: "DONE session=USR-4521 terminated=true" },
      { id: "resp-6", timestamp: new Date(baseTimestamp - 40000).toISOString(), type: "info", message: "EXEC action=mfa_challenge sent=true" },
      { id: "resp-7", timestamp: new Date(baseTimestamp - 38000).toISOString(), type: "success", message: "NOTIFY soc_team=alerted channel=pagerduty" },
      { id: "resp-8", timestamp: new Date(baseTimestamp - 35000).toISOString(), type: "info", message: "AUDIT actions_logged=true" },
      { id: "resp-9", timestamp: new Date(baseTimestamp - 30000).toISOString(), type: "success", message: "STATUS threat=contained" },
      { id: "resp-10", timestamp: new Date(baseTimestamp - 25000).toISOString(), type: "info", message: "AWAIT mfa_verification=pending" }
    ],
    "reporting-agent": [
      { id: "report-1", timestamp: new Date(baseTimestamp - 300000).toISOString(), type: "info", message: "INIT Reporting_Agent initialized" },
      { id: "report-2", timestamp: new Date(baseTimestamp - 290000).toISOString(), type: "info", message: "COLLECT metrics=aggregating sources=5" },
      { id: "report-3", timestamp: new Date(baseTimestamp - 280000).toISOString(), type: "info", message: "GENERATE report=daily_security_summary" },
      { id: "report-4", timestamp: new Date(baseTimestamp - 270000).toISOString(), type: "success", message: "DONE report=RPT-2024-0156 status=generated" },
      { id: "report-5", timestamp: new Date(baseTimestamp - 260000).toISOString(), type: "info", message: "AUDIT framework=SOC2 checking..." },
      { id: "report-6", timestamp: new Date(baseTimestamp - 250000).toISOString(), type: "success", message: "PASS SOC2=compliant" },
      { id: "report-7", timestamp: new Date(baseTimestamp - 240000).toISOString(), type: "success", message: "PASS GDPR=compliant" },
      { id: "report-8", timestamp: new Date(baseTimestamp - 230000).toISOString(), type: "warning", message: "REVIEW HIPAA=manual_review_required" },
      { id: "report-9", timestamp: new Date(baseTimestamp - 220000).toISOString(), type: "info", message: "DISTRIBUTE recipients=stakeholders" },
      { id: "report-10", timestamp: new Date(baseTimestamp - 210000).toISOString(), type: "success", message: "DONE reports_distributed=true" }
    ],
    "attacker-agent": [
      { id: "attack-1", timestamp: new Date(baseTimestamp - 120000).toISOString(), type: "info", message: "INIT Adversarial_Agent initialized" },
      { id: "attack-2", timestamp: new Date(baseTimestamp - 115000).toISOString(), type: "info", message: "LOAD llm=Llama-3.1-70B-Instruct" },
      { id: "attack-3", timestamp: new Date(baseTimestamp - 110000).toISOString(), type: "success", message: "LOAD patterns=30 mitre_techniques=15" },
      { id: "attack-4", timestamp: new Date(baseTimestamp - 100000).toISOString(), type: "info", message: "CONTEXT analyzing_system_state..." },
      { id: "attack-5", timestamp: new Date(baseTimestamp - 90000).toISOString(), type: "info", message: "LLM reasoning=attack_strategy_generation" },
      { id: "attack-6", timestamp: new Date(baseTimestamp - 80000).toISOString(), type: "warning", message: "INJECT attack=USB_Exfiltration technique=T1052.001" },
      { id: "attack-7", timestamp: new Date(baseTimestamp - 70000).toISOString(), type: "success", message: "DONE events=3 is_simulated=true stored=true" },
      { id: "attack-8", timestamp: new Date(baseTimestamp - 60000).toISOString(), type: "warning", message: "INJECT attack=Credential_Theft technique=T1003" },
      { id: "attack-9", timestamp: new Date(baseTimestamp - 50000).toISOString(), type: "success", message: "DONE events=2 is_simulated=true stored=true" },
      { id: "attack-10", timestamp: new Date(baseTimestamp - 40000).toISOString(), type: "info", message: "STATS total_attacks=15 events_generated=45" }
    ]
  }
  
  return logTemplates[agentSlug] || []
}

export type SystemStatus = "active" | "idle" | "alert"

export const getSystemStatus = (): SystemStatus => {
  const hasProcessing = agents.some(a => a.status === "processing")
  const hasAlert = agents.some(a => a.status === "alert")
  
  if (hasAlert) return "alert"
  if (hasProcessing) return "active"
  return "idle"
}
