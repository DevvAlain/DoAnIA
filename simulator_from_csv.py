import argparse, threading, time, os, json, csv
import paho.mqtt.client as mqtt
import random

DEVICES = [
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
    if username: c.username_pw_set(username)
    return c

def device_thread(device_name, csv_path, broker, port, username=None, loop=True, publish_interval=None):
    topic = f"site/tenantA/home/{device_name}/telemetry"
    client = mk_client(f"{device_name}-replayer", username)
    
    connected = False
    while not connected:
        try:
            client.connect(broker, port, 60)
            client.loop_start()
            connected = True
            print(f"[{device_name}] connected to {broker}:{port}")
        except Exception as e:
            print(f"[{device_name}] connect failed, retrying in 5s: {e}")
            time.sleep(5)

    rows = []
    with open(csv_path, newline='', encoding='utf-8') as f:
        r = csv.DictReader(f)
        for row in r:
            if row.get('mqtt.msgtype') == '3':
                rows.append(row)

    i = 0
    while True:
        if not rows:
            print(f"No valid MQTT data found in {csv_path}")
            break
            
        row = rows[i % len(rows)]
        
        tcp_payload = row.get('tcp.payload', '')
        if tcp_payload:
            try:
                payload_bytes = bytes.fromhex(tcp_payload)
                if len(payload_bytes) > 10:
                    payload_str = payload_bytes[10:].decode('utf-8', errors='ignore')
                    if payload_str:
                        payload = json.dumps({"value": payload_str.strip()})
                    else:
                        payload = json.dumps({"value": round(random.uniform(10, 100), 2)})
                else:
                    payload = json.dumps({"value": round(random.uniform(10, 100), 2)})
            except:
                payload = json.dumps({"value": round(random.uniform(10, 100), 2)})
        else:
            payload = json.dumps({"value": round(random.uniform(10, 100), 2)})

        client.publish(topic, payload)
        if publish_interval is not None:
            time.sleep(publish_interval)
        else:
            time.sleep(0.1 + random.random()*0.1)
        i += 1

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--indir", default=".")
    parser.add_argument("--broker", default="localhost")
    parser.add_argument("--port", type=int, default=1883)
    parser.add_argument("--publish-interval", type=float, help="fixed delay (s) between publishes per device")
    args = parser.parse_args()

    threads = []
    for name, fname, username in DEVICES:
        path = os.path.join(args.indir, fname)
        if not os.path.exists(path):
            print("Missing", path, "- skipping")
            continue
        t = threading.Thread(target=device_thread, args=(name, path, args.broker, args.port, username, True, args.publish_interval), daemon=True)
        t.start()
        threads.append(t)
        print("started", name, "->", path)

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("stopped")

if __name__ == "__main__":
    main()
