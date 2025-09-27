#!/usr/bin/env python3
"""
Simulator for 9 IoT devices (MQTT) producing telemetry matching canonical schema.
Features:
 - Fields: timestamp, src_ip, src_port, dst_ip, dst_port, client_id, topic,
   payload_sample, payload_length, protocol, Label, qos, retain, dupflag,
   packet_type, username, msgid, connack_code, auth_reason
 - Randomized QoS (0,1,2), retain, dupflag; msgid set when qos>0
 - Optional simple attack scenarios per-device:
     - publish_flood: rapid burst of publishes for short duration
     - dup_client: simulate same client_id reused from different src_ip
     - brute_connect: many CONNECT attempts with failing connack_code
 - CLI-configurable global broker host/port and optional --attack to enable demo attacks
"""
import argparse
import json
import random
import threading
import time
import socket
from typing import Optional

import paho.mqtt.client as mqtt

BROKER_DEFAULT = "emqx"
BROKER_PORT_DEFAULT = 1883

# Device definitions: (device_name, src_ip, base_interval_seconds, username(optional), suggested_topic_suffix)
DEVICES = [
    ("Temperature", "192.168.0.151", 5, "sensor_temp", "temperature"),
    ("Light",       "192.168.0.150", 5, "sensor_light", "light"),
    ("Humidity",    "192.168.0.152", 6, "sensor_hum", "humidity"),
    ("Motion",      "192.168.0.154", 4, "sensor_motion", "motion"),
    ("CO-Gas",      "192.168.0.155", 7, "sensor_co", "co_gas"),
    ("Smoke",       "192.168.0.180", 6, "sensor_smoke", "smoke"),
    ("FanSpeed",    "192.168.0.173", 8, "sensor_fanspeed", "fan_speed"),
    ("DoorLock",    "192.168.0.176", 10, "sensor_door", "door_lock"),
    ("FanSensor",   "192.168.0.178", 8, "sensor_fan", "fan_sensor"),
]

# Attack presets for demo purposes: can be enabled per device by name (strings)
# Supported: 'publish_flood', 'dup_client', 'brute_connect'
ATTACK_PRESETS = {
    # device_name: [attack_types...]
    # e.g. "Temperature": ["publish_flood"]
}

# Helper to create MQTT client
def mk_client(client_id: str, username: Optional[str] = None):
    c = mqtt.Client(client_id=client_id, protocol=mqtt.MQTTv311)
    if username:
        c.username_pw_set(username)  # no password in this sim
    # optional callbacks for debugging
    def on_connect(client, userdata, flags, rc):
        # rc 0 = success
        pass
    c.on_connect = on_connect
    return c

# Utilities
def gen_msgid():
    return random.randint(1, 65535)

def random_port():
    return random.randint(10000, 65000)

def now_ts():
    return int(time.time())

def generate_payload(device_name, src_ip, dst_ip, topic, username=None, attack_label="normal"):
    # Random message sample depending on device type
    base = random.uniform(10, 100)
    payload_json = {
        "value": round(base + random.uniform(-2, 2), 3),
        "unit": "auto"
    }
    payload_str = json.dumps(payload_json)
    payload_length = len(payload_str.encode("utf-8"))

    # randomize MQTT flags
    qos = random.choices([0, 1, 2], weights=[0.7, 0.2, 0.1])[0]
    retain = random.random() < 0.05  # 5% retained
    dupflag = random.random() < 0.01  # rare duplicate flag
    packet_type = "PUBLISH"

    msg = {
        "timestamp": now_ts(),
        "src_ip": src_ip,
        "src_port": random_port(),
        "dst_ip": dst_ip,
        "dst_port": BROKER_PORT_DEFAULT,
        "client_id": f"{device_name}-{src_ip}",
        "topic": topic,
        "payload": payload_json,
        "payload_length": payload_length,
        "payload_sample": round(base, 3),
        "protocol": "MQTT",
        "Label": attack_label,
        "qos": qos,
        "retain": int(retain),
        "dupflag": int(dupflag),
        "packet_type": packet_type,
        "username": username or None,
        "msgid": gen_msgid() if qos > 0 else None,
        "connack_code": None,
        "auth_reason": None,
    }
    return msg, payload_str, qos, retain, dupflag

# Attack behaviors
def do_publish_flood(client, topic, payload_str, qos, retain, burst_count=50, interval_between=0.02):
    for _ in range(burst_count):
        client.publish(topic, payload_str, qos=qos, retain=retain)
        time.sleep(interval_between)

def do_dup_client_publish(broker_host, broker_port, original_client_id, topic, payload_str, qos, retain):
    # Create a new client from different src_ip (simulated by suffix)
    fake_client_id = f"{original_client_id}-dup-{random.randint(1,999)}"
    c = mk_client(fake_client_id)
    try:
        c.connect(broker_host, broker_port, 60)
        c.loop_start()
        c.publish(topic, payload_str, qos=qos, retain=retain)
        c.loop_stop()
        c.disconnect()
    except Exception as e:
        print(f"[dup_client] error connecting fake client {fake_client_id}: {e}")

def do_brute_connect(broker_host, broker_port, target_client_base, attempts=30, fail_ratio=0.8):
    # Simulate many CONNECTs, most failing (we set connack_code in logs, but brokers decide real response)
    for i in range(attempts):
        cid = f"{target_client_base}-brute-{i}-{random.randint(0,999)}"
        c = mk_client(cid)
        try:
            c.connect(broker_host, broker_port, 2)
            # we immediately disconnect; connack_code cannot be forced here without broker hooks
            c.disconnect()
        except Exception:
            pass
        time.sleep(0.05)

def simulate_device(device_name, src_ip, interval_seconds, broker_host, broker_port, username=None, enabled_attacks=None):
    client_id = f"{device_name}-{src_ip}"
    topic = f"site/tenantA/home/{device_name}/{src_ip}/telemetry"
    c = mk_client(client_id, username)

    # retry loop để chắc chắn kết nối được
    connected = False
    while not connected:
        try:
            c.connect(broker_host, broker_port, 60)
            c.loop_start()
            connected = True
            print(f"[{device_name}] connected to {broker_host}:{broker_port}")
        except Exception as e:
            print(f"[{device_name}] connect failed, retrying in 5s: {e}")
            time.sleep(5)

    # internal counters to occasionally trigger attack/demo patterns
    tick = 0
    while True:
        # normal telemetry
        attack_label = "normal"
        msg, payload_str, qos, retain, dupflag = generate_payload(device_name, src_ip, broker_host, topic, username, attack_label)
        # publish normally
        try:
            info = c.publish(topic, payload_str, qos=qos, retain=retain)
            # optionally log when publish fails
            if info.rc != mqtt.MQTT_ERR_SUCCESS:
                print(f"[{device_name}] publish rc={info.rc}")
        except Exception as e:
            print(f"[{device_name}] publish exception: {e}")

        # occasionally (by tick) perform attack/demo patterns if enabled for this device
        if enabled_attacks:
            # publish_flood: every ~60 ticks do a short burst
            if "publish_flood" in enabled_attacks and tick % 60 == 0:
                print(f"[{device_name}] launching publish_flood demo")
                do_publish_flood(c, topic, payload_str, qos=qos, retain=retain, burst_count=40, interval_between=0.01)
            # dup_client: occasionally send a publish from a fake client
            if "dup_client" in enabled_attacks and tick % 90 == 0:
                print(f"[{device_name}] launching dup_client demo")
                do_dup_client_publish(broker_host, broker_port, client_id, topic, payload_str, qos, retain)
            # brute_connect: occasional burst of connects
            if "brute_connect" in enabled_attacks and tick % 120 == 0:
                print(f"[{device_name}] launching brute_connect demo")
                threading.Thread(target=do_brute_connect, args=(broker_host, broker_port, client_id, 40), daemon=True).start()

        tick += 1
        time.sleep(interval_seconds)

def main():
    parser = argparse.ArgumentParser(description="MQTT 9-device simulator (full schema)")
    parser.add_argument("--broker", default=BROKER_DEFAULT, help="MQTT broker host (default emqx)")
    parser.add_argument("--port", type=int, default=BROKER_PORT_DEFAULT, help="MQTT broker port")
    parser.add_argument("--enable-attacks", action="store_true", help="Enable demo attack patterns defined in ATTACK_PRESETS")
    parser.add_argument("--list-devices", action="store_true", help="List devices and exit")
    args = parser.parse_args()

    if args.list_devices:
        for d in DEVICES:
            print(f"- {d[0]} ({d[1]}) interval={d[2]}s username={d[3]}")
        return

    # small local override: example presets for attacks (demo)
    enabled_attacks_global = args.enable_attacks
    # If global enabled, use hardcoded samples (you can edit ATTACK_PRESETS above)
    attack_map = {}
    if enabled_attacks_global:
        # Example: toggle some attacks for a couple devices for demo
        attack_map = {
            "Temperature": ["publish_flood"],
            "CO-Gas": ["dup_client"],
            "DoorLock": ["brute_connect"]
        }

    print(f"Starting simulator -> broker={args.broker}:{args.port} (attacks_enabled={enabled_attacks_global})")
    # start threads
    for device_name, src_ip, interval, username, suffix in DEVICES:
        attacks_for_device = attack_map.get(device_name, ATTACK_PRESETS.get(device_name))
        t = threading.Thread(
            target=simulate_device,
            args=(device_name, src_ip, interval, args.broker, args.port, username, attacks_for_device),
            daemon=True
        )
        t.start()

    # keep main alive
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Simulator stopped by user")

if __name__ == "__main__":
    main()
