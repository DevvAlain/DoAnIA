#!/usr/bin/env python3
"""
Camera MQTT Demo Script
Demo camera simulator với MQTT broker sẵn có
"""

import subprocess
import time
import logging
import sys
import os
import signal
from threading import Thread

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class CameraDemo:
    def __init__(self):
        self.processes = []
        self.running = True
        
    def check_mqtt_broker(self):
        """Check if MQTT broker is running"""
        try:
            # Try to connect to MQTT broker
            import paho.mqtt.client as mqtt
            
            def on_connect(client, userdata, flags, rc, properties=None):
                if rc == 0:
                    logger.info("✅ MQTT broker is running")
                    client.disconnect()
                else:
                    logger.error(f"❌ Cannot connect to MQTT broker, return code {rc}")
                    
            client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2)
            client.on_connect = on_connect
            client.connect("localhost", 1883, 10)
            client.loop_start()
            time.sleep(2)
            client.loop_stop()
            return True
            
        except Exception as e:
            logger.error(f"❌ MQTT broker not available: {e}")
            return False
    
    def start_docker_broker(self):
        """Start MQTT broker using docker-compose"""
        logger.info("🐳 Starting MQTT broker with docker-compose...")
        try:
            # Check if docker-compose.yml exists
            if os.path.exists("docker-compose.yml"):
                cmd = ["docker-compose", "up", "-d", "emqx"]
                process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                stdout, stderr = process.communicate()
                
                if process.returncode == 0:
                    logger.info("✅ MQTT broker started successfully")
                    time.sleep(10)  # Wait for broker to be ready
                    return True
                else:
                    logger.error(f"❌ Failed to start MQTT broker: {stderr.decode()}")
                    return False
            else:
                logger.error("❌ docker-compose.yml not found")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error starting MQTT broker: {e}")
            return False
    
    def run_camera_simulator(self, cameras=3, duration=60):
        """Run camera simulator"""
        logger.info(f"🎬 Starting camera simulator with {cameras} cameras for {duration} seconds...")
        
        try:
            cmd = [
                sys.executable, "camera_mqtt_simulator.py",
                "--cameras", str(cameras),
                "--duration", str(duration),
                "--broker", "localhost",
                "--port", "1883"
            ]
            
            process = subprocess.Popen(cmd)
            self.processes.append(process)
            
            return process
            
        except Exception as e:
            logger.error(f"❌ Error starting camera simulator: {e}")
            return None
    
    def run_subscriber(self):
        """Run camera MQTT subscriber"""
        logger.info("👂 Starting camera MQTT subscriber...")
        
        try:
            cmd = [
                sys.executable, "camera_mqtt_subscriber.py",
                "--broker", "localhost",
                "--port", "1883"
            ]
            
            process = subprocess.Popen(cmd)
            self.processes.append(process)
            
            return process
            
        except Exception as e:
            logger.error(f"❌ Error starting subscriber: {e}")
            return None
    
    def run_test_simulator(self):
        """Run simple test camera simulator"""
        logger.info("🧪 Running test camera simulator...")
        
        try:
            cmd = [sys.executable, "test_camera_simulator.py"]
            process = subprocess.Popen(cmd)
            process.wait()  # Wait for test to complete
            
            if process.returncode == 0:
                logger.info("✅ Test camera simulator completed successfully")
            else:
                logger.error("❌ Test camera simulator failed")
                
        except Exception as e:
            logger.error(f"❌ Error running test simulator: {e}")
    
    def cleanup(self):
        """Cleanup processes"""
        logger.info("🧹 Cleaning up processes...")
        
        for process in self.processes:
            try:
                if process.poll() is None:  # Still running
                    process.terminate()
                    process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
            except Exception as e:
                logger.error(f"Error terminating process: {e}")
        
        self.processes.clear()
    
    def signal_handler(self, signum, frame):
        """Handle Ctrl+C"""
        logger.info("🛑 Received interrupt signal...")
        self.running = False
        self.cleanup()
        sys.exit(0)
    
    def run_full_demo(self, cameras=3, duration=120):
        """Run full camera demo"""
        # Setup signal handler
        signal.signal(signal.SIGINT, self.signal_handler)
        
        logger.info("🎬 Starting Camera MQTT Demo")
        logger.info("=" * 50)
        
        # 1. Check if MQTT broker is running
        if not self.check_mqtt_broker():
            logger.info("🔄 MQTT broker not running, attempting to start...")
            if not self.start_docker_broker():
                logger.error("❌ Cannot start MQTT broker. Please start manually:")
                logger.error("   docker-compose up -d emqx")
                return False
        
        # 2. Run test simulator first
        logger.info("\n📋 Step 1: Running test camera simulator...")
        self.run_test_simulator()
        
        input("\n📋 Step 2: Press Enter to start full camera simulation...")
        
        # 3. Start subscriber in background
        subscriber_process = self.run_subscriber()
        if not subscriber_process:
            return False
        
        time.sleep(2)  # Let subscriber start
        
        # 4. Start camera simulator
        simulator_process = self.run_camera_simulator(cameras, duration)
        if not simulator_process:
            return False
        
        logger.info(f"🎯 Demo running for {duration} seconds...")
        logger.info("📊 Monitor the messages above")
        logger.info("🛑 Press Ctrl+C to stop early")
        
        try:
            # Wait for simulator to complete
            simulator_process.wait()
            logger.info("✅ Camera simulator completed")
            
            # Let subscriber run a bit more to catch final messages
            time.sleep(5)
            
        except KeyboardInterrupt:
            logger.info("🛑 Demo stopped by user")
        finally:
            self.cleanup()
        
        logger.info("🏁 Camera MQTT Demo completed!")
        return True
    
    def run_quick_test(self):
        """Run quick test without full demo"""
        logger.info("🧪 Running quick camera test...")
        
        if not self.check_mqtt_broker():
            logger.error("❌ MQTT broker not available for quick test")
            logger.error("💡 Try: docker-compose up -d emqx")
            return False
        
        self.run_test_simulator()
        return True

def main():
    demo = CameraDemo()
    
    print("🎬 Camera MQTT Simulator Demo")
    print("=" * 40)
    print("1. Quick Test (test_camera_simulator.py)")
    print("2. Full Demo (simulator + subscriber)")
    print("3. Exit")
    
    while True:
        try:
            choice = input("\nSelect option (1-3): ").strip()
            
            if choice == "1":
                demo.run_quick_test()
                break
            elif choice == "2":
                cameras = input("Number of cameras (default 3): ").strip()
                cameras = int(cameras) if cameras.isdigit() else 3
                
                duration = input("Duration in seconds (default 120): ").strip()
                duration = int(duration) if duration.isdigit() else 120
                
                demo.run_full_demo(cameras, duration)
                break
            elif choice == "3":
                print("👋 Goodbye!")
                break
            else:
                print("❌ Invalid choice. Please select 1, 2, or 3.")
                
        except KeyboardInterrupt:
            print("\n🛑 Demo cancelled by user")
            break
        except Exception as e:
            print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()