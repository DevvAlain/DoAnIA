"""MQTT simulator that replays 9 IoT devices from canonical CSV datasets."""

from __future__ import annotations

import argparse
import csv
import json
import threading
import time
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional

import paho.mqtt.client as mqtt

DEVICE_TOPIC_MAP: Dict[str, str] = {
    "Temperature": "site/tenantA/zone1/temperature/{device_id}/telemetry",
    "Humidity": "site/tenantA/zone1/humidity/{device_id}/telemetry",
    "CO-GAS": "site/tenantA/zone2/co2/{device_id}/telemetry",
    "Smoke": "site/tenantA/zone1/smoke/{device_id}/telemetry",
    "Door Lock": "site/tenantA/zone1/doorlock/{device_id}/telemetry",
    "Movement": "site/tenantA/zone3/movement/{device_id}/telemetry",
    "Fan": "site/tenantA/zone2/fan/{device_id}/telemetry",
    "Fan Speed": "site/tenantA/zone2/fanspeed/{device_id}/telemetry",
    "Light Intensity": "site/tenantA/zone2/light/{device_id}/telemetry",
}

CANONICAL_DEVICES: Iterable[str] = DEVICE_TOPIC_MAP.keys()


@dataclass
class Event:
    topic_path: str
    payload: dict
    interval: float


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Replay MQTT payloads from canonical CSV datasets.")
    parser.add_argument("--broker", default="localhost", help="MQTT broker address")
    parser.add_argument("--port", type=int, default=1883, help="MQTT broker port")
    parser.add_argument("--features", default="features_canonical_dataset.csv", help="Path to features CSV")
    parser.add_argument("--canonical", default="canonical_dataset.csv", help="Path to canonical CSV")
    parser.add_argument("--devices", nargs="+", choices=sorted(DEVICE_TOPIC_MAP.keys()), help="Subset of devices to replay")
    parser.add_argument("--max-rows", type=int, help="Maximum rows per device (defaults to entire dataset)")
    parser.add_argument("--speedup", type=float, default=1.0, help="Speed factor (>1 accelerates playback)")
    parser.add_argument("--min-interval", type=float, default=0.05, help="Minimum publish interval in seconds")
    parser.add_argument("--default-interval", type=float, default=1.0, help="Fallback interval when iat_sec is missing")
    parser.add_argument("--username", help="MQTT username")
    parser.add_argument("--password", help="MQTT password")
    parser.add_argument("--once", action="store_true", help="Replay dataset once instead of looping")
    parser.add_argument("--verbose", action="store_true", help="Print every publish payload")
    return parser.parse_args()


def normalize_ts(ts: str) -> str:
    if not ts:
        return ""
    ts = ts.strip()
    if ts.endswith("Z"):
        ts = ts[:-1] + "+00:00"
    return ts.replace("T", " ")


def load_canonical_lookup(path: Path, allowed_topics: Iterable[str]) -> Dict[tuple[str, str, str], dict]:
    lookup: Dict[tuple[str, str, str], dict] = {}
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            topic = row.get("topic", "").strip()
            if topic not in allowed_topics:
                continue
            key = (topic, row.get("client_id", ""), normalize_ts(row.get("timestamp", "")))
            lookup[key] = row
    return lookup


def to_float(value: str) -> Optional[float]:
    if value is None:
        return None
    value = value.strip()
    if not value:
        return None
    try:
        return float(value)
    except ValueError:
        return None


def sanitize_device_id(client_id: str) -> str:
    cleaned = [ch.lower() if ch.isalnum() else "_" for ch in client_id]
    return "device_" + "".join(cleaned).strip("_")


def build_event(
    feature_row: dict,
    canonical_row: Optional[dict],
    topic_template: str,
    min_interval: float,
    default_interval: float,
    speedup: float,
) -> Event:
    client_id = feature_row.get("client_id", "")
    device_id = sanitize_device_id(client_id)
    topic_path = topic_template.format(device_id=device_id)

    numeric_value = to_float(feature_row.get("value"))
    raw_payload = (canonical_row or {}).get("Payload_sample", "").strip()
    fallback_value = to_float(raw_payload)

    payload: dict = {
        "ts": feature_row.get("ts"),
        "client_id": client_id,
        "label": feature_row.get("Label") or (canonical_row or {}).get("Label"),
        "metrics": {
            "payload_length": to_float(feature_row.get("payload_length")),
            "qos": to_float(feature_row.get("qos")),
            "retain": to_float(feature_row.get("retain_flag")),
            "dup": to_float(feature_row.get("dup_flag")),
            "msgid_present": bool(int(float(feature_row.get("msgid_present", 0)))) if feature_row.get("msgid_present") else False,
            "iat_sec": to_float(feature_row.get("iat_sec")),
        },
        "source": "features_canonical_dataset",
    }

    if numeric_value is not None:
        payload["value"] = numeric_value
    elif fallback_value is not None:
        payload["value"] = fallback_value

    if raw_payload and raw_payload != str(payload.get("value", "")):
        payload["raw_payload"] = raw_payload

    if canonical_row:
        payload["packet_type"] = canonical_row.get("packet_type")
        payload["username"] = canonical_row.get("username")
        payload["auth_reason"] = canonical_row.get("auth_reason")

    raw_interval = to_float(feature_row.get("iat_sec"))
    if raw_interval is None or raw_interval <= 0:
        raw_interval = default_interval
    interval = max(min_interval, raw_interval / max(speedup, 1e-6))

    return Event(topic_path=topic_path, payload=payload, interval=interval)


def load_events(
    features_path: Path,
    canonical_lookup: Dict[tuple[str, str, str], dict],
    devices: Iterable[str],
    min_interval: float,
    default_interval: float,
    speedup: float,
    max_rows: Optional[int],
) -> Dict[str, List[Event]]:
    events: Dict[str, List[Event]] = defaultdict(list)
    devices_set = set(devices)
    completed: set[str] = set()

    with features_path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            topic = row.get("topic", "").strip()
            if topic not in devices_set:
                continue

            if max_rows and len(events[topic]) >= max_rows:
                completed.add(topic)
                if completed == devices_set:
                    break
                continue

            key = (topic, row.get("client_id", ""), row.get("ts", ""))
            canonical_row = canonical_lookup.get(key)
            event = build_event(
                row,
                canonical_row,
                DEVICE_TOPIC_MAP[topic],
                min_interval,
                default_interval,
                speedup,
            )
            events[topic].append(event)

    for topic_events in events.values():
        topic_events.sort(key=lambda evt: evt.payload.get("ts") or "")

    return events


class DeviceSimulator(threading.Thread):
    def __init__(
        self,
        device_name: str,
        events: List[Event],
        broker: str,
        port: int,
        username: Optional[str],
        password: Optional[str],
        loop_forever: bool,
        verbose: bool,
    ) -> None:
        super().__init__(daemon=True)
        self.device_name = device_name
        self.events = events
        self.broker = broker
        self.port = port
        self.username = username
        self.password = password
        self.loop_forever = loop_forever
        self.verbose = verbose
        client_id = f"sim_{device_name.replace(' ', '_').lower()}"
        self.client = mqtt.Client(client_id=client_id)
        if username:
            self.client.username_pw_set(username, password)

    def run(self) -> None:
        self.client.connect(self.broker, self.port, 60)
        self.client.loop_start()
        publish_count = 0

        try:
            while True:
                for event in self.events:
                    payload_json = json.dumps(event.payload)
                    result = self.client.publish(event.topic_path, payload_json)
                    publish_count += 1
                    if self.verbose:
                        status = "OK" if result.rc == mqtt.MQTT_ERR_SUCCESS else f"ERR:{result.rc}"
                        print(f"[{self.device_name}] {status} -> {event.topic_path} :: {payload_json}")
                    time.sleep(event.interval)
                if not self.loop_forever:
                    break
        finally:
            self.client.loop_stop()
            self.client.disconnect()
            print(f"[{self.device_name}] stopped after {publish_count} publishes")


def main() -> None:
    args = parse_args()
    devices = args.devices or list(CANONICAL_DEVICES)

    features_path = Path(args.features)
    canonical_path = Path(args.canonical)

    if not features_path.exists():
        raise FileNotFoundError(f"Features dataset not found: {features_path}")
    if not canonical_path.exists():
        raise FileNotFoundError(f"Canonical dataset not found: {canonical_path}")

    print("📂 Loading canonical dataset lookup ...")
    canonical_lookup = load_canonical_lookup(canonical_path, devices)
    print(f"   → Loaded {len(canonical_lookup):,} canonical records for selected devices")

    print("📂 Loading feature dataset events ...")
    events_by_device = load_events(
        features_path,
        canonical_lookup,
        devices,
        args.min_interval,
        args.default_interval,
        args.speedup,
        args.max_rows,
    )

    for device in devices:
        if device not in events_by_device or not events_by_device[device]:
            raise RuntimeError(f"No events found for device '{device}'. Check dataset content.")

    print("🚀 Starting MQTT replay threads ...")
    threads: List[DeviceSimulator] = []
    for device in devices:
        events = events_by_device[device]
        print(f"   • {device}: {len(events):,} events -> {DEVICE_TOPIC_MAP[device]}")
        worker = DeviceSimulator(
            device,
            events,
            args.broker,
            args.port,
            args.username,
            args.password,
            loop_forever=not args.once,
            verbose=args.verbose,
        )
        worker.start()
        threads.append(worker)
        time.sleep(0.2)

    try:
        for thread in threads:
            thread.join()
    except KeyboardInterrupt:
        print("\n🛑 Interrupt received, stopping simulators ...")


if __name__ == "__main__":
    main()
