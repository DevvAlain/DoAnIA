#!/usr/bin/env python3
"""
Test comprehensive attack flows and verify detection capabilities
"""
import subprocess
import time
import os
import pandas as pd
from datetime import datetime

def run_attack_test(attack_name, script_path, args, duration=10):
    """Run một attack script và return log path"""
    print(f"\n🎯 Testing {attack_name} Attack...")
    
    log_file = f"test_{attack_name.lower().replace(' ', '_')}_attack.csv"
    if os.path.exists(log_file):
        os.remove(log_file)
    
    # Add log file to arguments
    full_args = args + [f"--log-csv={log_file}", f"--duration={duration}"]
    
    try:
        # Run attack script
        cmd = ["python", script_path] + full_args
        print(f"Running: {' '.join(cmd)}")
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=duration+5)
        
        if result.returncode == 0:
            print(f"✅ {attack_name} completed successfully")
        else:
            print(f"⚠️ {attack_name} exit code: {result.returncode}")
            if result.stderr:
                print(f"Error: {result.stderr}")
        
        # Check if log file was created and has data
        if os.path.exists(log_file):
            df = pd.read_csv(log_file)
            print(f"📊 Generated {len(df)} log entries")
            print(f"📁 Log saved to: {log_file}")
            return log_file, df
        else:
            print(f"❌ No log file generated")
            return None, None
            
    except subprocess.TimeoutExpired:
        print(f"⏰ {attack_name} timed out after {duration+5}s")
        return None, None
    except Exception as e:
        print(f"❌ {attack_name} failed: {e}")
        return None, None

def analyze_attack_logs(attack_name, log_file, df):
    """Analyze attack logs to verify required fields"""
    print(f"\n🔍 Analyzing {attack_name} Logs...")
    
    if df is None or len(df) == 0:
        print("❌ No data to analyze")
        return False
    
    print(f"📊 Columns: {list(df.columns)}")
    print(f"📊 Sample data:")
    print(df.head(3).to_string(index=False))
    
    # Check required fields based on attack type
    required_fields = {}
    
    if "flood" in attack_name.lower():
        required_fields = {
            "timestamp": ["timestamp", "timestamp_utc"],
            "client_id": ["client_id"],
            "src_ip": ["src_ip"],
            "topic": ["topic"],
            "packet_type": ["packet_type"],
            "payload_length": ["payload_length"],
            "qos": ["qos"]
        }
    elif "wildcard" in attack_name.lower():
        required_fields = {
            "timestamp": ["timestamp", "timestamp_utc"],
            "client_id": ["client_id"], 
            "packet_type": ["packet_type"],
            "topic": ["topic"]
        }
    elif "brute" in attack_name.lower():
        required_fields = {
            "timestamp": ["timestamp", "timestamp_utc"],
            "client_id": ["client_id"],
            "src_ip": ["src_ip"],
            "packet_type": ["packet_type"],
            "connack_reason": ["connack_reason"]
        }
    
    # Verify required fields exist
    missing_fields = []
    for field_type, possible_names in required_fields.items():
        found = any(col in df.columns for col in possible_names)
        if not found:
            missing_fields.append(f"{field_type} (tried: {possible_names})")
    
    if missing_fields:
        print(f"❌ Missing required fields: {missing_fields}")
        return False
    else:
        print("✅ All required fields present")
        return True

def main():
    """Test all attack scripts"""
    print("🚀 Testing MQTT Attack Scripts Flow Compliance")
    print("=" * 60)
    
    attacks = [
        {
            "name": "Publish Flood",
            "script": "script_flood.py", 
            "args": ["--broker=localhost", "--clients=3", "--msg-rate=50", "--duration=8"]
        },
        {
            "name": "Wildcard Abuse",
            "script": "script_wildcard.py",
            "args": ["--broker=localhost", "--topics", "#", "$SYS/#", "factory/+/+/#", "--duration=8"]
        },
        {
            "name": "Brute Force",
            "script": "script_bruteforce.py", 
            "args": ["--broker=localhost", "--rate=5", "--topic-count=10", "--duration=8"]
        }
    ]
    
    results = {}
    
    for attack in attacks:
        log_file, df = run_attack_test(
            attack["name"], 
            attack["script"], 
            attack["args"]
        )
        
        if log_file and df is not None:
            compliance = analyze_attack_logs(attack["name"], log_file, df)
            results[attack["name"]] = {
                "log_file": log_file,
                "entries": len(df),
                "compliant": compliance
            }
        else:
            results[attack["name"]] = {
                "log_file": None,
                "entries": 0, 
                "compliant": False
            }
    
    # Summary report
    print("\n" + "=" * 60)
    print("📋 ATTACK FLOW COMPLIANCE SUMMARY")
    print("=" * 60)
    
    for attack_name, result in results.items():
        status = "✅ COMPLIANT" if result["compliant"] else "❌ NON-COMPLIANT"
        print(f"{attack_name:20} | {result['entries']:6d} entries | {status}")
        if result["log_file"]:
            print(f"{'':20} | Log: {result['log_file']}")
    
    # Overall compliance
    compliant_count = sum(1 for r in results.values() if r["compliant"])
    total_count = len(results)
    
    print(f"\n🎯 Overall Compliance: {compliant_count}/{total_count} attacks")
    
    if compliant_count == total_count:
        print("✅ All attack scripts are flow compliant!")
    else:
        print("⚠️ Some attack scripts need field enhancements")
        
    return results

if __name__ == "__main__":
    main()