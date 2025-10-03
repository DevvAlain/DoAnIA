#!/usr/bin/env python3
"""
Test Camera MQTT Simulator - Simple version for testing
Kiểm tra camera simulator với các tính năng cơ bản
"""

import paho.mqtt.client as mqtt
import json
import time
import random
import logging
from datetime import datetime, timezone

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def on_connect(client, userdata, flags, rc, properties=None):
    if rc == 0:
        logger.info("✅ Connected to MQTT broker")
    else:
        logger.error(f"❌ Failed to connect, return code {rc}")

def simulate_single_camera():
    """Simulate một camera đơn giản để test"""
    
    # Camera config
    camera_config = {
        "camera_id": "cam_001",
        "zone": "entrance",
        "model": "HikVision DS-2CD2086G2",
        "ip_address": "192.168.1.101",
        "resolution": "1920x1080",
        "fps": 30
    }
    
    # MQTT Client setup
    client = mqtt.Client(
        client_id="test_camera_simulator",
        callback_api_version=mqtt.CallbackAPIVersion.VERSION2
    )
    client.on_connect = on_connect
    
    try:
        # Connect to broker
        logger.info("🔌 Connecting to MQTT broker...")
        client.connect("localhost", 1883, 60)
        client.loop_start()
        time.sleep(2)  # Wait for connection
        
        logger.info("🎬 Starting camera simulation test...")
        
        # Simulate 10 messages
        for i in range(10):
            
            # 1. Camera Status
            status_data = {
                "device_type": "Camera",
                "camera_id": camera_config["camera_id"],
                "zone": camera_config["zone"],
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "status": "online",
                "temperature": round(random.uniform(40.0, 65.0), 1),
                "cpu_usage": round(random.uniform(20.0, 70.0), 1),
                "memory_usage": round(random.uniform(30.0, 80.0), 1),
                "recording": True,
                "motion_detection_enabled": True
            }
            
            topic = f"surveillance/{camera_config['zone']}/camera/{camera_config['camera_id']}/status"
            client.publish(topic, json.dumps(status_data), qos=1)
            logger.info(f"📊 [Status] Message {i+1}/10 published")
            
            time.sleep(1)
            
            # 2. Motion Detection (random)
            if random.random() < 0.3:  # 30% chance
                motion_data = {
                    "device_type": "Camera",
                    "event_type": "motion_detected",
                    "camera_id": camera_config["camera_id"],
                    "zone": camera_config["zone"],
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "confidence": round(random.uniform(0.5, 0.95), 2),
                    "motion_area_percent": round(random.uniform(5.0, 20.0), 1),
                    "alert_level": random.choice(["low", "medium", "high"])
                }
                
                topic = f"surveillance/{camera_config['zone']}/camera/{camera_config['camera_id']}/motion"
                client.publish(topic, json.dumps(motion_data), qos=2)
                logger.info(f"🚶 [Motion] Motion detected - confidence: {motion_data['confidence']}")
            
            time.sleep(2)
            
            # 3. Security Event (random)
            if random.random() < 0.2:  # 20% chance
                security_data = {
                    "device_type": "Camera",
                    "event_type": random.choice(["person_detected", "face_unknown", "vehicle_detected"]),
                    "camera_id": camera_config["camera_id"],
                    "zone": camera_config["zone"],
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "severity": random.choice(["info", "warning"]),
                    "confidence": round(random.uniform(0.6, 0.9), 2),
                    "alert_sent": True
                }
                
                topic = f"security/{camera_config['zone']}/camera/{camera_config['camera_id']}/event"
                client.publish(topic, json.dumps(security_data), qos=2)
                logger.info(f"🚨 [Security] {security_data['event_type']} - {security_data['severity']}")
        
        logger.info("✅ Camera simulation test completed!")
        
    except Exception as e:
        logger.error(f"❌ Error: {e}")
    finally:
        client.loop_stop()
        client.disconnect()
        logger.info("📤 Disconnected from MQTT broker")

if __name__ == "__main__":
    simulate_single_camera()