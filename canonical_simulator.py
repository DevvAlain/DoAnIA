#!/usr/bin/env python3
"""
MQTT IoT Simulator theo Flow chuẩn:
Dataset thô → Canonical schema → Simulator → EMQX + Logging → Feature extraction → Detection
"""

import argparse, threading, time, os, json, csv
import paho.mqtt.client as mqtt
import pandas as pd
from datetime import datetime, timezone
import random
import logging

# Setup logging for flow tracking  
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('simulator_flow.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Windows-compatible logging messages
def log_error(device_type, error):
    logger.error(f"[ERROR] {device_type} simulation error: {error}")

def log_success(device_type):
    logger.info(f"[OK] {device_type} canonical simulator connected")

class CanonicalMQTTSimulator:
    """
    Simulator theo flow chuẩn: Canonical Dataset → MQTT Traffic → Broker Logging
    """
    
    def __init__(self, canonical_file="canonical_dataset.csv", broker="localhost", port=1883):
        self.canonical_file = canonical_file
        self.broker = broker
        self.port = port
        self.clients = {}
        self.canonical_data = None
        self.device_data = {}
        self.stop_event = threading.Event()
        
        # Load canonical dataset
        self._load_canonical_data()
        self._prepare_device_datasets()
        
    def _load_canonical_data(self):
        """Load và phân tích canonical dataset"""
        logger.info(f"[DATA] Loading canonical dataset from {self.canonical_file}")
        
        if not os.path.exists(self.canonical_file):
            logger.error(f"[ERROR] Canonical dataset not found: {self.canonical_file}")
            raise FileNotFoundError(f"Canonical dataset required: {self.canonical_file}")
            
        # Load data in chunks để xử lý dataset lớn
        chunk_size = 50000
        chunks = []
        
        for chunk in pd.read_csv(self.canonical_file, chunksize=chunk_size):
            # Filter chỉ lấy MQTT protocol records
            mqtt_chunk = chunk[chunk['protocol'].str.contains('MQTT', case=False, na=False)]
            if not mqtt_chunk.empty:
                chunks.append(mqtt_chunk)
                
        if chunks:
            self.canonical_data = pd.concat(chunks, ignore_index=True)
            logger.info(f"[OK] Loaded {len(self.canonical_data)} MQTT records from canonical dataset")
        else:
            logger.error("❌ No MQTT records found in canonical dataset")
            raise ValueError("No MQTT data in canonical dataset")
    
    def _prepare_device_datasets(self):
        """Chuẩn bị data cho từng device type từ canonical dataset"""
        logger.info("[SETUP] Preparing device datasets from canonical schema...")
        
        # Group by device types dựa trên payload patterns và topics
        device_patterns = {
            # Original devices
            'Temperature': ['temperature', 'temp'],
            'Humidity': ['humidity', 'humid'],
            'CO2': ['co2', 'co-gas', 'gas'],
            'Light': ['light', 'lux', 'intensity'], 
            'Motion': ['motion', 'movement', 'pir'],
            'Smoke': ['smoke', 'fire'],
            'Fan': ['fan', 'speed'],
            'Door': ['door', 'lock'],
            'Vibration': ['vibration', 'vib'],
            
            # Edge-IIoT devices  
            'DistanceSensor': ['Distance'],
            'FlameSensor': ['Flame_Sensor'],
            'PhLevelSensor': ['PhLv'],
            'SoilMoisture': ['soil_moisture'],
            'SoundSensor': ['sound_sensors'],
            'WaterLevel': ['WaterLV'],
            
            # Gotham city devices
            'AirQuality': ['city/air'],
            'CoolerMotor': ['vibration/cooler'],
            'HydraulicSystem': ['hydraulic/rig'],
            'PredictiveMaintenance': ['maintenance/iotsim']
        }
        
        for device_type, patterns in device_patterns.items():
            # Filter records có payload match với device patterns hoặc topic match
            device_records = self.canonical_data[
                (self.canonical_data['Payload_sample'].str.contains(
                    '|'.join(patterns), case=False, na=False
                )) |
                (self.canonical_data['topic'].str.contains(
                    '|'.join(patterns), case=False, na=False
                ))
            ].copy()
            
            if not device_records.empty:
                # Sample records để tránh duplicate quá nhiều
                sample_size = min(1000, len(device_records))
                self.device_data[device_type] = device_records.sample(n=sample_size).reset_index(drop=True)
                logger.info(f"  [DEVICE] {device_type}: {len(self.device_data[device_type])} records prepared")
            else:
                # Tạo synthetic data nếu không có trong canonical
                logger.warning(f"  [WARNING] {device_type}: No canonical data found, will generate synthetic")
                self.device_data[device_type] = self._generate_synthetic_canonical(device_type)
    
    def _generate_synthetic_canonical(self, device_type):
        """Generate synthetic canonical data cho device type không có trong dataset"""
        synthetic_records = []
        
        # Template cho synthetic canonical records
        base_record = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'src_ip': '192.168.1.100',
            'src_port': random.randint(50000, 60000), 
            'dst_ip': self.broker,
            'dst_port': self.port,
            'protocol': 'MQTT',
            'packet_type': 'PUBLISH',
            'qos': random.choice([0, 1, 2]),
            'retain': 0,
            'dupflag': 0,
            'Label': 'Normal'
        }
        
        # Device-specific payloads theo canonical format
        payload_templates = {
            # Original devices
            'Temperature': lambda: json.dumps({
                "device_id": f"temp_{random.randint(1,5):03d}",
                "value": round(random.uniform(15.0, 35.0), 1),
                "unit": "celsius",
                "timestamp": int(time.time())
            }),
            'Humidity': lambda: json.dumps({
                "device_id": f"hum_{random.randint(1,5):03d}", 
                "value": round(random.uniform(30.0, 80.0), 1),
                "unit": "percent"
            }),
            'CO2': lambda: json.dumps({
                "device_id": f"co2_{random.randint(1,3):03d}",
                "value": random.randint(380, 600),
                "unit": "ppm"
            }),
            
            # Edge-IIoT devices
            'DistanceSensor': lambda: json.dumps({
                "device_id": f"distance_{random.randint(1,3):03d}",
                "distance": round(random.uniform(0.5, 100.0), 2),
                "unit": "cm"
            }),
            'FlameSensor': lambda: json.dumps({
                "device_id": f"flame_{random.randint(1,3):03d}",
                "flame_detected": random.choice([True, False]),
                "intensity": random.randint(0, 1023)
            }),
            'PhLevelSensor': lambda: json.dumps({
                "device_id": f"ph_{random.randint(1,3):03d}",
                "ph_level": round(random.uniform(4.0, 10.0), 2),
                "temperature": round(random.uniform(20.0, 30.0), 1)
            }),
            'SoilMoisture': lambda: json.dumps({
                "device_id": f"soil_{random.randint(1,3):03d}",
                "moisture": round(random.uniform(20.0, 80.0), 1),
                "unit": "percent"
            }),
            'SoundSensor': lambda: json.dumps({
                "device_id": f"sound_{random.randint(1,3):03d}",
                "decibel": round(random.uniform(30.0, 90.0), 1),
                "frequency": random.randint(200, 8000)
            }),
            'WaterLevel': lambda: json.dumps({
                "device_id": f"water_{random.randint(1,3):03d}",
                "level": round(random.uniform(0.0, 100.0), 2),
                "unit": "percent"
            }),
            
            # Gotham city devices
            'AirQuality': lambda: json.dumps({
                "device_id": f"airquality_{random.randint(1,3):03d}",
                "pm25": round(random.uniform(5.0, 50.0), 1),
                "pm10": round(random.uniform(10.0, 80.0), 1),
                "co2": random.randint(400, 800),
                "aqi": random.randint(50, 150)
            }),
            'CoolerMotor': lambda: json.dumps({
                "device_id": f"cooler_{random.randint(1,3):03d}",
                "vibration_x": round(random.uniform(-2.0, 2.0), 3),
                "vibration_y": round(random.uniform(-2.0, 2.0), 3),
                "vibration_z": round(random.uniform(-2.0, 2.0), 3),
                "rpm": random.randint(1800, 3600)
            }),
            'HydraulicSystem': lambda: json.dumps({
                "device_id": f"hydraulic_{random.randint(1,3):03d}",
                "pressure": round(random.uniform(100.0, 300.0), 1),
                "flow_rate": round(random.uniform(10.0, 50.0), 1),
                "temperature": round(random.uniform(40.0, 80.0), 1)
            }),
            'PredictiveMaintenance': lambda: json.dumps({
                "device_id": f"maintenance_{random.randint(1,3):03d}",
                "status": random.choice(["low", "medium", "high"]),
                "score": round(random.uniform(0.0, 1.0), 3),
                "next_maintenance": random.randint(1, 30)
            })
        }
        
        payload_gen = payload_templates.get(device_type, 
            lambda: json.dumps({"device_id": f"{device_type.lower()}_{random.randint(1,3):03d}", "value": random.randint(1, 100)})
        )
        
        # Generate 100 synthetic records
        for i in range(100):
            record = base_record.copy()
            record.update({
                'client_id': f"{device_type.lower()}_device_{i%5+1:03d}",
                'topic': f"site/canonical/{device_type.lower()}/device_{i%5+1:03d}/telemetry",
                'Payload_sample': payload_gen(),
                'payload_length': len(record.get('Payload_sample', '')),
                'msgid': random.randint(1, 65535) if record['qos'] > 0 else None
            })
            synthetic_records.append(record)
            
        return pd.DataFrame(synthetic_records)
    
    def start_simulation(self, devices=None, publish_interval=2.0, duration=0):
        """
        Bắt đầu simulation theo flow chuẩn:
        Canonical Data -> MQTT Publish -> Broker Logging
        """
        logger.info("[START] Starting Canonical MQTT Simulation Flow")
        logger.info(f"[TARGET] Target: {self.broker}:{self.port}")
        logger.info(f"[TIMING] Publish interval: {publish_interval}s")
        
        # Default tất cả devices nếu không specify
        if devices is None:
            devices = list(self.device_data.keys())
            
        available_devices = [d for d in devices if d in self.device_data]
        if not available_devices:
            logger.error("[ERROR] No valid devices found in canonical dataset")
            return
            
        logger.info(f"[DEVICES] Simulating {len(available_devices)} device types:")
        for device in available_devices:
            logger.info(f"   - {device}: {len(self.device_data[device])} canonical records")
        
        # Start simulation threads
        threads = []
        for device_type in available_devices:
            thread = threading.Thread(
                target=self._simulate_device_canonical,
                args=(device_type, publish_interval),
                daemon=True
            )
            thread.start()
            threads.append(thread)
            
        logger.info("=" * 60)
        logger.info("[START] Canonical simulation started! Press Ctrl+C to stop...")
        
        try:
            if duration > 0:
                time.sleep(duration)
                logger.info(f"[TIMER] Duration {duration}s completed")
            else:
                while not self.stop_event.is_set():
                    time.sleep(1)
        except KeyboardInterrupt:
            logger.info("🛑 Stopping simulation...")
        finally:
            self.stop_event.set()
            self._cleanup()
            
    def _simulate_device_canonical(self, device_type, publish_interval):
        """Simulate một device type từ canonical data"""
        device_records = self.device_data[device_type]
        # Ensure unique client ID để tránh collision
        timestamp = int(time.time() * 1000) % 10000  # Last 4 digits of timestamp
        client_id = f"canonical_{device_type.lower()}_{timestamp}_sim"
        
        # Create MQTT client with callback API v2
        client = mqtt.Client(
            client_id=client_id,
            callback_api_version=mqtt.CallbackAPIVersion.VERSION2
        )
        self.clients[device_type] = client
        
        try:
            # Connect to broker
            client.connect(self.broker, self.port, 60)
            client.loop_start()
            log_success(device_type)
            
            record_idx = 0
            while not self.stop_event.is_set():
                # Get next canonical record (cycle through available records)
                record = device_records.iloc[record_idx % len(device_records)]
                
                # Extract canonical fields but fix invalid topics
                original_topic = record.get('topic', f"canonical/{device_type.lower()}/telemetry")
                payload = record.get('Payload_sample', '{}')
                qos = int(record.get('qos', 0))
                retain = bool(record.get('retain', False))
                
                # Fix topic format - canonical dataset has invalid topics like "CO-GAS", "Door Lock"
                # Convert to proper MQTT topic format
                if pd.isna(original_topic) or not isinstance(original_topic, str) or '/' not in original_topic:
                    # Generate proper MQTT topic from device type
                    device_id = f"device_{(record_idx % 5) + 1:03d}"
                    topic = f"site/canonical/{device_type.lower()}/{device_id}/telemetry"
                else:
                    topic = original_topic
                
                # Enhance payload với canonical metadata
                try:
                    if payload and payload != '{}':
                        payload_data = json.loads(payload) if isinstance(payload, str) else {}
                    else:
                        payload_data = {}
                        
                    # Add canonical tracking fields
                    enhanced_payload = {
                        **payload_data,
                        "canonical_source": "dataset_canonical",
                        "device_type": device_type,
                        "simulator_timestamp": datetime.now(timezone.utc).isoformat(),
                        "canonical_record_id": record_idx,
                        "flow_stage": "canonical_to_mqtt"
                    }
                    
                    final_payload = json.dumps(enhanced_payload)
                    
                except (json.JSONDecodeError, Exception):
                    # Fallback cho malformed payload
                    final_payload = json.dumps({
                        "device_type": device_type,
                        "canonical_source": "dataset_canonical",
                        "raw_payload": str(payload)[:100],
                        "simulator_timestamp": datetime.now(timezone.utc).isoformat()
                    })
                
                # Publish canonical record to MQTT broker
                result = client.publish(topic, final_payload, qos=qos, retain=retain)
                
                if result.rc == mqtt.MQTT_ERR_SUCCESS:
                    logger.info(f"[{device_type}] -> {topic}: {final_payload[:100]}...")
                else:
                    logger.warning(f"[{device_type}] Publish failed: {result.rc}")
                
                record_idx += 1
                time.sleep(publish_interval)
                
        except Exception as e:
            log_error(device_type, e)
        finally:
            if client.is_connected():
                client.loop_stop()
                client.disconnect()
                
    def _cleanup(self):
        """Clean up connections"""
        logger.info("[CLEANUP] Cleaning up MQTT connections...")
        for device_type, client in self.clients.items():
            try:
                if client.is_connected():
                    client.loop_stop()
                    client.disconnect()
                    logger.info(f"  [OK] {device_type} disconnected")
            except Exception as e:
                logger.warning(f"  [WARNING] {device_type} cleanup error: {e}")

def main():
    parser = argparse.ArgumentParser(description="Canonical MQTT IoT Simulator - Flow chuẩn")
    parser.add_argument("--canonical-file", default="canonical_dataset.csv", 
                       help="Path to canonical dataset CSV")
    parser.add_argument("--broker", default="localhost", help="MQTT broker address")
    parser.add_argument("--port", type=int, default=1883, help="MQTT broker port")
    parser.add_argument("--devices", nargs="+", 
                       choices=["Temperature", "Humidity", "CO2", "Light", "Motion", "Smoke", "Fan", "Door", "Vibration"],
                       help="Specific device types to simulate")
    parser.add_argument("--publish-interval", type=float, default=2.0,
                       help="Interval between publishes (seconds)")
    parser.add_argument("--duration", type=int, default=0,
                       help="Simulation duration in seconds (0 = infinite)")
    
    args = parser.parse_args()
    
    try:
        simulator = CanonicalMQTTSimulator(
            canonical_file=args.canonical_file,
            broker=args.broker,
            port=args.port
        )
        
        simulator.start_simulation(
            devices=args.devices,
            publish_interval=args.publish_interval,
            duration=args.duration
        )
        
    except Exception as e:
        logger.error(f"[ERROR] Simulation failed: {e}")
        return 1
        
    logger.info("[COMPLETE] Canonical simulation completed")
    return 0

if __name__ == "__main__":
    exit(main())