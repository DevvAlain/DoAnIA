
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
            # try parse JSON
            j = safe_json_load(x)
            if isinstance(j, dict):
                for k in ("value", "val", "temp", "temperature"):
                    if k in j:
                        return j[k]
                # otherwise first numeric
                for v in j.values():
                    if isinstance(v, (int, float)):
                        return v
                return None
            # if not JSON try numeric cast
            try:
                return float(x)
            except Exception:
                return None
        elif isinstance(x, dict):
            for k in ("value", "val"):
                if k in x: return x[k]
            for v in x.values():
                if isinstance(v, (int,float)): return v
            return None
        elif isinstance(x, (int, float, np.integer, np.floating)):
            return x
        else:
            return None
    except Exception:
        return None

def bool_to_int_flag(v):
    # Accept True/False, 'True'/'False', 'true'/'false', 1/0, '1'/'0'
    if pd.isna(v):
        return 0
    if isinstance(v, (int, float, np.integer, np.floating)):
        return 1 if int(v) != 0 else 0
    s = str(v).strip().lower()
    if s in ("true","t","yes","y","1"):
        return 1
    return 0

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

    # normalize clientid -> client_id
    if 'clientid' in df.columns and 'client_id' not in df.columns:
        df = df.rename(columns={'clientid': 'client_id'})

    # find timestamp-like column
    ts_candidates = [c for c in df.columns if 'time' in c.lower() or 'timestamp' in c.lower()]
    if not ts_candidates:
        print("No timestamp-like column found in", infile.name, file=sys.stderr)
        sys.exit(1)
    ts_col = ts_candidates[0]

    # parse timestamp to datetime (try seconds unix, else try auto)
    # first try as numeric epoch seconds
    df['_raw_ts'] = df[ts_col]
    ts_parsed = None
    try:
        # attempt numeric (seconds)
        df['ts'] = pd.to_datetime(df[ts_col].astype(float), unit='s', errors='raise')
    except Exception:
        # fallback auto parse with coercion
        df['ts'] = pd.to_datetime(df[ts_col], errors='coerce')
    # if still all NaT, set to now
    if df['ts'].isna().all():
        df['ts'] = pd.to_datetime('now')

    # ensure client_id exists, fallback to src_ip or synthetic
    if 'client_id' not in df.columns:
        if 'src_ip' in df.columns:
            df['client_id'] = df['src_ip'].astype(str)
        else:
            df['client_id'] = 'unknown'
    else:
        df['client_id'] = df['client_id'].fillna(df.get('src_ip', 'unknown')).astype(str)

    # extract numeric value from payload if exists, otherwise use 'value' column
    if 'payload' in df.columns:
        df['value_extracted'] = df['payload'].apply(extract_val)
    elif 'payload_sample' in df.columns:
        df['value_extracted'] = df['payload_sample'].apply(extract_val)
    elif 'value' in df.columns:
        df['value_extracted'] = df['value']
    else:
        df['value_extracted'] = None

    # payload_length
    if 'payload' in df.columns:
        df['payload_length'] = df['payload'].astype(str).str.len().fillna(0).astype(int)
    elif 'payload_sample' in df.columns:
        df['payload_length'] = df['payload_sample'].astype(str).str.len().fillna(0).astype(int)
    elif 'value' in df.columns:
        df['payload_length'] = df['value'].astype(str).str.len().fillna(0).astype(int)
    else:
        df['payload_length'] = 0

    # qos
    if 'qos' in df.columns:
        try:
            df['qos'] = df['qos'].fillna(0).astype(int)
        except Exception:
            # coerce safely
            df['qos'] = pd.to_numeric(df['qos'], errors='coerce').fillna(0).astype(int)
    else:
        df['qos'] = 0

    # retain flag
    if 'retain' in df.columns:
        df['retain_flag'] = df['retain'].apply(bool_to_int_flag).astype(int)
    else:
        df['retain_flag'] = 0

    # dup flag
    if 'dupflag' in df.columns:
        df['dup_flag'] = df['dupflag'].apply(bool_to_int_flag).astype(int)
    else:
        df['dup_flag'] = 0

    # msgid present
    if 'msgid' in df.columns:
        df['msgid_present'] = (~pd.isna(df['msgid'])).astype(int)
    else:
        df['msgid_present'] = 0

    # create epoch timestamp seconds column for replay convenience
    # convert ts (datetime64[ns]) to int seconds, fill NaT with 0
    df['timestamp'] = df['ts'].view('int64') // 10**9
    # if any NaT produced extreme negatives, coerce
    df.loc[df['timestamp'].isna(), 'timestamp'] = 0
    df['timestamp'] = df['timestamp'].astype(int)

    # compute inter-arrival time grouped by client_id or src_ip
    group_key = 'client_id' if 'client_id' in df.columns else ('src_ip' if 'src_ip' in df.columns else None)
    df = df.sort_values('ts')
    if group_key:
        df['prev_ts'] = df.groupby(group_key)['ts'].shift(1)
        df['iat_sec'] = (df['ts'] - df['prev_ts']).dt.total_seconds().fillna(0.0)
    else:
        df['iat_sec'] = 0.0

    # prepare output columns, keep Label if present
    out_cols = ['timestamp', 'ts', 'client_id', 'topic', 'value_extracted', 'payload_length',
                'qos', 'retain_flag', 'dup_flag', 'msgid_present', 'iat_sec']
    existing = [c for c in out_cols if c in df.columns]
    if 'Label' in df.columns:
        existing.append('Label')

    outdf = df[existing].copy()
    # rename to consistent 'value' column
    if 'value_extracted' in outdf.columns:
        outdf = outdf.rename(columns={'value_extracted': 'value'})

    # create output filename: if input stem starts with 'processed_' remove it
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
