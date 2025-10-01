#!/usr/bin/env python3
"""
MQTT Broker Log Collector cho Flow Detection Pipeline
EMQX → Log Collection → Feature Extraction → Detection
"""

import paho.mqtt.client as mqtt
import json
import csv
import time
import logging
from datetime import datetime, timezone
import argparse
import threading
import os

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class MQTTLogCollector:
    """
    Thu thập log từ MQTT broker để feed vào detection pipeline
    """
    
    def __init__(self, broker="localhost", port=1883, log_file="mqtt_traffic_log.csv"):
        self.broker = broker
        self.port = port
        self.log_file = log_file
        self.client = None
        self.csv_writer = None
        self.csv_file = None
        self.message_count = 0
        self.start_time = time.time()
        
        # Initialize CSV log file với canonical schema
        self._init_csv_log()
        
    def _init_csv_log(self):
        """Initialize CSV log file với schema tương thích canonical"""
        fieldnames = [
            'timestamp', 'src_ip', 'src_port', 'dst_ip', 'dst_port', 
            'client_id', 'topic', 'qos', 'retain', 'dupflag',
            'payload_length', 'payload_sample', 'packet_type', 
            'protocol', 'msgid', 'flow_stage', 'label'
        ]
        
        self.csv_file = open(self.log_file, 'w', newline='', encoding='utf-8')
        self.csv_writer = csv.DictWriter(self.csv_file, fieldnames=fieldnames)
        self.csv_writer.writeheader()
        
        logger.info(f"📝 Initialized traffic log: {self.log_file}")
        
    def start_collection(self, topics=["#"], duration=0):
        """
        Bắt đầu thu thập MQTT traffic theo flow detection pipeline
        """
        logger.info("🎯 Starting MQTT Traffic Collection for Detection Pipeline")
        logger.info(f"📡 Broker: {self.broker}:{self.port}")
        logger.info(f"📋 Topics: {topics}")
        logger.info(f"📝 Log file: {self.log_file}")
        
        # Create MQTT client
        self.client = mqtt.Client(
            client_id="traffic_collector_001",
            callback_api_version=mqtt.CallbackAPIVersion.VERSION2
        )
        
        # Set callbacks
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message
        self.client.on_disconnect = self._on_disconnect
        
        try:
            # Connect và subscribe
            self.client.connect(self.broker, self.port, 60)
            self.client.loop_start()
            
            # Subscribe to topics
            for topic in topics:
                self.client.subscribe(topic, qos=2)  # Highest QoS để capture tất cả
                
            logger.info("="*60)
            logger.info("🚀 Traffic collection started! Press Ctrl+C to stop...")
            
            # Run collection
            if duration > 0:
                time.sleep(duration)
                logger.info(f"⏰ Collection duration {duration}s completed")
            else:
                try:
                    while True:
                        time.sleep(1)
                        # Print stats mỗi 10 giây
                        if int(time.time() - self.start_time) % 10 == 0:
                            self._print_stats()
                except KeyboardInterrupt:
                    logger.info("🛑 Stopping collection...")
                    
        except Exception as e:
            logger.error(f"❌ Collection error: {e}")
        finally:
            self._cleanup()
            
    def _on_connect(self, client, userdata, flags, rc, properties=None):
        if rc == 0:
            logger.info("✅ Connected to MQTT broker for traffic collection")
        else:
            logger.error(f"❌ Connection failed with code: {rc}")
            
    def _on_message(self, client, userdata, msg):
        """
        Process mỗi message và log vào CSV theo canonical schema
        """
        self.message_count += 1
        
        try:
            # Extract message info
            timestamp = datetime.now(timezone.utc).isoformat()
            topic = msg.topic
            payload = msg.payload.decode('utf-8', errors='ignore')
            qos = msg.qos
            retain = msg.retain
            
            # Parse payload để extract thêm info
            client_id = "unknown"
            device_type = "unknown"
            
            try:
                if payload.startswith('{'):
                    payload_json = json.loads(payload)
                    client_id = payload_json.get('device_id', 
                                               payload_json.get('client_id', 'unknown'))
                    device_type = payload_json.get('device_type', 'unknown')
            except:
                pass
                
            # Extract info từ topic
            topic_parts = topic.split('/')
            if len(topic_parts) >= 3:
                potential_device = topic_parts[-3] if 'device' in topic_parts[-2] else topic_parts[-2]
                if device_type == 'unknown':
                    device_type = potential_device
                    
            # Create log record theo canonical schema
            log_record = {
                'timestamp': timestamp,
                'src_ip': '192.168.1.unknown',  # Would need broker logs for real IP
                'src_port': '50000',
                'dst_ip': self.broker,
                'dst_port': str(self.port),
                'client_id': client_id,
                'topic': topic,
                'qos': qos,
                'retain': 1 if retain else 0,
                'dupflag': 0,  # MQTT library doesn't expose this easily
                'payload_length': len(payload),
                'payload_sample': payload[:200] if len(payload) > 200 else payload,
                'packet_type': 'PUBLISH',
                'protocol': 'MQTT',
                'msgid': None,  # Would need to intercept at protocol level
                'flow_stage': 'broker_to_detection',
                'label': 'Unknown'  # To be determined by detection
            }
            
            # Write to CSV
            self.csv_writer.writerow(log_record)
            self.csv_file.flush()  # Ensure immediate write
            
            # Log sample messages
            if self.message_count % 10 == 0 or self.message_count <= 5:
                logger.info(f"📦 [{self.message_count}] {topic}: {payload[:100]}...")
                
        except Exception as e:
            logger.error(f"❌ Message processing error: {e}")
            
    def _on_disconnect(self, client, userdata, flags, rc, properties=None):
        logger.info("👋 Disconnected from MQTT broker")
        
    def _print_stats(self):
        """Print collection statistics"""
        duration = time.time() - self.start_time
        rate = self.message_count / duration if duration > 0 else 0
        logger.info(f"📊 Stats: {self.message_count} messages, {rate:.2f} msg/s, {duration:.0f}s runtime")
        
    def _cleanup(self):
        """Clean up resources"""
        logger.info("🧹 Cleaning up traffic collector...")
        
        if self.client and self.client.is_connected():
            self.client.loop_stop()
            self.client.disconnect()
            
        if self.csv_file:
            self.csv_file.close()
            
        logger.info(f"✅ Collection completed: {self.message_count} messages logged to {self.log_file}")

def main():
    parser = argparse.ArgumentParser(description="MQTT Traffic Collector for Detection Pipeline")
    parser.add_argument("--broker", default="localhost", help="MQTT broker address")
    parser.add_argument("--port", type=int, default=1883, help="MQTT broker port")
    parser.add_argument("--log-file", default="mqtt_traffic_log.csv", help="Output CSV log file")
    parser.add_argument("--topics", nargs="+", default=["#"], help="Topics to monitor")
    parser.add_argument("--duration", type=int, default=0, help="Collection duration (0=infinite)")
    
    args = parser.parse_args()
    
    try:
        collector = MQTTLogCollector(
            broker=args.broker,
            port=args.port,
            log_file=args.log_file
        )
        
        collector.start_collection(
            topics=args.topics,
            duration=args.duration
        )
        
    except Exception as e:
        logger.error(f"❌ Traffic collection failed: {e}")
        return 1
        
    return 0

if __name__ == "__main__":
    exit(main())