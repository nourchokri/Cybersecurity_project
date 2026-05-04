"""Test script for Response Agent."""

import requests
import json
from pprint import pprint

# Base URL
BASE_URL = "http://127.0.0.1:8000/api/v1"

# Sample risk agent output (from your example)
SAMPLE_RISK_OUTPUT = {
    "event_id": "MJS0890_2026-04-23T05:32:31.535756",
    "timestamp": "2026-04-23T05:32:31.535756",
    "user_id": "MJS0890",
    "entity_id": "",
    "base_score": 0.4327057100801832,
    "risk_adjustment": -0.3,
    "adjusted_risk_score": 0.13270571008018323,
    "risk_level": "LOW",
    "decision": "ALLOW",
    "recommended_action": "log event for audit trail",
    "risk_factors": [
        "Unusual behavior vs baseline (the user has not accessed the system from this device before)",
        "High privilege + high sensitivity combination (the user is a Technician with access to sensitive information)"
    ],
    "mitigating_factors": [
        "Consistent with user's role and responsibilities (the user is a Technician and may need to access the system from different devices)"
    ],
    "context_summary": {
        "asset_sensitivity": "unavailable",
        "asset_data_type": "unavailable",
        "recent_incidents": "unavailable",
        "triggered_rules_count": 1
    },
    "confidence": "medium",
    "computation_method": "llm_react_contextual",
    "llm_driven": True,
    "execution_logs": [
        "\n=== Decision Agent: Contextual Risk Analysis ===\n",
        "Event ID: MJS0890_2026-04-23T05:32:31.535756",
        "Base Score (from Team 2): 0.4327057100801832",
        "Threat Classification: HIGH_PRIORITY"
    ]
}

# HIGH risk example
HIGH_RISK_OUTPUT = {
    **SAMPLE_RISK_OUTPUT,
    "event_id": "HIGH_RISK_TEST_001",
    "adjusted_risk_score": 0.85,
    "risk_level": "HIGH",
    "decision": "BLOCK",
    "risk_factors": [
        "Multiple failed login attempts",
        "Access from suspicious IP address",
        "Unusual time of access (3 AM)",
        "Attempting to access sensitive data"
    ],
    "mitigating_factors": []
}

# MEDIUM risk example
MEDIUM_RISK_OUTPUT = {
    **SAMPLE_RISK_OUTPUT,
    "event_id": "MEDIUM_RISK_TEST_001",
    "adjusted_risk_score": 0.55,
    "risk_level": "MEDIUM",
    "decision": "ESCALATE",
    "risk_factors": [
        "Unusual behavior pattern",
        "Access to sensitive resource"
    ],
    "mitigating_factors": [
        "User has legitimate access rights"
    ]
}


def test_health():
    """Test health endpoint."""
    print("\n" + "="*80)
    print("TEST 1: Health Check")
    print("="*80)
    
    response = requests.get(f"{BASE_URL}/response/health/")
    print(f"Status: {response.status_code}")
    pprint(response.json())


def test_low_risk():
    """Test LOW risk event (should just log)."""
    print("\n" + "="*80)
    print("TEST 2: LOW Risk Event")
    print("="*80)
    
    response = requests.post(
        f"{BASE_URL}/response/process/",
        json=SAMPLE_RISK_OUTPUT,
        headers={"Content-Type": "application/json"}
    )
    
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        result = response.json()
        print(f"\nFinal Action: {result['final_action']}")
        print(f"Execution Status: {result['execution_status']}")
        print(f"Confidence: {result['confidence']:.3f}")
        
        print("\n--- Decision Breakdown ---")
        print(f"LLM Weighted: {result['llm_weighted_decision']['action']} (conf: {result['llm_weighted_decision']['confidence']:.3f})")
        print(f"LLM Direct: {result['llm_direct_decision']['action']} (conf: {result['llm_direct_decision']['confidence']:.3f})")
        print(f"RL Model: {result['rl_decision']['action']} (conf: {result['rl_decision']['confidence']:.3f})")
        
        print("\n--- Risk Explanation ---")
        print(result['risk_explanation'])
        
        print("\n--- Action Explanation ---")
        print(result['action_explanation'])
        
        print("\n--- Orchestrator Reasoning ---")
        print(result['orchestrator_reasoning'])
    else:
        print("Error:", response.text)


def test_high_risk():
    """Test HIGH risk event (should auto-execute)."""
    print("\n" + "="*80)
    print("TEST 3: HIGH Risk Event (Auto-Execute)")
    print("="*80)
    
    response = requests.post(
        f"{BASE_URL}/response/process/",
        json=HIGH_RISK_OUTPUT,
        headers={"Content-Type": "application/json"}
    )
    
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        result = response.json()
        print(f"\nFinal Action: {result['final_action']}")
        print(f"Execution Status: {result['execution_status']}")
        print(f"Risk Level: {result['risk_level']}")
        
        print("\n--- Risk Explanation ---")
        print(result['risk_explanation'])
        
        print("\n--- Action Explanation ---")
        print(result['action_explanation'])
    else:
        print("Error:", response.text)


def test_medium_risk():
    """Test MEDIUM risk event (should request user approval)."""
    print("\n" + "="*80)
    print("TEST 4: MEDIUM Risk Event (User Approval Required)")
    print("="*80)
    
    response = requests.post(
        f"{BASE_URL}/response/process/",
        json=MEDIUM_RISK_OUTPUT,
        headers={"Content-Type": "application/json"}
    )
    
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        result = response.json()
        print(f"\nFinal Action: {result['final_action']}")
        print(f"Execution Status: {result['execution_status']}")
        print(f"User Approval Required: {result['user_approval_required']}")
        
        if result.get('twilio_call_sid'):
            print(f"Twilio Call SID: {result['twilio_call_sid']}")
        
        print("\n--- Risk Explanation ---")
        print(result['risk_explanation'])
    else:
        print("Error:", response.text)


def test_rl_stats():
    """Test RL model statistics."""
    print("\n" + "="*80)
    print("TEST 5: RL Model Statistics")
    print("="*80)
    
    response = requests.get(f"{BASE_URL}/response/rl/stats/")
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        pprint(response.json())
    else:
        print("Error:", response.text)


def test_rl_training():
    """Test RL model training."""
    print("\n" + "="*80)
    print("TEST 6: RL Model Training")
    print("="*80)
    
    training_data = {
        "event_id": "TRAINING_TEST_001",
        "risk_data": SAMPLE_RISK_OUTPUT,
        "action_taken": "ALLOW",
        "outcome": "SUCCESS"
    }
    
    response = requests.post(
        f"{BASE_URL}/response/train/",
        json=training_data,
        headers={"Content-Type": "application/json"}
    )
    
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        pprint(response.json())
    else:
        print("Error:", response.text)


if __name__ == "__main__":
    print("\n" + "="*80)
    print("RESPONSE AGENT TEST SUITE")
    print("="*80)
    print("\nMake sure the Django server is running:")
    print("  cd cybersec_backend")
    print("  python manage.py runserver")
    print("\nPress Enter to continue...")
    input()
    
    try:
        test_health()
        test_low_risk()
        test_high_risk()
        test_medium_risk()
        test_rl_stats()
        test_rl_training()
        
        print("\n" + "="*80)
        print("ALL TESTS COMPLETED")
        print("="*80)
        
    except requests.exceptions.ConnectionError:
        print("\n❌ ERROR: Could not connect to server.")
        print("Make sure Django server is running on http://127.0.0.1:8000")
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
