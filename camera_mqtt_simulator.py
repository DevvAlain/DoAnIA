#!/usr/bin/env python3
"""
Camera MQTT Simulator - Synthetic Camera IoT Simulation
Tạo dữ liệu camera thực tế: motion detection, security events, camera status
"""

import paho.mqtt.client as mqtt
import json
import time
import random
import threading
import argparse
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any
import uuid

# Setup logging với UTF-8 encoding cho Windows
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class CameraMQTTSimulator:
    """
    Camera IoT Simulator với MQTT protocol
    Simulate: Camera status, Motion detection, Security events, System telemetry
    """
    
    def __init__(self, broker="localhost", port=1883, num_cameras=5):
        self.broker = broker
        self.port = port
        self.num_cameras = num_cameras
        self.client = None
        self.running = False
        
        # Initialize states first
        self.motion_detection_active = {}
        self.recording_status = {}
        
        # Camera configurations
        self.cameras = self._init_cameras()
        
        logger.info(f"🎥 Camera MQTT Simulator initialized")
        logger.info(f"📡 Broker: {self.broker}:{self.port}")
        logger.info(f"🎬 Cameras: {self.num_cameras}")
        
    def _init_cameras(self) -> List[Dict[str, Any]]:
        """Initialize camera configurations"""
        cameras = []
        zones = ["entrance", "lobby", "parking", "warehouse", "office", "cafeteria", "server_room"]
        
        for i in range(1, self.num_cameras + 1):
            camera = {
                "camera_id": f"cam_{i:03d}",
                "zone": random.choice(zones),
                "resolution": random.choice(["1920x1080", "1280x720", "3840x2160", "1600x1200"]),
                "fps": random.choice([15, 24, 30, 60]),
                "model": random.choice(["HikVision DS-2CD2086G2", "Dahua IPC-HFW5241E", "Axis M3046-V", "Bosch NBE-4502-AL"]),
                "ip_address": f"192.168.1.{100+i}",
                "mac_address": f"00:11:22:33:44:{i:02X}",
                "firmware_version": f"V5.{random.randint(6,9)}.{random.randint(10,40)}",
                "install_date": f"2024-{random.randint(1,12):02d}-{random.randint(1,28):02d}",
                "night_vision": random.choice([True, False]),
                "ptz_capable": random.choice([True, False]),
                "audio_enabled": random.choice([True, False])
            }
            cameras.append(camera)
            
            # Initialize states
            self.motion_detection_active[camera["camera_id"]] = True
            self.recording_status[camera["camera_id"]] = random.choice([True, False])
            
        return cameras
    
    def connect(self):
        """Connect to MQTT broker"""
        try:
            self.client = mqtt.Client(
                client_id=f"camera_simulator_{uuid.uuid4().hex[:8]}",
                callback_api_version=mqtt.CallbackAPIVersion.VERSION2
            )
            
            self.client.on_connect = self._on_connect
            self.client.on_disconnect = self._on_disconnect
            self.client.on_publish = self._on_publish
            
            logger.info(f"🔌 Connecting to MQTT broker {self.broker}:{self.port}...")
            self.client.connect(self.broker, self.port, 60)
            self.client.loop_start()
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to connect to MQTT broker: {e}")
            return False
    
    def _on_connect(self, client, userdata, flags, rc, properties=None):
        """Callback when connected to broker"""
        if rc == 0:
            logger.info(f"✅ Connected to MQTT broker successfully")
            self.running = True
        else:
            logger.error(f"❌ Failed to connect to MQTT broker, return code {rc}")
    
    def _on_disconnect(self, client, userdata, flags, rc, properties=None):
        """Callback when disconnected from broker"""
        logger.info(f"📤 Disconnected from MQTT broker, return code {rc}")
        self.running = False
    
    def _on_publish(self, client, userdata, mid, reason_code=None, properties=None):
        """Callback when message is published"""
        # Optional: log publish confirmations
        pass
    
    def start_simulation(self, duration=0):
        """Start camera simulation"""
        if not self.connect():
            return
        
        logger.info(f"🎬 Starting camera simulation...")
        logger.info(f"⏱️ Duration: {'infinite' if duration == 0 else f'{duration} seconds'}")
        
        # Start simulation threads
        threads = []
        
        # Camera status telemetry (every 30 seconds)
        status_thread = threading.Thread(target=self._simulate_status_telemetry, args=(30,))
        status_thread.daemon = True
        threads.append(status_thread)
        
        # Motion detection events (random intervals)
        motion_thread = threading.Thread(target=self._simulate_motion_detection, args=(5, 15))
        motion_thread.daemon = True
        threads.append(motion_thread)
        
        # Security events (random intervals)
        security_thread = threading.Thread(target=self._simulate_security_events, args=(20, 60))
        security_thread.daemon = True
        threads.append(security_thread)
        
        # System events (configuration changes, etc.)
        system_thread = threading.Thread(target=self._simulate_system_events, args=(45, 120))
        system_thread.daemon = True
        threads.append(system_thread)
        
        # Stream metadata (every 10 seconds)
        stream_thread = threading.Thread(target=self._simulate_stream_metadata, args=(10,))
        stream_thread.daemon = True
        threads.append(stream_thread)
        
        # Start all threads
        for thread in threads:
            thread.start()
        
        try:
            if duration > 0:
                time.sleep(duration)
                logger.info(f"⏰ Simulation duration reached: {duration} seconds")
            else:
                # Run until interrupted
                while self.running:
                    time.sleep(1)
                    
        except KeyboardInterrupt:
            logger.info(f"⏹️ Simulation stopped by user")
        finally:
            self.stop_simulation()
    
    def _simulate_status_telemetry(self, interval):
        """Simulate camera status telemetry"""
        while self.running:
            for camera in self.cameras:
                try:
                    # Generate realistic camera status
                    status_data = {
                        "device_type": "Camera",
                        "camera_id": camera["camera_id"],
                        "zone": camera["zone"],
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "status": random.choices(["online", "offline", "maintenance"], weights=[85, 10, 5])[0],
                        "resolution": camera["resolution"],
                        "fps": camera["fps"],
                        "model": camera["model"],
                        "ip_address": camera["ip_address"],
                        "firmware_version": camera["firmware_version"],
                        "uptime_hours": random.randint(1, 8760),  # Up to 1 year
                        "temperature": round(random.uniform(35.0, 75.0), 1),  # Celsius
                        "cpu_usage": round(random.uniform(15.0, 85.0), 1),  # Percentage
                        "memory_usage": round(random.uniform(25.0, 90.0), 1),  # Percentage
                        "storage_used_gb": round(random.uniform(10.0, 500.0), 1),
                        "storage_total_gb": random.choice([256, 512, 1024, 2048]),
                        "network_rx_mbps": round(random.uniform(1.0, 25.0), 2),
                        "network_tx_mbps": round(random.uniform(5.0, 50.0), 2),
                        "recording": self.recording_status[camera["camera_id"]],
                        "motion_detection_enabled": self.motion_detection_active[camera["camera_id"]],
                        "night_vision_active": camera["night_vision"] and random.choice([True, False]),
                        "ptz_position": {
                            "pan": random.randint(0, 360) if camera["ptz_capable"] else None,
                            "tilt": random.randint(-90, 90) if camera["ptz_capable"] else None,
                            "zoom": random.randint(1, 30) if camera["ptz_capable"] else None
                        } if camera["ptz_capable"] else None
                    }
                    
                    topic = f"surveillance/{camera['zone']}/camera/{camera['camera_id']}/status"
                    payload = json.dumps(status_data, ensure_ascii=False)
                    
                    self.client.publish(topic, payload, qos=1)
                    logger.info(f"📊 [Status] {camera['camera_id']} @ {camera['zone']} - {status_data['status']}")
                    
                except Exception as e:
                    logger.error(f"❌ Error publishing status for {camera['camera_id']}: {e}")
            
            time.sleep(interval)
    
    def _simulate_motion_detection(self, min_interval, max_interval):
        """Simulate motion detection events"""
        while self.running:
            # Random sleep between motion events
            sleep_time = random.uniform(min_interval, max_interval)
            time.sleep(sleep_time)
            
            # Select random camera that has motion detection enabled
            active_cameras = [cam for cam in self.cameras if self.motion_detection_active[cam["camera_id"]]]
            if not active_cameras:
                continue
                
            camera = random.choice(active_cameras)
            
            try:
                # Generate motion detection event
                motion_data = {
                    "device_type": "Camera",
                    "event_type": "motion_detected",
                    "camera_id": camera["camera_id"],
                    "zone": camera["zone"],
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "confidence": round(random.uniform(0.3, 0.99), 2),
                    "motion_area_percent": round(random.uniform(2.0, 25.0), 1),
                    "bounding_boxes": [
                        {
                            "x": random.randint(0, 1500),
                            "y": random.randint(0, 800),
                            "width": random.randint(50, 300),
                            "height": random.randint(80, 400),
                            "confidence": round(random.uniform(0.5, 0.95), 2)
                        }
                        for _ in range(random.randint(1, 3))
                    ],
                    "motion_vector": {
                        "direction": random.choice(["north", "south", "east", "west", "northeast", "northwest", "southeast", "southwest"]),
                        "speed": random.choice(["slow", "medium", "fast"])
                    },
                    "trigger_reason": random.choice(["significant_motion", "object_detection", "person_detection", "vehicle_detection"]),
                    "alert_level": random.choices(["low", "medium", "high"], weights=[60, 30, 10])[0]
                }
                
                topic = f"surveillance/{camera['zone']}/camera/{camera['camera_id']}/motion"
                payload = json.dumps(motion_data, ensure_ascii=False)
                
                self.client.publish(topic, payload, qos=2)  # QoS 2 for important events
                logger.info(f"🚶 [Motion] {camera['camera_id']} @ {camera['zone']} - Confidence: {motion_data['confidence']}")
                
            except Exception as e:
                logger.error(f"❌ Error publishing motion event for {camera['camera_id']}: {e}")
    
    def _simulate_security_events(self, min_interval, max_interval):
        """Simulate security-related events"""
        while self.running:
            sleep_time = random.uniform(min_interval, max_interval)
            time.sleep(sleep_time)
            
            camera = random.choice(self.cameras)
            
            try:
                event_types = [
                    "person_detected", "face_recognized", "face_unknown", "vehicle_detected",
                    "loitering_detected", "intrusion_alert", "tampering_detected", 
                    "audio_anomaly", "object_removed", "object_left_behind"
                ]
                
                event_type = random.choice(event_types)
                
                security_data = {
                    "device_type": "Camera",
                    "event_type": event_type,
                    "camera_id": camera["camera_id"],
                    "zone": camera["zone"],
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "severity": random.choices(["info", "warning", "critical"], weights=[50, 35, 15])[0],
                    "confidence": round(random.uniform(0.4, 0.98), 2),
                    "details": self._generate_event_details(event_type),
                    "snapshot_id": f"snap_{camera['camera_id']}_{int(time.time())}",
                    "video_clip_id": f"clip_{camera['camera_id']}_{int(time.time())}" if random.choice([True, False]) else None,
                    "alert_sent": random.choice([True, False]),
                    "requires_action": random.choice([True, False])
                }
                
                topic = f"security/{camera['zone']}/camera/{camera['camera_id']}/event"
                payload = json.dumps(security_data, ensure_ascii=False)
                
                self.client.publish(topic, payload, qos=2)
                logger.info(f"🚨 [Security] {camera['camera_id']} @ {camera['zone']} - {event_type} ({security_data['severity']})")
                
            except Exception as e:
                logger.error(f"❌ Error publishing security event for {camera['camera_id']}: {e}")
    
    def _generate_event_details(self, event_type):
        """Generate realistic event details based on event type"""
        details = {}
        
        if event_type == "person_detected":
            details = {
                "person_count": random.randint(1, 5),
                "estimated_age": f"{random.randint(20, 70)}±10",
                "estimated_gender": random.choice(["male", "female", "unknown"]),
                "clothing_color": random.choice(["dark", "light", "blue", "red", "black", "white"])
            }
        elif event_type == "face_recognized":
            details = {
                "person_id": f"person_{random.randint(1000, 9999)}",
                "name": random.choice(["John Doe", "Jane Smith", "Unknown Employee", "Visitor"]),
                "access_level": random.choice(["employee", "visitor", "contractor", "security"])
            }
        elif event_type == "vehicle_detected":
            details = {
                "vehicle_type": random.choice(["car", "truck", "motorcycle", "bicycle", "van"]),
                "license_plate": f"ABC{random.randint(100, 999)}" if random.choice([True, False]) else "unknown",
                "color": random.choice(["white", "black", "silver", "blue", "red"])
            }
        elif event_type == "tampering_detected":
            details = {
                "tampering_type": random.choice(["lens_blocked", "camera_moved", "cable_disconnected", "housing_opened"]),
                "duration_seconds": random.randint(5, 300)
            }
        else:
            details = {"description": f"Event details for {event_type}"}
            
        return details
    
    def _simulate_system_events(self, min_interval, max_interval):
        """Simulate system events like configuration changes"""
        while self.running:
            sleep_time = random.uniform(min_interval, max_interval)
            time.sleep(sleep_time)
            
            camera = random.choice(self.cameras)
            
            try:
                event_types = [
                    "config_changed", "firmware_update", "restart", "maintenance_mode",
                    "storage_full", "network_issue", "temperature_warning", "auth_failure"
                ]
                
                event_type = random.choice(event_types)
                
                system_data = {
                    "device_type": "Camera",
                    "event_type": event_type,
                    "camera_id": camera["camera_id"],
                    "zone": camera["zone"],
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "source": "system",
                    "details": self._generate_system_event_details(event_type, camera),
                    "user_id": f"admin_{random.randint(1, 5)}" if event_type in ["config_changed", "firmware_update"] else None,
                    "requires_attention": random.choice([True, False])
                }
                
                topic = f"system/{camera['zone']}/camera/{camera['camera_id']}/event"
                payload = json.dumps(system_data, ensure_ascii=False)
                
                self.client.publish(topic, payload, qos=1)
                logger.info(f"🔧 [System] {camera['camera_id']} @ {camera['zone']} - {event_type}")
                
                # Update camera state based on events
                if event_type == "maintenance_mode":
                    self.recording_status[camera["camera_id"]] = False
                elif event_type == "config_changed" and "motion_detection" in system_data["details"]:
                    self.motion_detection_active[camera["camera_id"]] = random.choice([True, False])
                    
            except Exception as e:
                logger.error(f"❌ Error publishing system event for {camera['camera_id']}: {e}")
    
    def _generate_system_event_details(self, event_type, camera):
        """Generate system event details"""
        if event_type == "config_changed":
            return {
                "parameter": random.choice(["resolution", "fps", "motion_detection", "recording_schedule", "quality"]),
                "old_value": "previous_value",
                "new_value": "new_value"
            }
        elif event_type == "firmware_update":
            return {
                "old_version": camera["firmware_version"],
                "new_version": f"V5.{random.randint(7,9)}.{random.randint(50,99)}",
                "update_size_mb": random.randint(10, 100)
            }
        elif event_type == "storage_full":
            return {
                "storage_used_percent": random.randint(95, 100),
                "oldest_files_deleted": random.choice([True, False])
            }
        elif event_type == "temperature_warning":
            return {
                "current_temp": round(random.uniform(75, 95), 1),
                "warning_threshold": 75.0
            }
        else:
            return {"description": f"System event: {event_type}"}
    
    def _simulate_stream_metadata(self, interval):
        """Simulate video stream metadata (not actual video)"""
        while self.running:
            for camera in self.cameras:
                if not self.recording_status[camera["camera_id"]]:
                    continue
                    
                try:
                    stream_data = {
                        "device_type": "Camera",
                        "camera_id": camera["camera_id"],
                        "zone": camera["zone"],
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "stream_status": "active",
                        "current_fps": camera["fps"] + random.randint(-2, 2),
                        "current_resolution": camera["resolution"],
                        "bitrate_kbps": random.randint(1000, 8000),
                        "frame_count": random.randint(1000000, 9999999),
                        "dropped_frames": random.randint(0, 50),
                        "encoding": random.choice(["H.264", "H.265", "MJPEG"]),
                        "audio_enabled": camera["audio_enabled"],
                        "storage_remaining_hours": round(random.uniform(24, 168), 1),  # 1-7 days
                        "quality_score": round(random.uniform(0.8, 1.0), 2)
                    }
                    
                    topic = f"surveillance/{camera['zone']}/camera/{camera['camera_id']}/stream"
                    payload = json.dumps(stream_data, ensure_ascii=False)
                    
                    self.client.publish(topic, payload, qos=0)  # QoS 0 for frequent metadata
                    
                except Exception as e:
                    logger.error(f"❌ Error publishing stream metadata for {camera['camera_id']}: {e}")
            
            time.sleep(interval)
    
    def stop_simulation(self):
        """Stop the simulation"""
        logger.info(f"⏹️ Stopping camera simulation...")
        self.running = False
        
        if self.client:
            self.client.loop_stop()
            self.client.disconnect()
        
        logger.info(f"✅ Camera simulation stopped")

def main():
    parser = argparse.ArgumentParser(description="Camera MQTT IoT Simulator")
    parser.add_argument("--broker", default="localhost", help="MQTT broker address")
    parser.add_argument("--port", type=int, default=1883, help="MQTT broker port")
    parser.add_argument("--cameras", type=int, default=5, help="Number of cameras to simulate")
    parser.add_argument("--duration", type=int, default=0, 
                       help="Simulation duration in seconds (0 = infinite)")
    
    args = parser.parse_args()
    
    try:
        simulator = CameraMQTTSimulator(
            broker=args.broker,
            port=args.port,
            num_cameras=args.cameras
        )
        
        simulator.start_simulation(duration=args.duration)
        
    except KeyboardInterrupt:
        logger.info(f"🛑 Camera simulation interrupted by user")
    except Exception as e:
        logger.error(f"❌ Camera simulation error: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())