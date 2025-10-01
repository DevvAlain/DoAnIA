import argparse
from pathlib import Path
import json
import pandas as pd
import numpy as np
import sys

def parse_args():
    p = argparse.ArgumentParser(description="Extract features from processed MQTT CSV")
    p.add_argument("infile", help="Input CSV (processed_*.csv or similar)")
    p.add_argument("--out", default=None, help="Output CSV (defaults to features_<device>.csv)")
    return p.parse_args()

def safe_json_load(s):
    try:
        return json.loads(s)
    except Exception:
        return None

def extract_val(x):
    try:
        if pd.isna(x):
            return None
        if isinstance(x, str):
            j = safe_json_load(x)
            if isinstance(j, dict):
                for k in ("value", "val", "temp", "temperature"):
                    if k in j:
                        return j[k]
                for v in j.values():
                    if isinstance(v, (int, float)):
                        return v
                return None
            try:
                return float(x)
            except Exception:
                return None
        elif isinstance(x, dict):
            for k in ("value", "val"):
                if k in x:
                    return x[k]
            for v in x.values():
                if isinstance(v, (int, float)):
                    return v
            return None
        elif isinstance(x, (int, float, np.integer, np.floating)):
            return x
        else:
            return None
    except Exception:
        return None

def bool_to_int_flag(v):
    if pd.isna(v):
        return 0
    if isinstance(v, (int, float, np.integer, np.floating)):
        return 1 if int(v) != 0 else 0
    s = str(v).strip().lower()
    if s in ("true", "t", "yes", "y", "1"):
        return 1
    return 0

def resolve_column(df, *candidates):
    lower_map = {col.lower(): col for col in df.columns}
    for cand in candidates:
        if cand in df.columns:
            return cand
        actual = lower_map.get(cand.lower())
        if actual:
            return actual
    return None

def main():
    args = parse_args()
    infile = Path(args.infile)
    if not infile.exists():
        print("Input file not found:", infile, file=sys.stderr)
        sys.exit(1)

    try:
        df = pd.read_csv(infile)
    except Exception as e:
        print("Error reading CSV:", e, file=sys.stderr)
        sys.exit(1)

    clientid_col = resolve_column(df, "clientid")
    if clientid_col and clientid_col != "client_id" and "client_id" not in df.columns:
        df = df.rename(columns={clientid_col: "client_id"})

    ts_col = resolve_column(df, "timestamp", "ts", "time")
    if not ts_col:
        print("No timestamp-like column found in", infile.name, file=sys.stderr)
        sys.exit(1)

    df['_raw_ts'] = df[ts_col]
    try:
        df['ts'] = pd.to_datetime(df[ts_col].astype(float), unit='s', errors='raise')
    except Exception:
        df['ts'] = pd.to_datetime(df[ts_col], errors='coerce')
    if df['ts'].isna().all():
        df['ts'] = pd.to_datetime('now')

    src_ip_col = resolve_column(df, "src_ip", "ip.src")
    if 'client_id' not in df.columns:
        if src_ip_col:
            df['client_id'] = df[src_ip_col].astype(str)
        else:
            df['client_id'] = 'unknown'
    else:
        if src_ip_col:
            df['client_id'] = df['client_id'].fillna(df[src_ip_col]).astype(str)
        else:
            df['client_id'] = df['client_id'].fillna('unknown').astype(str)

    payload_col = resolve_column(df, "payload")
    payload_sample_col = resolve_column(df, "payload_sample", "Payload_sample")
    value_col = resolve_column(df, "value")
    if payload_col:
        df['value_extracted'] = df[payload_col].apply(extract_val)
    elif payload_sample_col:
        df['value_extracted'] = df[payload_sample_col].apply(extract_val)
    elif value_col:
        df['value_extracted'] = df[value_col]
    else:
        df['value_extracted'] = None

    payload_length_col = resolve_column(df, "payload_length")
    if payload_col:
        df['payload_length'] = df[payload_col].astype(str).str.len().fillna(0).astype(int)
    elif payload_sample_col:
        df['payload_length'] = df[payload_sample_col].astype(str).str.len().fillna(0).astype(int)
    elif value_col:
        df['payload_length'] = df[value_col].astype(str).str.len().fillna(0).astype(int)
    elif payload_length_col:
        df['payload_length'] = pd.to_numeric(df[payload_length_col], errors='coerce').fillna(0).astype(int)
    else:
        df['payload_length'] = 0

    if 'qos' in df.columns:
        try:
            df['qos'] = df['qos'].fillna(0).astype(int)
        except Exception:
            df['qos'] = pd.to_numeric(df['qos'], errors='coerce').fillna(0).astype(int)
    else:
        qos_col = resolve_column(df, 'qos')
        if qos_col:
            df['qos'] = pd.to_numeric(df[qos_col], errors='coerce').fillna(0).astype(int)
        else:
            df['qos'] = 0

    retain_col = resolve_column(df, 'retain', 'retain_flag')
    if retain_col:
        df['retain_flag'] = df[retain_col].apply(bool_to_int_flag).astype(int)
    else:
        df['retain_flag'] = 0

    dup_col = resolve_column(df, 'dupflag', 'dup_flag')
    if dup_col:
        df['dup_flag'] = df[dup_col].apply(bool_to_int_flag).astype(int)
    else:
        df['dup_flag'] = 0

    msgid_col = resolve_column(df, 'msgid')
    if msgid_col:
        df['msgid_present'] = (~pd.isna(df[msgid_col])).astype(int)
    else:
        df['msgid_present'] = 0

    df['timestamp'] = df['ts'].astype('int64') // 10**9
    df.loc[df['timestamp'].isna(), 'timestamp'] = 0
    df['timestamp'] = df['timestamp'].astype(int)

    group_key = 'client_id' if 'client_id' in df.columns else (src_ip_col if src_ip_col else None)
    df = df.sort_values('ts')
    if group_key:
        df['prev_ts'] = df.groupby(group_key)['ts'].shift(1)
        df['iat_sec'] = (df['ts'] - df['prev_ts']).dt.total_seconds().fillna(0.0)
    else:
        df['iat_sec'] = 0.0

    out_cols = ['timestamp', 'ts', 'client_id', 'topic', 'value_extracted', 'payload_length',
                'qos', 'retain_flag', 'dup_flag', 'msgid_present', 'iat_sec']
    topic_col = resolve_column(df, 'topic')
    if topic_col and topic_col != 'topic':
        df = df.rename(columns={topic_col: 'topic'})
    existing = [c for c in out_cols if c in df.columns]
    if 'Label' in df.columns:
        existing.append('Label')

    outdf = df[existing].copy()
    if 'value_extracted' in outdf.columns:
        outdf = outdf.rename(columns={'value_extracted': 'value'})

    stem = infile.stem
    if stem.startswith("processed_"):
        stem = stem[len("processed_"):]
    outfn = Path(args.out) if args.out else (infile.parent / f"features_{stem}.csv")

    try:
        outdf.to_csv(outfn, index=False)
        print("Wrote", outfn, "rows:", len(outdf))
    except Exception as e:
        print("Error writing output:", e, file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
