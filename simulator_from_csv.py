# simulator_from_csv.py
import argparse, threading, time, os, json, csv
import paho.mqtt.client as mqtt
import random

DEVICES = [
    # name, csv_filename (relative), username(optional)
    ("Temperature", "features_Temperature.csv", "sensor_temp"),
    ("Light", "features_Light_Intensity.csv", "sensor_light"),
    ("Humidity", "features_Humidity.csv", "sensor_hum"),
    ("Motion", "features_Movement.csv", "sensor_motion"),
    ("CO-Gas", "features_CO-GAS.csv", "sensor_co"),
    ("Smoke", "features_Smoke.csv", "sensor_smoke"),
    ("FanSpeed", "features_Fan_Speed.csv", "sensor_fanspeed"),
    ("DoorLock", "features_Door_Lock.csv", "sensor_door"),
    ("FanSensor", "features_Fan.csv", "sensor_fan"),
]

def mk_client(cid, username=None):
    c = mqtt.Client(client_id=cid)
    if username: c.username_pw_set(username)
    return c

def device_thread(device_name, csv_path, broker, port, username=None, loop=True, publish_interval=None):
    topic = f"site/tenantA/home/{device_name}/telemetry"
    client = mk_client(f"{device_name}-replayer", username)
    client.connect(broker, port, 60)
    client.loop_start()

    # read csv once into memory for simplicity
    rows = []
    with open(csv_path, newline='', encoding='utf-8') as f:
        r = csv.DictReader(f)
        for row in r:
            rows.append(row)

    i = 0
    while True:
        row = rows[i % len(rows)]
        # use 'value' column or payload if exists
        if 'payload' in row and row['payload']:
            try:
                payload = row['payload']
                # ensure it's a JSON string
                json.loads(payload)
            except:
                payload = json.dumps({"value": row.get('value','')})
        else:
            try:
                val = float(row.get('value','0'))
                payload = json.dumps({"value": val})
            except:
                payload = json.dumps({"value": row.get('value','')})

        client.publish(topic, payload)
        # wait: either use publish_interval param or use timestamp difference if present
        if publish_interval is not None:
            time.sleep(publish_interval)
        else:
            # no given interval; sleep small random to avoid blast
            time.sleep(0.1 + random.random()*0.1)
        i += 1

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--indir", default="./datasets")
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
