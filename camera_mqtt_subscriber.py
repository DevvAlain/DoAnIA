#!/usr/bin/env python3
"""
Camera MQTT Subscriber - Nhận và hiển thị dữ liệu từ camera simulator
Monitor camera events: status, motion detection, security events
"""

import paho.mqtt.client as mqtt
import json
import logging
from datetime import datetime
import argparse

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class CameraMQTTSubscriber:
    def __init__(self, broker="localhost", port=1883):
        self.broker = broker
        self.port = port
        self.client = None
        self.message_count = 0
        
        # Statistics
        self.stats = {
            "status": 0,
            "motion": 0,
            "security": 0,
            "system": 0,
            "stream": 0,
            "total": 0
        }
        
    def on_connect(self, client, userdata, flags, rc, properties=None):
        if rc == 0:
            logger.info("✅ Connected to MQTT broker")
            
            # Subscribe to all camera topics
            topics = [
                ("surveillance/+/camera/+/status", 1),
                ("surveillance/+/camera/+/motion", 2),
                ("surveillance/+/camera/+/stream", 0),
                ("security/+/camera/+/event", 2),
                ("system/+/camera/+/event", 1)
            ]
            
            for topic, qos in topics:
                client.subscribe(topic, qos)
                logger.info(f"📡 Subscribed to: {topic} (QoS {qos})")
                
        else:
            logger.error(f"❌ Failed to connect, return code {rc}")
    
    def on_message(self, client, userdata, msg):
        try:
            self.message_count += 1
            topic = msg.topic
            payload = json.loads(msg.payload.decode('utf-8'))
            
            # Parse topic to get info
            topic_parts = topic.split('/')
            zone = topic_parts[1]
            camera_id = topic_parts[3]
            message_type = topic_parts[4]
            
            # Update statistics
            if "status" in topic:
                self.stats["status"] += 1
                self._handle_status_message(zone, camera_id, payload)
            elif "motion" in topic:
                self.stats["motion"] += 1
                self._handle_motion_message(zone, camera_id, payload)
            elif "stream" in topic:
                self.stats["stream"] += 1
                self._handle_stream_message(zone, camera_id, payload)
            elif "security" in topic:
                self.stats["security"] += 1
                self._handle_security_message(zone, camera_id, payload)
            elif "system" in topic:
                self.stats["system"] += 1
                self._handle_system_message(zone, camera_id, payload)
            
            self.stats["total"] += 1
            
            # Print summary every 50 messages
            if self.message_count % 50 == 0:
                self._print_statistics()
                
        except Exception as e:
            logger.error(f"❌ Error processing message: {e}")
    
    def _handle_status_message(self, zone, camera_id, payload):
        """Handle camera status messages"""
        status = payload.get("status", "unknown")
        temp = payload.get("temperature", 0)
        cpu = payload.get("cpu_usage", 0)
        recording = payload.get("recording", False)
        
        logger.info(f"📊 [STATUS] {camera_id}@{zone} - {status} | Temp: {temp}°C | CPU: {cpu}% | Recording: {recording}")
    
    def _handle_motion_message(self, zone, camera_id, payload):
        """Handle motion detection messages"""
        confidence = payload.get("confidence", 0)
        area = payload.get("motion_area_percent", 0)
        alert_level = payload.get("alert_level", "unknown")
        
        # Emoji based on alert level
        emoji = "🟢" if alert_level == "low" else "🟡" if alert_level == "medium" else "🔴"
        
        logger.info(f"🚶 [MOTION] {camera_id}@{zone} - {emoji} {alert_level.upper()} | Confidence: {confidence} | Area: {area}%")
    
    def _handle_security_message(self, zone, camera_id, payload):
        """Handle security event messages"""
        event_type = payload.get("event_type", "unknown")
        severity = payload.get("severity", "info")
        confidence = payload.get("confidence", 0)
        
        # Emoji based on severity
        emoji = "ℹ️" if severity == "info" else "⚠️" if severity == "warning" else "🚨"
        
        logger.info(f"🚨 [SECURITY] {camera_id}@{zone} - {emoji} {event_type} | Severity: {severity} | Confidence: {confidence}")
    
    def _handle_system_message(self, zone, camera_id, payload):
        """Handle system event messages"""
        event_type = payload.get("event_type", "unknown")
        requires_attention = payload.get("requires_attention", False)
        
        emoji = "🔧" if not requires_attention else "⚠️"
        
        logger.info(f"🔧 [SYSTEM] {camera_id}@{zone} - {emoji} {event_type}")
    
    def _handle_stream_message(self, zone, camera_id, payload):
        """Handle stream metadata messages (less verbose)"""
        fps = payload.get("current_fps", 0)
        bitrate = payload.get("bitrate_kbps", 0)
        quality = payload.get("quality_score", 0)
        
        # Only log every 10th stream message to reduce noise
        if self.stats["stream"] % 10 == 0:
            logger.info(f"📹 [STREAM] {camera_id}@{zone} - FPS: {fps} | Bitrate: {bitrate}kbps | Quality: {quality}")
    
    def _print_statistics(self):
        """Print message statistics"""
        logger.info("=" * 60)
        logger.info(f"📈 MESSAGE STATISTICS (Total: {self.stats['total']})")
        logger.info(f"   📊 Status:    {self.stats['status']:4d}")
        logger.info(f"   🚶 Motion:    {self.stats['motion']:4d}")  
        logger.info(f"   🚨 Security:  {self.stats['security']:4d}")
        logger.info(f"   🔧 System:    {self.stats['system']:4d}")
        logger.info(f"   📹 Stream:    {self.stats['stream']:4d}")
        logger.info("=" * 60)
    
    def start_listening(self):
        """Start listening for camera messages"""
        try:
            self.client = mqtt.Client(
                client_id="camera_subscriber",
                callback_api_version=mqtt.CallbackAPIVersion.VERSION2
            )
            
            self.client.on_connect = self.on_connect
            self.client.on_message = self.on_message
            
            logger.info(f"🔌 Connecting to MQTT broker {self.broker}:{self.port}...")
            self.client.connect(self.broker, self.port, 60)
            
            logger.info("👂 Listening for camera messages... (Press Ctrl+C to stop)")
            self.client.loop_forever()
            
        except KeyboardInterrupt:
            logger.info("⏹️ Stopping camera subscriber...")
            self._print_statistics()
        except Exception as e:
            logger.error(f"❌ Error: {e}")
        finally:
            if self.client:
                self.client.disconnect()
                logger.info("📤 Disconnected from MQTT broker")

def main():
    parser = argparse.ArgumentParser(description="Camera MQTT Subscriber")
    parser.add_argument("--broker", default="localhost", help="MQTT broker address")
    parser.add_argument("--port", type=int, default=1883, help="MQTT broker port")
    
    args = parser.parse_args()
    
    subscriber = CameraMQTTSubscriber(broker=args.broker, port=args.port)
    subscriber.start_listening()

if __name__ == "__main__":
    main()