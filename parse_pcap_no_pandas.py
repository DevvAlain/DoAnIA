#!/usr/bin/env python3
# parse_pcap_no_pandas.py - parser nhẹ, không cần pandas
import csv, binascii, re, argparse, os, sys

def extract_from_hex_field(h):
    if h is None or h == "":
        return None
    # normalize: remove spaces, colons, 0x
    s = re.sub(r'[^0-9A-Fa-f]', '', str(h))
    if len(s) % 2 != 0:
        # drop last nibble if odd length
        s = s[:-1]
    if not s:
        return None
    try:
        b = binascii.unhexlify(s)
    except Exception:
        return None
    txt = ''.join([chr(c) if 32 <= c < 127 else '.' for c in b])
    # try find numeric (float/int)
    m = re.search(r'([-+]?\d+\.\d+|[-+]?\d+)', txt)
    if m:
        return m.group(0)
    # fallback: last printable chunk
    chunks = re.findall(r'[ -~]{2,}', txt)
    return chunks[-1] if chunks else None

def find_col(names, candidates):
    for c in candidates:
        if c in names:
            return c
    return None

def process(infile, outdir):
    os.makedirs(outdir, exist_ok=True)
    with open(infile, newline='', errors='ignore') as f:
        reader = csv.DictReader(f)
        headers = reader.fieldnames or []
        topic_col = find_col(headers, ['mqtt.topic','topic','_topic','mqtt_topic'])
        payload_cols = [c for c in headers if c.lower().find('payload')!=-1] or ['tcp.payload','mqtt.payload','data','payload']
        time_col = find_col(headers, ['frame.time_epoch','time','timestamp','frame.time'])
        client_col = find_col(headers, ['mqtt.clientid','clientid','client.id','client'])
        src_col = find_col(headers, ['ip.src','src','ip_source','ip.src_host'])
        qos_col = find_col(headers, ['mqtt.qos','qos'])
        retain_col = find_col(headers, ['mqtt.retain','retain'])

        if not topic_col:
            print("ERR: không tìm thấy cột topic trong CSV. Các cột có: ", headers)
            return

        groups = {}
        for row in reader:
            topic = row.get(topic_col) or "UNKNOWN"
            # find first non-empty payload column
            payload_raw = None
            for pc in payload_cols:
                if pc in row and row.get(pc):
                    payload_raw = row.get(pc)
                    break
            value = extract_from_hex_field(payload_raw)
            rec = {
                'timestamp': row.get(time_col) if time_col else "",
                'topic': topic,
                'value': value,
                'clientid': row.get(client_col) if client_col else "",
                'src_ip': row.get(src_col) if src_col else "",
                'qos': row.get(qos_col) if qos_col else "",
                'retain': row.get(retain_col) if retain_col else "",
            }
            groups.setdefault(topic, []).append(rec)

    # write per-topic files
    for topic, recs in groups.items():
        safe = topic.replace('/','_').replace(' ','_')
        outfn = os.path.join(outdir, f"processed_{safe}.csv")
        with open(outfn, 'w', newline='', encoding='utf-8') as fo:
            w = csv.DictWriter(fo, fieldnames=['timestamp','topic','value','clientid','src_ip','qos','retain'])
            w.writeheader()
            for r in recs:
                w.writerow(r)
        print("Wrote", outfn, "rows:", len(recs))

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("infile")
    p.add_argument("--outdir", default="./datasets")
    args = p.parse_args()
    if not os.path.exists(args.infile):
        print("File not found:", args.infile)
        sys.exit(1)
    process(args.infile, args.outdir)
