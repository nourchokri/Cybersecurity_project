"""
Test script to verify that attacker agent simulations produce HIGH risk levels.

This script:
1. Simulates an attack using the attacker agent
2. Waits for the attack to be processed through the pipeline
3. Checks the behavior agent's result
4. Verifies that the risk level is HIGH
"""

import requests
import time
import json

BASE_URL = "http://127.0.0.1:8000"

def test_attacker_high_risk():
    print("=" * 80)
    print("TESTING ATTACKER AGENT → HIGH RISK PIPELINE")
    print("=" * 80)
    
    # Step 1: Trigger attack simulation
    print("\n[1] Triggering attack simulation...")
    simulate_url = f"{BASE_URL}/api/v1/attacker/simulate/"
    
    try:
        response = requests.post(simulate_url, timeout=10)
        response.raise_for_status()
        result = response.json()
        
        if result.get('ok'):
            print(f"✅ Attack simulation started: {result.get('message')}")
        else:
            print(f"❌ Failed to start simulation: {result.get('error')}")
            return False
    except Exception as e:
        print(f"❌ Error starting simulation: {e}")
        return False
    
    # Step 2: Wait for simulation to complete
    print("\n[2] Waiting for simulation to complete (30 seconds)...")
    time.sleep(30)
    
    # Step 3: Check behavior agent result
    print("\n[3] Checking behavior agent result...")
    behavior_url = f"{BASE_URL}/api/v1/attacker/behavior-result/"
    
    try:
        response = requests.get(behavior_url, timeout=10)
        response.raise_for_status()
        result = response.json()
        
        if not result.get('ok'):
            print(f"❌ No behavior result available: {result.get('error')}")
            return False
        
        behavior_result = result.get('behavior_result', {})
        print(f"\n✅ Behavior result received:")
        print(f"   Sessions sent: {behavior_result.get('sessions_sent', 0)}")
        print(f"   Flagged count: {behavior_result.get('flagged_count', 0)}")
        print(f"   Skipped count: {behavior_result.get('skipped_count', 0)}")
        
        # Check individual results
        results = behavior_result.get('results', [])
        if not results:
            print("❌ No individual results found")
            return False
        
        print(f"\n[4] Analyzing {len(results)} results...")
        high_risk_count = 0
        
        for i, res in enumerate(results, 1):
            score = res.get('combined_score', 0)
            flagged = res.get('flagged', False)
            simulated = res.get('simulated', False)
            
            # Determine risk level based on score
            if score > 0.7:
                risk_level = "HIGH"
                high_risk_count += 1
            elif score > 0.4:
                risk_level = "MEDIUM"
            else:
                risk_level = "LOW"
            
            print(f"\n   Result {i}:")
            print(f"      Score: {score:.4f}")
            print(f"      Risk Level: {risk_level}")
            print(f"      Flagged: {flagged}")
            print(f"      Simulated: {simulated}")
            
            if simulated and risk_level == "HIGH":
                print(f"      ✅ Simulated attack correctly flagged as HIGH risk")
            elif simulated and risk_level != "HIGH":
                print(f"      ⚠️  Simulated attack NOT flagged as HIGH risk (got {risk_level})")
        
        # Summary
        print(f"\n" + "=" * 80)
        print(f"SUMMARY:")
        print(f"   Total results: {len(results)}")
        print(f"   HIGH risk count: {high_risk_count}")
        print(f"   Success rate: {high_risk_count}/{len(results)} ({100*high_risk_count/len(results):.1f}%)")
        
        if high_risk_count > 0:
            print(f"\n✅ SUCCESS: Attacker agent simulations are producing HIGH risk levels!")
            return True
        else:
            print(f"\n❌ FAILURE: No HIGH risk levels detected")
            return False
            
    except Exception as e:
        print(f"❌ Error checking behavior result: {e}")
        return False

if __name__ == "__main__":
    success = test_attacker_high_risk()
    exit(0 if success else 1)
