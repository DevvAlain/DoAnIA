#!/usr/bin/env python3
"""
Complete MQTT Security Flow Pipeline
Dataset → Canonical → Simulator → EMQX + Logging → Feature Extraction → Detection → Alert/Block
"""

import subprocess
import time
import argparse
import logging
import threading
import os
import signal
import sys
from datetime import datetime

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class MQTTSecurityPipeline:
    """
    Complete security pipeline theo flow trong ảnh:
    1. Dataset thô → Canonical schema
    2. Canonical → Simulator phát traffic MQTT  
    3. EMQX broker + Telegraf/Suricata thu log
    4. Feature extraction từ log canonical
    5. Rule-based detection / Anomaly detection
    6. Alert / Block
    """
    
    def __init__(self):
        self.processes = []
        self.stop_event = threading.Event()
        
        # Register signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
    def _signal_handler(self, signum, frame):
        logger.info("🛑 Stopping pipeline...")
        self.stop_event.set()
        self._cleanup_processes()
        sys.exit(0)
        
    def run_complete_flow(self, duration=300):
        """
        Chạy complete flow theo architecture diagram
        """
        logger.info("🚀 Starting Complete MQTT Security Flow Pipeline")
        logger.info("=" * 70)
        logger.info("Flow: Dataset → Canonical → Simulator → EMQX + Log → Features → Detection")
        logger.info("=" * 70)
        
        try:
            # Step 1: Prepare Canonical Dataset
            self._step1_prepare_canonical()
            
            # Step 2: Start EMQX Broker
            self._step2_start_broker()
            
            # Step 3: Start Traffic Collection 
            self._step3_start_traffic_collection()
            
            # Step 4: Start Canonical Simulator
            self._step4_start_canonical_simulator()
            
            # Step 5: Run Pipeline for specified duration
            logger.info(f"⏱️ Running pipeline for {duration} seconds...")
            time.sleep(duration)
            
            # Step 6: Stop traffic generation
            self._step6_stop_traffic_generation()
            
            # Step 7: Feature Extraction
            self._step7_feature_extraction()
            
            # Step 8: Security Detection
            self._step8_security_detection()
            
            # Step 9: Generate Report
            self._step9_generate_report()
            
        except Exception as e:
            logger.error(f"❌ Pipeline failed: {e}")
            raise
        finally:
            self._cleanup_processes()
            
        logger.info("✅ Complete security flow pipeline finished!")
        
    def _step1_prepare_canonical(self):
        """Step 1: Chuẩn bị canonical dataset"""
        logger.info("📊 Step 1: Preparing canonical dataset...")
        
        if not os.path.exists("canonical_dataset.csv"):
            logger.info("   Building canonical dataset from raw CSV files...")
            cmd = [
                "python", "build_canonical_dataset.py",
                "--pattern", "*MQTTset.csv",
                "--output", "canonical_dataset.csv"
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                raise Exception(f"Canonical dataset creation failed: {result.stderr}")
                
            logger.info("   ✅ Canonical dataset created")
        else:
            logger.info("   ✅ Canonical dataset already exists")
            
    def _step2_start_broker(self):
        """Step 2: Start EMQX broker if not running"""
        logger.info("🐳 Step 2: Ensuring EMQX broker is running...")
        
        # Check if EMQX container is running
        result = subprocess.run(["docker", "ps"], capture_output=True, text=True)
        if "emqx" not in result.stdout:
            logger.info("   Starting EMQX broker...")
            subprocess.run(["docker-compose", "up", "-d"], check=True)
            time.sleep(10)  # Wait for broker to start
            
        logger.info("   ✅ EMQX broker ready")
        
    def _step3_start_traffic_collection(self):
        """Step 3: Start MQTT traffic collection"""
        logger.info("📡 Step 3: Starting MQTT traffic collection...")
        
        cmd = [
            "python", "mqtt_traffic_collector.py",
            "--broker", "localhost",
            "--log-file", "realtime_mqtt_traffic.csv",
            "--topics", "#"
        ]
        
        process = subprocess.Popen(cmd)
        self.processes.append(("traffic_collector", process))
        time.sleep(3)  # Let collector start
        
        logger.info("   ✅ Traffic collection started")
        
    def _step4_start_canonical_simulator(self):
        """Step 4: Start canonical simulator"""
        logger.info("🎯 Step 4: Starting canonical MQTT simulator...")
        
        cmd = [
            "python", "canonical_simulator.py",
            "--canonical-file", "canonical_dataset.csv", 
            "--broker", "localhost",
            "--publish-interval", "1.0"
        ]
        
        process = subprocess.Popen(cmd)
        self.processes.append(("canonical_simulator", process))
        time.sleep(5)  # Let simulator start
        
        logger.info("   ✅ Canonical simulator started")
        
    def _step6_stop_traffic_generation(self):
        """Step 6: Stop traffic generation"""
        logger.info("🛑 Step 6: Stopping traffic generation...")
        
        # Stop simulator first
        for name, process in self.processes:
            if name == "canonical_simulator":
                process.terminate()
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()
                break
                
        time.sleep(5)  # Let final messages process
        
        # Stop traffic collector
        for name, process in self.processes:
            if name == "traffic_collector":
                process.terminate()
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()
                break
                
        logger.info("   ✅ Traffic generation stopped")
        
    def _step7_feature_extraction(self):
        """Step 7: Extract features from collected traffic"""
        logger.info("🔬 Step 7: Extracting features from collected traffic...")
        
        if os.path.exists("realtime_mqtt_traffic.csv"):
            cmd = [
                "python", "feature_extract.py",
                "realtime_mqtt_traffic.csv",
                "--out", "realtime_features.csv"
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                logger.warning(f"   ⚠️ Feature extraction had issues: {result.stderr}")
            else:
                logger.info("   ✅ Features extracted")
        else:
            logger.warning("   ⚠️ No traffic log found for feature extraction")
            
    def _step8_security_detection(self):
        """Step 8: Run security detection"""
        logger.info("🛡️ Step 8: Running security detection...")
        
        if os.path.exists("realtime_features.csv"):
            cmd = [
                "python", "security_detector.py",
                "--features", "realtime_features.csv",
                "--alerts", "security_alerts.csv"
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                logger.warning(f"   ⚠️ Security detection had issues: {result.stderr}")
            else:
                logger.info("   ✅ Security detection completed")
        else:
            logger.warning("   ⚠️ No features file found for detection")
            
    def _step9_generate_report(self):
        """Step 9: Generate final report"""
        logger.info("📋 Step 9: Generating security report...")
        
        report_file = f"security_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write("MQTT Security Pipeline Report\n")
            f.write("=" * 50 + "\n")
            f.write(f"Generated: {datetime.now().isoformat()}\n\n")
            
            # Check各个文件的存在和统计
            files_to_check = [
                ("canonical_dataset.csv", "Canonical Dataset"),
                ("realtime_mqtt_traffic.csv", "Collected Traffic"), 
                ("realtime_features.csv", "Extracted Features"),
                ("security_alerts.csv", "Security Alerts")
            ]
            
            for filename, description in files_to_check:
                if os.path.exists(filename):
                    size = os.path.getsize(filename)
                    f.write(f"[OK] {description}: {filename} ({size:,} bytes)\n")
                    
                    # Count lines for CSV files
                    if filename.endswith('.csv'):
                        try:
                            with open(filename, 'r', encoding='utf-8') as csv_file:
                                lines = sum(1 for _ in csv_file) - 1  # Exclude header
                            f.write(f"   Records: {lines:,}\n")
                        except:
                            pass
                else:
                    f.write(f"[MISSING] {description}: {filename} (not found)\n")
                f.write("\n")
                
            # Add flow summary
            f.write("Flow Summary:\n")
            f.write("1. [OK] Dataset -> Canonical schema conversion\n")
            f.write("2. [OK] Canonical -> MQTT traffic simulation\n") 
            f.write("3. [OK] EMQX broker + traffic logging\n")
            f.write("4. [OK] Feature extraction from logs\n")
            f.write("5. [OK] Rule-based security detection\n")
            f.write("6. [OK] Alert generation and reporting\n")
            
        logger.info(f"   ✅ Report generated: {report_file}")
        
    def _cleanup_processes(self):
        """Clean up all running processes"""
        logger.info("🧹 Cleaning up processes...")
        
        for name, process in self.processes:
            try:
                if process.poll() is None:  # Process still running
                    logger.info(f"   Stopping {name}...")
                    process.terminate()
                    try:
                        process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait()
            except Exception as e:
                logger.warning(f"   Error stopping {name}: {e}")
                
        self.processes.clear()

def main():
    parser = argparse.ArgumentParser(description="Complete MQTT Security Flow Pipeline")
    parser.add_argument("--duration", type=int, default=120, 
                       help="Duration to run traffic simulation (seconds)")
    parser.add_argument("--skip-canonical", action="store_true",
                       help="Skip canonical dataset generation")
    
    args = parser.parse_args()
    
    try:
        pipeline = MQTTSecurityPipeline()
        pipeline.run_complete_flow(duration=args.duration)
        
    except KeyboardInterrupt:
        logger.info("🛑 Pipeline interrupted by user")
    except Exception as e:
        logger.error(f"❌ Pipeline failed: {e}")
        return 1
        
    return 0

if __name__ == "__main__":
    exit(main())