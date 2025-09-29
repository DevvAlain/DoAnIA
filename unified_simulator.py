import argparse, threading, time, os, json, csv
import paho.mqtt.client as mqtt
import random
from datetime import datetime

DEVICE_CONFIGS = {
    "Temperature": {
        "csv_file": "TemperatureMQTTset.csv",
        "topic_template": "site/tenantA/zone1/temperature/{device_id}/telemetry",
        "payload_generator": lambda: {
            "timestamp": int(time.time()),
            "value": round(random.uniform(15.0, 35.0), 1),
            "unit": "C"
        },
        "device_count": 5,
        "username": "sensor_temp"
    },
    "Humidity": {
        "csv_file": "HumidityMQTTset.csv", 
        "topic_template": "site/tenantA/zone1/humidity/{device_id}/telemetry",
        "payload_generator": lambda: {
            "value": round(random.uniform(30.0, 80.0), 1),
            "unit": "%"
        },
        "device_count": 5,
        "username": "sensor_hum"
    },
    "CO2": {
        "csv_file": "CO-GasMQTTset.csv",
        "topic_template": "site/tenantA/zone2/co2/{device_id}/telemetry", 
        "payload_generator": lambda: {
            "value": random.randint(380, 600),
            "unit": "ppm"
        },
        "device_count": 3,
        "username": "sensor_co2"
    },
    "Vibration": {
        "csv_file": "FanSpeedControllerMQTTset.csv",
        "topic_template": "site/tenantA/zone3/vibration/{device_id}/telemetry",
        "payload_generator": lambda: {
            "rms": round(random.uniform(0.01, 0.05), 3),
            "freq": random.randint(50, 200)
        },
        "device_count": 2,
        "username": "sensor_vib"
    },
    "Smoke": {
        "csv_file": "SmokeMQTTset.csv",
        "topic_template": "site/tenantA/zone1/smoke/{device_id}/telemetry",
        "payload_generator": lambda: {
            "value": round(random.uniform(0.01, 0.1), 3),
            "alarm": random.choice([True, False]) if random.random() < 0.1 else False
        },
        "device_count": 4,
        "username": "sensor_smoke"
    },
    "AirQuality": {
        "csv_file": "CO-GasMQTTset.csv",
        "topic_template": "site/tenantA/zone4/airquality/{device_id}/telemetry",
        "payload_generator": lambda: {
            "pm2_5": round(random.uniform(5.0, 25.0), 1),
            "pm10": round(random.uniform(10.0, 50.0), 1)
        },
        "device_count": 3,
        "username": "sensor_air"
    },
    "Light": {
        "csv_file": "LightIntensityMQTTset.csv",
        "topic_template": "site/tenantA/zone2/light/{device_id}/telemetry",
        "payload_generator": lambda: {
            "lux": random.randint(50, 800)
        },
        "device_count": 6,
        "username": "sensor_light"
    },
    "Sound": {
        "csv_file": "FansensorMQTTset.csv",
        "topic_template": "site/tenantA/zone2/sound/{device_id}/telemetry", 
        "payload_generator": lambda: {
            "db": random.randint(30, 80)
        },
        "device_count": 4,
        "username": "sensor_sound"
    },
    "WaterLevel": {
        "csv_file": "HumidityMQTTset.csv",
        "topic_template": "site/tenantA/zone5/waterlevel/{device_id}/telemetry",
        "payload_generator": lambda: {
            "level": round(random.uniform(0.5, 2.0), 2),
            "unit": "m"
        },
        "device_count": 2,
        "username": "sensor_water"
    }
}

LEGACY_DEVICES = [
    ("Temperature", "TemperatureMQTTset.csv", "sensor_temp"),
    ("Light", "LightIntensityMQTTset.csv", "sensor_light"),
    ("Humidity", "HumidityMQTTset.csv", "sensor_hum"),
    ("Motion", "MotionMQTTset.csv", "sensor_motion"),
    ("CO-Gas", "CO-GasMQTTset.csv", "sensor_co"),
    ("Smoke", "SmokeMQTTset.csv", "sensor_smoke"),
    ("FanSpeed", "FanSpeedControllerMQTTset.csv", "sensor_fanspeed"),
    ("DoorLock", "DoorlockMQTTset.csv", "sensor_door"),
    ("FanSensor", "FansensorMQTTset.csv", "sensor_fan"),
]

def mk_client(cid, username=None):
    c = mqtt.Client(client_id=cid)
    if username: 
        c.username_pw_set(username)
    return c

def enhanced_device_thread(device_name, config, broker, port, username=None, loop=True, publish_interval=None):
    
    connected = False
    retry_count = 0
    max_retries = 5
    
    while not connected and retry_count < max_retries:
        try:
            clients = []
            for device_idx in range(config["device_count"]):
                device_id = f"device_{device_idx+1:03d}"
                client_id = f"{device_name}_{device_id}_client"
                topic = config["topic_template"].format(device_id=device_id)
                
                client = mk_client(client_id, username or config["username"])
                client.connect(broker, port, 60)
                client.loop_start()
                
                clients.append({
                    "client": client,
                    "device_id": device_id,
                    "topic": topic,
                    "client_id": client_id
                })
            
            connected = True
            print(f"[Enhanced] {device_name}: connected {config['device_count']} devices to {broker}:{port}")
            
            while loop:
                for client_info in clients:
                    try:
                        payload_data = config["payload_generator"]()
                        payload_json = json.dumps(payload_data)
                        
                        result = client_info["client"].publish(client_info["topic"], payload_json)
                        
                        if result.rc == mqtt.MQTT_ERR_SUCCESS:
                            print(f"[{client_info['client_id']}] -> {client_info['topic']}: {payload_json}")
                        else:
                            print(f"[{client_info['client_id']}] publish failed: {result.rc}")
                        
                    except Exception as e:
                        print(f"[{client_info['client_id']}] publish error: {e}")
                
                if publish_interval is not None:
                    time.sleep(publish_interval)
                else:
                    time.sleep(random.uniform(2.0, 5.0))
            
        except Exception as e:
            retry_count += 1
            print(f"[Enhanced] {device_name} connect failed (attempt {retry_count}/{max_retries}): {e}")
            time.sleep(5)
    
    if not connected:
        print(f"[Enhanced] {device_name} failed to connect after {max_retries} attempts")

def legacy_device_thread(device_name, csv_path, broker, port, username=None, loop=True, publish_interval=None):
    
    topic = f"site/tenantA/home/{device_name}/telemetry"
    client = mk_client(f"{device_name}-replayer", username)
    
    connected = False
    while not connected:
        try:
            client.connect(broker, port, 60)
            client.loop_start()
            connected = True
            print(f"[Legacy] {device_name} connected to {broker}:{port}")
        except Exception as e:
            print(f"[Legacy] {device_name} connect failed, retrying in 5s: {e}")
            time.sleep(5)

    rows = []
    try:
        with open(csv_path, newline='', encoding='utf-8') as f:
            r = csv.DictReader(f)
            for row in r:
                if row.get('mqtt.msgtype') == '3':
                    rows.append(row)
    except Exception as e:
        print(f"[Legacy] {device_name} failed to load {csv_path}: {e}")
        return

    i = 0
    while loop:
        if not rows:
            print(f"[Legacy] No valid MQTT data found in {csv_path}")
            break
            
        row = rows[i % len(rows)]
        
        tcp_payload = row.get('tcp.payload', '')
        if tcp_payload:
            try:
                payload_bytes = bytes.fromhex(tcp_payload)
                if len(payload_bytes) > 10:
                    payload_str = payload_bytes[10:].decode('utf-8', errors='ignore')
                    if payload_str.strip().replace('-', '').replace('.', '').isdigit():
                        try:
                            value = float(payload_str.strip())
                            payload = json.dumps({"value": value, "source": "csv_replay"})
                        except:
                            payload = json.dumps({"value": payload_str.strip(), "source": "csv_replay"})
                    else:
                        payload = json.dumps({"value": payload_str.strip(), "source": "csv_replay"})
                else:
                    payload = json.dumps({"value": round(random.uniform(10, 100), 2), "source": "generated"})
            except:
                payload = json.dumps({"value": round(random.uniform(10, 100), 2), "source": "generated"})
        else:
            payload = json.dumps({"value": round(random.uniform(10, 100), 2), "source": "generated"})

        result = client.publish(topic, payload)
        if result.rc == mqtt.MQTT_ERR_SUCCESS:
            print(f"[Legacy] {device_name} -> {topic}: {payload}")
        
        if publish_interval is not None:
            time.sleep(publish_interval)
        else:
            time.sleep(0.1 + random.random()*0.1)
        i += 1

def main():
    parser = argparse.ArgumentParser(description="Unified MQTT IoT Simulator")
    
    parser.add_argument("--broker", default="localhost", help="MQTT broker address")
    parser.add_argument("--port", type=int, default=1883, help="MQTT broker port")
    parser.add_argument("--publish-interval", type=float, help="Fixed delay (s) between publishes")
    
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument("--enhanced", action="store_true", default=True, 
                           help="Use enhanced mode with realistic IoT payloads (default)")
    mode_group.add_argument("--legacy", action="store_true", 
                           help="Use legacy mode replaying from CSV data")
    
    parser.add_argument("--devices", nargs="+", 
                       help="Specific devices to simulate (enhanced mode) or device names (legacy)")
    parser.add_argument("--indir", default="datasets", 
                       help="Folder containing device CSV files (legacy mode)")
    
    args = parser.parse_args()
    
    if args.legacy:
        mode = "legacy"
        print(f"🔄 LEGACY MODE: Replaying from CSV data")
    else:
        mode = "enhanced"  
        print(f"✨ ENHANCED MODE: Realistic IoT payload generation")
    
    print(f"🎯 Target broker: {args.broker}:{args.port}")
    print(f"⏱️  Publish interval: {args.publish_interval or 'auto'}")
    
    threads = []
    
    if mode == "enhanced":
        devices_to_run = args.devices if args.devices else list(DEVICE_CONFIGS.keys())
        
        print(f"📡 Starting {len(devices_to_run)} enhanced device simulators:")
        for device_name in devices_to_run:
            print(f"   - {device_name}")
        print("=" * 60)
        
        for device_name in devices_to_run:
            if device_name not in DEVICE_CONFIGS:
                print(f"❌ Unknown device: {device_name}")
                continue
                
            config = DEVICE_CONFIGS[device_name]
            
            t = threading.Thread(
                target=enhanced_device_thread, 
                args=(device_name, config, args.broker, args.port, None, True, args.publish_interval), 
                daemon=True
            )
            t.start()
            threads.append(t)
            print(f"✅ Started {device_name} simulator with {config['device_count']} devices")
            time.sleep(0.5)
    
    else:
        devices_to_run = LEGACY_DEVICES
        if args.devices:
            device_names = [d.lower() for d in args.devices]
            devices_to_run = [(name, fname, username) for name, fname, username in LEGACY_DEVICES 
                            if name.lower() in device_names]
        
        print(f"📡 Starting {len(devices_to_run)} legacy device simulators:")
        for name, _, _ in devices_to_run:
            print(f"   - {name}")
        print("=" * 60)
        
        for name, fname, username in devices_to_run:
            csv_path = os.path.join(args.indir, fname)
            if not os.path.exists(csv_path):
                print(f"❌ Missing {csv_path} - skipping {name}")
                continue
            
            t = threading.Thread(
                target=legacy_device_thread, 
                args=(name, csv_path, args.broker, args.port, username, True, args.publish_interval), 
                daemon=True
            )
            t.start()
            threads.append(t)
            print(f"✅ Started {name} legacy simulator -> {csv_path}")
            time.sleep(0.5)

    print("=" * 60)
    print("🚀 All simulators started! Press Ctrl+C to stop...")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n🛑 Stopping simulators...")

if __name__ == "__main__":
    main()
