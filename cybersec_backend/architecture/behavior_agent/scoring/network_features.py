"""
Maps Team 1 network_connection events → 34-feature vector
matching EXACTLY the column order your scaler was trained on.

UNSW-NB15 columns (in order):
['dur', 'proto', 'service', 'state', 'spkts', 'dpkts', 'sbytes', 'dbytes',
 'rate', 'sload', 'dload', 'sloss', 'dloss', 'sinpkt', 'dinpkt', 'sjit',
 'djit', 'swin', 'stcpb', 'dtcpb', 'dwin', 'tcprtt', 'synack', 'ackdat',
 'smean', 'dmean', 'trans_depth', 'response_body_len', 'ct_src_dport_ltm',
 'ct_dst_sport_ltm', 'is_ftp_login', 'ct_ftp_cmd', 'ct_flw_http_mthd',
 'is_sm_ips_ports']
"""

import numpy as np
from datetime import datetime


# ── Protocol encoding (matches LabelEncoder fitted on UNSW-NB15) ─────────────
# UNSW-NB15 proto column was label-encoded alphabetically.
# Most common values and their approximate encoded indices:
PROTO_MAP = {
    "tcp":  6,
    "udp":  17,
    "icmp": 1,
    "TCP":  6,
    "UDP":  17,
    "ICMP": 1,
}

# ── Service port → service index mapping ─────────────────────────────────────
# UNSW-NB15 service column: '-', 'dns', 'ftp', 'http', 'smtp', 'ssh', etc.
# Label-encoded alphabetically. We approximate from dst_port.
SERVICE_MAP = {
    21:   2,   # ftp
    22:   8,   # ssh
    25:   9,   # smtp
    53:   1,   # dns
    80:   3,   # http
    443:  3,   # http (https approximated)
    123:  0,   # ntp → '-' (no specific service)
    161:  0,   # snmp → '-'
    389:  0,   # ldap → '-'
    1433: 0,   # mssql → '-'
    1900: 0,   # ssdp → '-'
    137:  0,   # netbios → '-'
    111:  0,   # portmap → '-'
    69:   0,   # tftp → '-'
}

# ── State encoding ─────────────────────────────────────────────────────────────
# UNSW-NB15 state: CON, FIN, INT, REQ, RST, etc. — label-encoded.
# We approximate: TCP=FIN(1), UDP=CON(0), unknown=INT(2)
STATE_MAP = {
    "TCP": 1,
    "UDP": 0,
    "tcp": 1,
    "udp": 0,
}


def extract(events: list) -> np.ndarray:
    """
    Input:  list of Team 1 network_connection event dicts (min 1)
    Output: np.array shape (34,) — ready for scaler.transform()

    Column order matches UNSW-NB15 training exactly.
    Fields not available from Team 1 are set to 0.
    """
    if not events:
        return np.zeros(34, dtype=np.float32)

    # ── Aggregate across all events in the window ─────────────────
    meta_list  = [e.get("metadata", {}) for e in events]
    timestamps = []
    for e in events:
        try:
            timestamps.append(datetime.fromisoformat(e["timestamp"]))
        except Exception:
            pass

    # Core byte counts
    sbytes_list = [float(m.get("bytes_sent", 0) or 0) for m in meta_list]
    dbytes_list = [float(m.get("bytes_received", 0) or 0) for m in meta_list]

    sbytes_total = sum(sbytes_list)
    dbytes_total = sum(dbytes_list)

    # Duration from first to last timestamp
    if len(timestamps) >= 2:
        dur = (timestamps[-1] - timestamps[0]).total_seconds()
    else:
        dur = 0.0

    # Protocol from first event
    raw_proto = meta_list[0].get("protocol", "tcp")
    proto     = PROTO_MAP.get(str(raw_proto), 6)

    # Service from dst_port of first event
    dst_port  = int(meta_list[0].get("dst_port", 0) or 0)
    src_port  = int(meta_list[0].get("src_port", 0) or 0)
    service   = SERVICE_MAP.get(dst_port, 0)

    # State
    state = STATE_MAP.get(str(raw_proto), 2)

    # Packet counts — not available, estimate 1 per event
    spkts = float(len(events))       # source packets (fwd)
    dpkts = float(len(events))       # dest packets (bwd) — symmetric estimate

    # Rate = total packets / duration
    rate = (spkts + dpkts) / dur if dur > 0 else 0.0

    # Load = bits per second
    sload = (sbytes_total * 8) / dur if dur > 0 else 0.0
    dload = (dbytes_total * 8) / dur if dur > 0 else 0.0

    # Loss — not available
    sloss = 0.0
    dloss = 0.0

    # Inter-packet time
    sinpkt = dur / spkts if spkts > 0 else 0.0
    dinpkt = dur / dpkts if dpkts > 0 else 0.0

    # Jitter — not available
    sjit = float(np.std(sbytes_list)) if len(sbytes_list) > 1 else 0.0
    djit = float(np.std(dbytes_list)) if len(dbytes_list) > 1 else 0.0

    # TCP window sizes — not available
    swin  = 0.0
    dwin  = 0.0

    # TCP base sequence numbers — not available
    stcpb = 0.0
    dtcpb = 0.0

    # TCP round trip times — not available
    tcprtt = 0.0
    synack = 0.0
    ackdat = 0.0

    # Mean packet sizes
    smean = sbytes_total / spkts if spkts > 0 else 0.0
    dmean = dbytes_total / dpkts if dpkts > 0 else 0.0

    # HTTP depth / response body — not available
    trans_depth       = 0.0
    response_body_len = 0.0

    # Connection counts — approximate from window size
    ct_src_dport_ltm  = float(len(set(m.get("dst_port", 0) or 0 for m in meta_list)))
    ct_dst_sport_ltm  = float(len(set(m.get("src_port", 0) or 0 for m in meta_list)))

    # FTP — not available
    is_ftp_login    = 1.0 if dst_port == 21 else 0.0
    ct_ftp_cmd      = 0.0

    # HTTP methods — not available
    ct_flw_http_mthd = 0.0

    # Same IP/port pairs
    src_ips  = [m.get("src_ip", "") for m in meta_list]
    dst_ips  = [m.get("dst_ip", "") for m in meta_list]
    is_sm_ips_ports = 1.0 if (
        len(set(src_ips)) == 1 and
        len(set(dst_ips)) == 1 and
        len(set(m.get("dst_port", 0) for m in meta_list)) == 1
    ) else 0.0

    # ── Assemble in EXACT column order ───────────────────────────
    features = np.array([
        dur,               # 0  dur
        proto,             # 1  proto
        service,           # 2  service
        state,             # 3  state
        spkts,             # 4  spkts
        dpkts,             # 5  dpkts
        sbytes_total,      # 6  sbytes
        dbytes_total,      # 7  dbytes
        rate,              # 8  rate
        sload,             # 9  sload
        dload,             # 10 dload
        sloss,             # 11 sloss
        dloss,             # 12 dloss
        sinpkt,            # 13 sinpkt
        dinpkt,            # 14 dinpkt
        sjit,              # 15 sjit
        djit,              # 16 djit
        swin,              # 17 swin
        stcpb,             # 18 stcpb
        dtcpb,             # 19 dtcpb
        dwin,              # 20 dwin
        tcprtt,            # 21 tcprtt
        synack,            # 22 synack
        ackdat,            # 23 ackdat
        smean,             # 24 smean
        dmean,             # 25 dmean
        trans_depth,       # 26 trans_depth
        response_body_len, # 27 response_body_len
        ct_src_dport_ltm,  # 28 ct_src_dport_ltm
        ct_dst_sport_ltm,  # 29 ct_dst_sport_ltm
        is_ftp_login,      # 30 is_ftp_login
        ct_ftp_cmd,        # 31 ct_ftp_cmd
        ct_flw_http_mthd,  # 32 ct_flw_http_mthd
        is_sm_ips_ports,   # 33 is_sm_ips_ports
    ], dtype=np.float32)

    return features