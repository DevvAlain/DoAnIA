import argparse
import sys
from pathlib import Path
from typing import Iterable, List, Sequence, Set

import pandas as pd
import string

CANONICAL_COLUMNS = [
    "timestamp",
    "src_ip",
    "src_port",
    "dst_ip",
    "dst_port",
    "client_id",
    "topic",
    "topicfilter",
    "qos",
    "retain",
    "dupflag",
    "payload_length",
    "Payload_sample",
    "packet_type",
    "protocol",
    "connack_code",
    "Label",
    "username",
    "msgid",
    "auth_reason",
]

TIMESTAMP_CANDIDATES = [
    "timestamp",
    "ts",
    "time",
    "frame.time_epoch",
    "frame.time_relative",
    "Time",
    "SniffTimestamp",
]

SRC_IP_CANDIDATES = ["src_ip", "ip.src", "source_ip", "ipv4_src", "ip_source"]
DST_IP_CANDIDATES = ["dst_ip", "ip.dst", "destination_ip", "ipv4_dst", "ip_destination"]
SRC_PORT_CANDIDATES = ["src_port", "tcp.srcport", "source_port", "sport"]
DST_PORT_CANDIDATES = ["dst_port", "tcp.dstport", "destination_port", "dport"]
CLIENT_ID_CANDIDATES = [
    "client_id",
    "clientid",
    "mqtt.clientid",
    "device_id",
    "deviceid",
    "client",
]
TOPIC_CANDIDATES = ["topic", "mqtt.topic", "Topic", "publish_topic"]
TOPICFILTER_CANDIDATES = ["topicfilter", "mqtt.topicfilter", "subscription", "filter"]
QOS_CANDIDATES = ["qos", "mqtt.qos", "request_qos", "mqtt.sub.qos", "mqtt.suback.qos"]
RETAIN_CANDIDATES = ["retain", "retain_flag", "mqtt.retain", "mqtt.conflag.retain"]
DUP_CANDIDATES = ["dupflag", "dup_flag", "mqtt.dupflag"]
PAYLOAD_LENGTH_CANDIDATES = ["payload_length", "payload_len", "mqtt.msg_len", "mqtt.payload_len"]
PAYLOAD_PRIORITY = [
    ("payload_sample", False),
    ("payload", False),
    ("mqtt.msg", True),
    ("mqtt.willmsg", True),
    ("tcp.payload", True),
]
PACKET_TYPE_CANDIDATES = ["packet_type", "mqtt.msgtype", "msg_type", "message_type"]
PROTOCOL_CANDIDATES = ["protocol", "app_protocol", "mqtt.protoname", "proto_name"]
CONNACK_CANDIDATES = ["connack_code", "mqtt.conack.val", "connack", "return_code"]
LABEL_CANDIDATES = ["Label", "label", "attack_type", "attack_label", "class"]
USERNAME_CANDIDATES = ["username", "mqtt.username", "user"]
MSGID_CANDIDATES = ["msgid", "mqtt.msgid", "message_id"]
AUTH_REASON_CANDIDATES = ["auth_reason", "reason", "disconnect_reason", "auth.reason"]

MQTT_MSGTYPE_MAP = {
    1: "CONNECT",
    2: "CONNACK",
    3: "PUBLISH",
    4: "PUBACK",
    5: "PUBREC",
    6: "PUBREL",
    7: "PUBCOMP",
    8: "SUBSCRIBE",
    9: "SUBACK",
    10: "UNSUBSCRIBE",
    11: "UNSUBACK",
    12: "PINGREQ",
    13: "PINGRESP",
    14: "DISCONNECT",
    15: "AUTH",
}

TRUTHY_VALUES = {"true", "1", "yes", "y", "t"}
HEX_DIGITS = set("0123456789abcdefABCDEF")
PRINTABLE_SAFE = set(string.printable) - {"\t", "\r", "\n", "\x0b", "\x0c"}

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("inputs", nargs="*", default=["datasets"])
    parser.add_argument("--pattern", default="*.csv")
    parser.add_argument("--output", default="canonical_dataset.csv")
    parser.add_argument("--chunksize", type=int, default=50000)
    parser.add_argument("--protocols", default="MQTT,MQTTS,MQTT-TLS,AMQP,AMQPS,COAP,COAPS,DDS,HTTP,HTTPS,MODBUS,MODBUS-TCP,BACNET,BACNET/IP,OPC-UA,OPCUA,ZIGBEE,Z-WAVE,ZWAVE,LORAWAN,NB-IOT,BLE,BLUETOOTH,BLUETOOTH-LE")
    parser.add_argument("--force", action="store_true")
    return parser.parse_args()

def collect_input_paths(raw_inputs: Sequence[str], pattern: str) -> List[Path]:
    collected: List[Path] = []
    for raw in raw_inputs:
        path = Path(raw)
        if path.is_dir():
            collected.extend(sorted(path.glob(pattern)))
        elif path.is_file():
            collected.append(path)
        else:
            print(f"[warn] Input not found: {raw}", file=sys.stderr)
    unique: List[Path] = []
    seen = set()
    for item in collected:
        if item not in seen:
            unique.append(item)
            seen.add(item)
    return unique

def pick_series(frame: pd.DataFrame, candidates: Iterable[str]) -> pd.Series | None:
    for name in candidates:
        if name in frame.columns:
            return frame[name]
    return None

def parse_timestamp(frame: pd.DataFrame) -> pd.Series | None:
    series = pick_series(frame, TIMESTAMP_CANDIDATES)
    if series is None:
        return None
    numeric = pd.to_numeric(series, errors="coerce")
    dt = pd.to_datetime(numeric, unit="s", errors="coerce", utc=True)
    missing = dt.isna()
    if missing.any():
        dt_alt = pd.to_datetime(series, errors="coerce", utc=True)
        dt = dt.fillna(dt_alt)
    return dt

def format_timestamp(ts: pd.Series | None, frame_length: int) -> pd.Series:
    if ts is None:
        return pd.Series(["" for _ in range(frame_length)], dtype="object")
    formatted = ts.dt.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    return formatted.where(~ts.isna(), "")

def string_series(frame: pd.DataFrame, candidates: Iterable[str], default: str = "") -> pd.Series:
    series = pick_series(frame, candidates)
    if series is None:
        return pd.Series([default for _ in range(len(frame))], index=frame.index, dtype="object")
    return series.fillna("").astype(str).str.strip()

def bool_flag_series(frame: pd.DataFrame, candidates: Iterable[str]) -> pd.Series:
    series = pick_series(frame, candidates)
    if series is None:
        return pd.Series(0, index=frame.index, dtype="int64")
    cleaned = series.fillna("").astype(str).str.strip().str.lower()
    return cleaned.isin(TRUTHY_VALUES).astype("int64")

def numeric_series(
    frame: pd.DataFrame,
    candidates: Iterable[str],
    default: int | None = None,
    allow_na: bool = False,
) -> pd.Series:
    series = pick_series(frame, candidates)
    if series is None:
        if allow_na:
            return pd.Series(pd.NA, index=frame.index, dtype="Int64")
        fill_value = 0 if default is None else default
        return pd.Series(fill_value, index=frame.index, dtype="Int64")
    numeric = pd.to_numeric(series, errors="coerce")
    if allow_na:
        return numeric.astype("Int64")
    fill_value = 0 if default is None else default
    return numeric.fillna(fill_value).astype("Int64")

def determine_protocol(frame: pd.DataFrame) -> pd.Series:
    series = pick_series(frame, PROTOCOL_CANDIDATES)
    if series is None:
        if any(col.lower().startswith("mqtt") for col in frame.columns):
            base = pd.Series(["MQTT"] * len(frame), index=frame.index)
        else:
            base = pd.Series(["UNKNOWN"] * len(frame), index=frame.index)
    else:
        base = series.fillna("").astype(str)
    cleaned = base.str.strip()
    cleaned = cleaned.replace("", "UNKNOWN")
    cleaned = cleaned.str.upper()
    if any(col.lower().startswith("mqtt") for col in frame.columns):
        cleaned = cleaned.where(cleaned != "UNKNOWN", "MQTT")
    return cleaned

def sanitize_text(value: str, limit: int = 120) -> str:
    if not value:
        return ""
    filtered = ''.join(ch for ch in str(value) if ch in PRINTABLE_SAFE)
    cleaned = ' '.join(filtered.split())
    return cleaned[:limit]

def decode_hex_payload(value: str, limit: int = 120) -> str:
    text = str(value).strip()
    if not text:
        return ""
    candidate = text.replace(":", "").replace(" ", "")
    if candidate and all(ch in HEX_DIGITS for ch in candidate):
        padded = candidate if len(candidate) % 2 == 0 else "0" + candidate
        try:
            raw = bytes.fromhex(padded)
        except ValueError:
            return sanitize_text(text, limit)
        decoded = raw.decode("utf-8", errors="ignore")
        cleaned = sanitize_text(decoded, limit)
        if cleaned:
            return cleaned
        return raw[:limit].hex()
    return sanitize_text(text, limit)

def hex_length(value: str) -> int:
    text = str(value).strip()
    if not text:
        return 0
    candidate = text.replace(":", "").replace(" ", "")
    if candidate and all(ch in HEX_DIGITS for ch in candidate):
        return len(candidate) // 2
    return len(text)

def compute_payload_length(frame: pd.DataFrame) -> pd.Series:
    series = pick_series(frame, PAYLOAD_LENGTH_CANDIDATES)
    if series is not None:
        numeric = pd.to_numeric(series, errors="coerce")
        return numeric.astype("Int64")
    if "mqtt.msg" in frame.columns:
        lengths = frame["mqtt.msg"].fillna("").apply(hex_length)
        return pd.to_numeric(lengths, errors="coerce").astype("Int64")
    if "payload" in frame.columns:
        lengths = frame["payload"].fillna("").astype(str).str.len()
        return pd.to_numeric(lengths, errors="coerce").astype("Int64")
    if "payload_sample" in frame.columns:
        lengths = frame["payload_sample"].fillna("").astype(str).str.len()
        return pd.to_numeric(lengths, errors="coerce").astype("Int64")
    if "tcp.payload" in frame.columns:
        lengths = frame["tcp.payload"].fillna("").apply(hex_length)
        return pd.to_numeric(lengths, errors="coerce").astype("Int64")
    if "mqtt.len" in frame.columns:
        numeric = pd.to_numeric(frame["mqtt.len"], errors="coerce")
        return numeric.astype("Int64")
    return pd.Series(pd.NA, index=frame.index, dtype="Int64")

def build_payload_sample(row: pd.Series) -> str:
    for column, treat_as_hex in PAYLOAD_PRIORITY:
        if column not in row:
            continue
        value = row[column]
        if pd.isna(value):
            continue
        text = str(value).strip()
        if not text:
            continue
        if treat_as_hex:
            decoded = decode_hex_payload(text)
        else:
            decoded = sanitize_text(text)
        if decoded:
            return decoded
    return ""

def map_packet_type(frame: pd.DataFrame) -> pd.Series:
    series = pick_series(frame, PACKET_TYPE_CANDIDATES)
    if series is None:
        return pd.Series(["UNKNOWN"] * len(frame), index=frame.index, dtype="object")
    raw = series.fillna("").astype(str).str.strip()
    numeric = pd.to_numeric(raw, errors="coerce")
    mapped = numeric.map(MQTT_MSGTYPE_MAP)
    fallback = raw.str.upper().replace("", "UNKNOWN")
    return mapped.fillna(fallback)

def canonicalize_chunk(
    chunk: pd.DataFrame,
    source_name: str,
    allowed_protocols: Set[str],
) -> pd.DataFrame:
    if chunk.empty:
        return pd.DataFrame(columns=CANONICAL_COLUMNS)

    chunk = chunk.copy()
    chunk.columns = [col.strip() for col in chunk.columns]

    ts_series = parse_timestamp(chunk)
    formatted_ts = format_timestamp(ts_series, len(chunk))

    src_ip = string_series(chunk, SRC_IP_CANDIDATES)
    dst_ip = string_series(chunk, DST_IP_CANDIDATES)
    src_port = string_series(chunk, SRC_PORT_CANDIDATES)
    dst_port = string_series(chunk, DST_PORT_CANDIDATES)

    client_id = string_series(chunk, CLIENT_ID_CANDIDATES)
    client_id = client_id.where(client_id != "", src_ip.where(src_ip != "", "unknown"))

    topic = string_series(chunk, TOPIC_CANDIDATES)
    topicfilter = string_series(chunk, TOPICFILTER_CANDIDATES)

    qos = numeric_series(chunk, QOS_CANDIDATES, default=0, allow_na=False)
    retain_flag = bool_flag_series(chunk, RETAIN_CANDIDATES)
    dup_flag = bool_flag_series(chunk, DUP_CANDIDATES)
    payload_length = compute_payload_length(chunk)

    payload_sample = chunk.apply(build_payload_sample, axis=1)
    packet_type = map_packet_type(chunk)
    protocol = determine_protocol(chunk)

    connack_code = string_series(chunk, CONNACK_CANDIDATES)
    label = string_series(chunk, LABEL_CANDIDATES, default="unknown")
    label = label.replace("", "unknown")
    username = string_series(chunk, USERNAME_CANDIDATES)
    msgid = numeric_series(chunk, MSGID_CANDIDATES, allow_na=True)
    auth_reason = string_series(chunk, AUTH_REASON_CANDIDATES)

    df = pd.DataFrame(
        {
            "timestamp": formatted_ts,
            "src_ip": src_ip,
            "src_port": src_port,
            "dst_ip": dst_ip,
            "dst_port": dst_port,
            "client_id": client_id,
            "topic": topic,
            "topicfilter": topicfilter,
            "qos": qos,
            "retain": retain_flag,
            "dupflag": dup_flag,
            "payload_length": payload_length,
            "Payload_sample": payload_sample,
            "packet_type": packet_type,
            "protocol": protocol,
            "connack_code": connack_code,
            "Label": label,
            "username": username,
            "msgid": msgid,
            "auth_reason": auth_reason,
        }
    )

    df = df[df["timestamp"] != ""]
    df = df[df["protocol"].isin(allowed_protocols)]

    return df[CANONICAL_COLUMNS]

def process_files(
    input_paths: Sequence[Path],
    output_path: Path,
    chunksize: int,
    allowed_protocols: Set[str],
) -> int:
    total_rows = 0
    header_written = False
    for path in input_paths:
        if not path.exists():
            print(f"[warn] Skipping missing file: {path}", file=sys.stderr)
            continue
        try:
            reader = pd.read_csv(path, chunksize=chunksize, low_memory=False)
        except Exception as exc:
            print(f"[error] Failed to read {path}: {exc}", file=sys.stderr)
            continue
        for chunk in reader:
            canonical = canonicalize_chunk(chunk, path.name, allowed_protocols)
            if canonical.empty:
                continue
            canonical.to_csv(
                output_path,
                mode="a",
                header=not header_written,
                index=False,
            )
            header_written = True
            total_rows += len(canonical)
        print(f"[info] Processed {path} -> {total_rows} rows cumulative", file=sys.stderr)
    return total_rows

def main() -> None:
    args = parse_args()
    allowed_protocols = {p.strip().upper() for p in args.protocols.split(",") if p.strip()}
    if not allowed_protocols:
        print("[error] No allowed protocols configured", file=sys.stderr)
        sys.exit(1)

    input_paths = collect_input_paths(args.inputs, args.pattern)
    if not input_paths:
        print("[error] No input CSV files found", file=sys.stderr)
        sys.exit(1)

    output_path = Path(args.output)
    if output_path.exists() and not args.force:
        print(
            f"[error] Output file {output_path} already exists. Use --force to overwrite.",
            file=sys.stderr,
        )
        sys.exit(1)
    if output_path.exists():
        output_path.unlink()

    try:
        total_rows = process_files(input_paths, output_path, args.chunksize, allowed_protocols)
    except KeyboardInterrupt:
        print("[warn] Interrupted by user", file=sys.stderr)
        sys.exit(130)

    if total_rows == 0:
        print("[warn] No rows written to output after filtering", file=sys.stderr)
    else:
        print(f"[done] Wrote {total_rows} rows to {output_path}")

if __name__ == "__main__":
    main()
