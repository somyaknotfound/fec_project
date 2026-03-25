#!/usr/bin/env python3
"""
DEMO 4: Controlled Packet Loss + Live FEC Recovery
====================================================
★ THE BEST DEMO FOR PRESENTATIONS ★

Shows EXACTLY which data packets are lost and PROVES FEC recovers them.

KEY: The sender SKIPS sending the "lost" packets entirely, so
     Wireshark shows FEWER packets — proving the loss is REAL.

Flow:
  1. Sender encodes 4 data packets → 8 total (4 data + 4 parity)
  2. Sender SKIPS packets #1 and #3 (simulates network loss)
  3. Wireshark shows only 6 of 8 packets — VISIBLE GAP in sequence!
  4. Receiver detects missing packets, runs FEC recovery
  5. FEC decoder recovers the 2 "lost" data packets using parity
  6. Recovered data is printed to PROVE it matches the originals

Wireshark Setup:
  1. Open Wireshark → Select "Loopback: lo" interface
  2. Filter: udp.port == 5003
  3. Start capture, then run this script
  4. You'll see only 6 UDP packets (NOT 8!) — 2 were "lost in transit"
  5. Terminal shows: FEC recovered them from the remaining 6!

Port: 5003
Duration: ~8 seconds

Run:  python3 demo4_controlled_recovery.py
"""

import socket
import struct
import time
import threading
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from core.fec_encoder import FECEncoder
from core.fec_decoder import FECDecoder

# ── Terminal colors ──────────────────────────────────────────────
GREEN   = '\033[92m'
RED     = '\033[91m'
YELLOW  = '\033[93m'
CYAN    = '\033[96m'
BLUE    = '\033[94m'
MAGENTA = '\033[95m'
BOLD    = '\033[1m'
DIM     = '\033[2m'
RESET   = '\033[0m'
BG_RED  = '\033[41m'
BG_GREEN= '\033[42m'

# ── Configuration ───────────────────────────────────────────────
HOST = "127.0.0.1"
PORT = 5003
N_DATA = 4
N_PARITY = 4

# ★★★ CHANGE THESE to demo different loss scenarios ★★★
# Indices 0-3 = data packets, indices 4-7 = parity packets
# These packets will NOT be sent — simulating network loss
LOST_PACKET_INDICES = [1, 3]   # Lose DATA_1 and DATA_3

# The 4 original messages (readable text so recovery is visually proven)
ORIGINAL_MESSAGES = [
    "HELLO 5G WORLD - This is data packet ZERO",
    "FEC PROTECTION - This is data packet ONE",
    "ERASURE CODING - This is data packet TWO",
    "GF256 RECOVERY - This is data packet THREE",
]


def print_header():
    print(f"\n{BOLD}{YELLOW}╔═══════════════════════════════════════════════════════════════╗{RESET}")
    print(f"{BOLD}{YELLOW}║  ★ DEMO 4: Controlled Packet Loss + Live FEC Recovery ★      ║{RESET}")
    print(f"{BOLD}{YELLOW}║  Port: 5003  │  4 Data + 4 Parity  │  Dropping: {str(LOST_PACKET_INDICES):14s}║{RESET}")
    print(f"{BOLD}{YELLOW}╚═══════════════════════════════════════════════════════════════╝{RESET}")
    print()
    print(f"  {CYAN}➜ Open Wireshark → filter: {BOLD}udp.port == 5003{RESET}")
    print(f"  {CYAN}➜ Start capture, then press Enter here{RESET}")
    print()
    lost_data = [i for i in LOST_PACKET_INDICES if i < N_DATA]
    if lost_data:
        print(f"  {RED}⚠  Packets {LOST_PACKET_INDICES} will be LOST in transit (not sent at all){RESET}")
        print(f"  {RED}   Wireshark will show only {8 - len(LOST_PACKET_INDICES)} of 8 packets!{RESET}")
    print(f"  {GREEN}✓  FEC will recover the missing data from parity — watch!{RESET}")
    print()


# ── RECEIVER THREAD ─────────────────────────────────────────────

def receiver_thread(results):
    """Receive whatever packets arrive and attempt FEC decoding."""

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind((HOST, PORT))
    sock.settimeout(15)

    total_in_block = N_DATA + N_PARITY  # 8
    received_packets = [None] * total_in_block
    received_count = 0
    expected_to_receive = total_in_block - len(LOST_PACKET_INDICES)

    print(f"\n  {BOLD}┌─────────────────────────────────────────────────────┐{RESET}")
    print(f"  {BOLD}│  PHASE 1: RECEIVING PACKETS (waiting for arrivals)  │{RESET}")
    print(f"  {BOLD}└─────────────────────────────────────────────────────┘{RESET}\n")

    # We only expect to receive (8 - lost) packets
    while received_count < expected_to_receive:
        try:
            data, addr = sock.recvfrom(4096)

            # Parse FEC header
            header = data[:8]
            payload = data[8:]
            block_id, pkt_idx, total = struct.unpack('!IHH', header)

            is_data = pkt_idx < N_DATA
            pkt_label = f"DATA_{pkt_idx}" if is_data else f"PARITY_{pkt_idx - N_DATA}"

            received_count += 1
            received_packets[pkt_idx] = payload
            type_color = GREEN if is_data else BLUE

            preview = ""
            if is_data:
                preview = payload[:42].decode('ascii', errors='replace').strip('\x00')
                preview = f'{DIM}  "{preview}"{RESET}'
            else:
                preview = f"{DIM}  [GF(256) parity bytes]{RESET}"

            print(f"  {type_color}{BOLD} ✓ RCVD {RESET}  [{pkt_label:10s}]  idx={pkt_idx}"
                  f"{preview}")

        except socket.timeout:
            break

    sock.close()

    # ── Phase 2: Show what's missing ──
    print(f"\n  {BOLD}┌─────────────────────────────────────────────────────┐{RESET}")
    print(f"  {BOLD}│  PHASE 2: PACKET STATUS — WHAT ARRIVED?             │{RESET}")
    print(f"  {BOLD}└─────────────────────────────────────────────────────┘{RESET}\n")

    missing_indices = [i for i in range(total_in_block) if received_packets[i] is None]
    missing_data = [i for i in missing_indices if i < N_DATA]

    print(f"  Encoded total:   {BOLD}8{RESET} packets (4 data + 4 parity)")
    print(f"  Received:        {GREEN}{BOLD}{received_count}{RESET} packets")
    print(f"  {RED}Lost in transit:   {BOLD}{len(missing_indices)}{RESET}{RED} packets (indices {missing_indices}){RESET}")
    if missing_data:
        print(f"  {RED}Lost DATA packets: {BOLD}{missing_data}{RESET}{RED}  ← these had real user data!{RESET}")
    print()

    # Show what the lost data contained
    for idx in missing_data:
        print(f"  {BG_RED}{BOLD} LOST {RESET}  DATA_{idx} contained: "
              f"{RED}\"{ORIGINAL_MESSAGES[idx]}\"{RESET}")
    print()

    # Visual packet map
    print(f"  ┌──────────────────────────────┬──────────────────────────────┐")
    print(f"  │     DATA PACKETS (0-3)       │    PARITY PACKETS (4-7)      │")
    print(f"  ├──────────────────────────────┼──────────────────────────────┤")
    data_visual = "  │  "
    for i in range(N_DATA):
        if received_packets[i] is not None:
            data_visual += f"{GREEN}[D{i} ✓]{RESET} "
        else:
            data_visual += f"{RED}[D{i} ✗]{RESET} "
    data_visual += "         │  "
    for i in range(N_DATA, N_DATA + N_PARITY):
        if received_packets[i] is not None:
            data_visual += f"{BLUE}[P{i-N_DATA} ✓]{RESET} "
        else:
            data_visual += f"{RED}[P{i-N_DATA} ✗]{RESET} "
    data_visual += "        │"
    print(data_visual)
    print(f"  └──────────────────────────────┴──────────────────────────────┘")
    print()

    # ── Phase 3: FEC Recovery ──
    print(f"  {BOLD}{MAGENTA}┌─────────────────────────────────────────────────────┐{RESET}")
    print(f"  {BOLD}{MAGENTA}│  PHASE 3: FEC RECOVERY                              │{RESET}")
    print(f"  {BOLD}{MAGENTA}│  Algorithm: Gauss-Jordan Elimination over GF(2⁸)    │{RESET}")
    print(f"  {BOLD}{MAGENTA}└─────────────────────────────────────────────────────┘{RESET}\n")

    decoder = FECDecoder(n_data_packets=N_DATA, n_parity_packets=N_PARITY)

    if received_count < N_DATA:
        print(f"  {RED}✗ UNRECOVERABLE: Need ≥ {N_DATA} packets, only got {received_count}{RESET}")
        results['success'] = False
        return

    available = [i for i in range(total_in_block) if received_packets[i] is not None]

    print(f"  {CYAN}Condition check:{RESET}  received ({received_count}) ≥ needed ({N_DATA})  →  "
          f"{GREEN}✓ Recovery possible{RESET}")
    print()
    print(f"  {DIM}  Step 1: Identify missing data packets: {missing_data}{RESET}")
    time.sleep(0.5)
    print(f"  {DIM}  Step 2: Select {N_DATA} received packets: indices {available[:N_DATA]}{RESET}")
    time.sleep(0.5)
    print(f"  {DIM}  Step 3: Build sub-matrix from encoding matrix rows {available[:N_DATA]}{RESET}")
    time.sleep(0.5)
    print(f"  {DIM}  Step 4: Invert sub-matrix via Gauss-Jordan over GF(256){RESET}")
    time.sleep(0.5)
    print(f"  {DIM}  Step 5: Multiply S⁻¹ × received_bytes → original data{RESET}")
    time.sleep(1)
    print()

    recovered, success = decoder.decode_block(received_packets)

    if success:
        print(f"  {GREEN}{BOLD}╔═══════════════════════════════════════════════════╗{RESET}")
        print(f"  {GREEN}{BOLD}║       ★ ★ ★  FEC RECOVERY SUCCESSFUL  ★ ★ ★      ║{RESET}")
        print(f"  {GREEN}{BOLD}╚═══════════════════════════════════════════════════╝{RESET}")
        print()

        # Show all 4 recovered data packets
        for i in range(N_DATA):
            text = recovered[i][:44].decode('ascii', errors='replace').strip('\x00')
            was_lost = i in LOST_PACKET_INDICES

            if was_lost:
                print(f"  {BG_GREEN}{BOLD} RECOVERED {RESET}  DATA_{i}: \"{GREEN}{text}{RESET}\"")
            else:
                print(f"  {DIM} received  {RESET}  {DIM}DATA_{i}: \"{text}\"{RESET}")

        print()

        # Verify byte-for-byte
        print(f"  {BOLD}Byte-for-byte verification:{RESET}")
        all_correct = True
        for i in range(N_DATA):
            original = ORIGINAL_MESSAGES[i].encode()
            recovered_text = recovered[i][:len(original)]
            match = (recovered_text == original)
            if not match:
                all_correct = False

            if i in LOST_PACKET_INDICES:
                status = f"{GREEN}✓ EXACT MATCH{RESET}" if match else f"{RED}✗ MISMATCH{RESET}"
                print(f"    DATA_{i}: {status}  ← was lost, recovered via GF(256)")
            else:
                print(f"    {DIM}DATA_{i}: ✓ (was never lost){RESET}")

        if all_correct:
            print(f"\n  {GREEN}{BOLD}  ✓ ALL DATA VERIFIED — 100% accurate recovery!{RESET}")
            print(f"  {GREEN}{BOLD}  ✓ Zero retransmissions needed — 5G URLLC ready!{RESET}")

        results['success'] = True
    else:
        print(f"\n  {RED}{BOLD}  ✗ DECODE FAILED — too many losses for this code rate{RESET}")
        results['success'] = False

    results['stats'] = decoder.get_statistics()
    results['received_count'] = received_count
    results['missing'] = missing_indices


# ── SENDER THREAD ───────────────────────────────────────────────

def sender_thread():
    """Encode all 8 FEC packets but SKIP the 'lost' ones — simulating network loss."""
    time.sleep(0.3)  # Let receiver bind first

    encoder = FECEncoder(n_data_packets=N_DATA, n_parity_packets=N_PARITY)
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    dest = (HOST, PORT)

    # Create data packets with clear readable text
    data_packets = []
    for msg in ORIGINAL_MESSAGES:
        payload = msg.encode()
        payload += b'\x00' * (1024 - len(payload))
        data_packets.append(payload)

    # FEC encode: 4 data → 8 total
    encoded = encoder.encode_block(data_packets)

    sent_count = 0
    skipped_count = 0

    print(f"\n  {BOLD}┌─────────────────────────────────────────────────────┐{RESET}")
    print(f"  {BOLD}│  SENDER: Encoded {len(encoded)} packets (4 data + 4 parity)        │{RESET}")
    print(f"  {BOLD}│  Simulating network loss on indices {str(LOST_PACKET_INDICES):15s}   │{RESET}")
    print(f"  {BOLD}└─────────────────────────────────────────────────────┘{RESET}\n")

    for idx, pkt_data in enumerate(encoded):
        is_data = idx < N_DATA
        pkt_label = f"DATA_{idx}" if is_data else f"PARITY_{idx - N_DATA}"
        type_color = GREEN if is_data else BLUE

        # ★ SKIP sending "lost" packets — they never reach the network! ★
        if idx in LOST_PACKET_INDICES:
            skipped_count += 1
            data_text = ""
            if is_data:
                data_text = f'  {DIM}"{ORIGINAL_MESSAGES[idx]}"{RESET}'
            print(f"  {BG_RED}{BOLD} ✗ LOST {RESET}  [{pkt_label:10s}]  idx={idx}  "
                  f"{RED}── dropped by network! ──{RESET}{data_text}")
            time.sleep(0.6)
            continue  # DON'T SEND — simulates packet loss in the channel

        # Send normally
        header = struct.pack('!IHH', 0, idx, len(encoded))
        full_packet = header + pkt_data

        print(f"  {type_color} → SENT {RESET}  [{pkt_label:10s}]  idx={idx}  "
              f"{DIM}{len(full_packet)} bytes{RESET}")

        sock.sendto(full_packet, dest)
        sent_count += 1
        time.sleep(0.6)

    sock.close()

    print(f"\n  {DIM}  Sender done: {sent_count} sent, "
          f"{skipped_count} lost in network channel{RESET}")


# ── MAIN ────────────────────────────────────────────────────────

def run_demo():
    print_header()
    input(f"  {YELLOW}Press Enter to start the demo...{RESET}")

    results = {}

    # Start receiver thread (binds to port first)
    recv = threading.Thread(target=receiver_thread, args=(results,), daemon=True)
    recv.start()
    time.sleep(0.5)

    # Send packets from main thread
    sender_thread()

    # Wait for receiver to finish decoding
    time.sleep(2)
    recv.join(timeout=10)

    # ── Final Summary ───────────────────────────────────────────
    received = results.get('received_count', 0)
    missing = results.get('missing', LOST_PACKET_INDICES)

    print(f"\n{BOLD}{YELLOW}╔═══════════════════════════════════════════════════════════════╗{RESET}")
    print(f"{BOLD}{YELLOW}║                      FINAL SUMMARY                            ║{RESET}")
    print(f"{BOLD}{YELLOW}╚═══════════════════════════════════════════════════════════════╝{RESET}")
    print()
    print(f"  Encoded:             {BOLD}8{RESET} packets (4 data + 4 parity)")
    print(f"  Actually sent:       {BOLD}{8 - len(LOST_PACKET_INDICES)}{RESET} packets")
    print(f"  Lost in channel:     {RED}{BOLD}{len(LOST_PACKET_INDICES)}{RESET}  (indices {LOST_PACKET_INDICES})")

    lost_data = [i for i in LOST_PACKET_INDICES if i < N_DATA]
    if lost_data:
        print(f"  Lost DATA packets:   {RED}{BOLD}{lost_data}{RESET}  ← user data was in these!")

    if results.get('success'):
        print(f"  FEC recovery:        {GREEN}{BOLD}★ 100% SUCCESS ★{RESET}")
        print(f"  Method:              Gauss-Jordan elimination over GF(2⁸)")
        print()
        print(f"  {GREEN}{BOLD}  ┌──────────────────────────────────────────────────┐{RESET}")
        print(f"  {GREEN}{BOLD}  │  CONCLUSION: {len(LOST_PACKET_INDICES)} packets lost → ALL data recovered    │{RESET}")
        print(f"  {GREEN}{BOLD}  │  No retransmissions. No delay. 5G URLLC ready.   │{RESET}")
        print(f"  {GREEN}{BOLD}  └──────────────────────────────────────────────────┘{RESET}")
    else:
        print(f"  FEC recovery:        {RED}{BOLD}FAILED{RESET}")
        print(f"  {YELLOW}  Too many losses (>{N_PARITY}) for this code rate.{RESET}")

    print(f"\n  {CYAN}🔍 Wireshark verification:{RESET}")
    print(f"     Filter: {BOLD}udp.port == 5003{RESET}")
    print(f"     • Wireshark shows only {GREEN}{BOLD}{8 - len(LOST_PACKET_INDICES)} packets{RESET} — NOT 8!")
    print(f"     • Packets with index {RED}{LOST_PACKET_INDICES}{RESET} are {RED}MISSING from capture{RESET}")
    print(f"     • Check the hex: indices jump from 0→2 (skipping 1) and 2→4 (skipping 3)")
    print(f"     • This proves the packets were {RED}genuinely lost{RESET} (never on the wire)")
    print(f"     • Yet FEC {GREEN}recovered all original data{RESET} from the {8 - len(LOST_PACKET_INDICES)} survivors!")
    print(f"\n{YELLOW}{'═' * 65}{RESET}")

    # Try different scenarios
    print(f"\n  {DIM}┌──────────────────────────────────────────────────────────┐{RESET}")
    print(f"  {DIM}│  TIP: Edit LOST_PACKET_INDICES to try other scenarios:   │{RESET}")
    print(f"  {DIM}│                                                          │{RESET}")
    print(f"  {DIM}│  [1, 3]          → Lose 2 data packets (default)         │{RESET}")
    print(f"  {DIM}│  [0, 1, 2]       → Lose 3 data packets (recoverable!)   │{RESET}")
    print(f"  {DIM}│  [0, 1, 2, 3]    → Lose ALL 4 data (STILL recoverable!) │{RESET}")
    print(f"  {DIM}│  [0, 1, 2, 3, 4] → Lose 5 packets → FAILS (max = 4)    │{RESET}")
    print(f"  {DIM}└──────────────────────────────────────────────────────────┘{RESET}")
    print()


if __name__ == '__main__':
    run_demo()
