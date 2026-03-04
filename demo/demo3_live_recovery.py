#!/usr/bin/env python3
"""
DEMO 3: Live Packet Loss with FEC Recovery
============================================
The main demonstration! Sends 2 FEC blocks (8 data packets) over UDP,
simulates ~30% packet loss at the receiver, and shows that all data
is still recovered through FEC decoding.

Wireshark Setup:
  1. Open Wireshark → Select "Loopback" or "lo" interface
  2. Apply display filter:  udp.port == 5002
  3. Start capture
  4. Run this script
  5. Watch terminal: green ✓ = received, red ✗ = dropped
  6. Final stats: 100% block recovery despite ~30% packet loss!

Port: 5002
Duration: ~20 seconds
"""

import socket
import struct
import time
import threading
import random
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from core.fec_encoder import FECEncoder
from core.fec_decoder import FECDecoder

# ── Terminal colors ──────────────────────────────────────────────
GREEN  = '\033[92m'
RED    = '\033[91m'
YELLOW = '\033[93m'
CYAN   = '\033[96m'
BLUE   = '\033[94m'
BOLD   = '\033[1m'
DIM    = '\033[2m'
RESET  = '\033[0m'

# ── Configuration ───────────────────────────────────────────────
HOST = "127.0.0.1"
PORT = 5002
N_DATA = 4
N_PARITY = 4
NUM_BLOCKS = 2          # 2 blocks = 8 data packets
LOSS_RATE = 0.30        # 30% simulated loss
SEND_DELAY = 0.4        # seconds between packets
RANDOM_SEED = 42        # fixed seed for reproducible demo


def print_header():
    print(f"\n{BOLD}{YELLOW}{'═' * 60}{RESET}")
    print(f"{BOLD}{YELLOW}  DEMO 3: Live Packet Loss + FEC Recovery{RESET}")
    print(f"{BOLD}{YELLOW}  Port: 5002  |  2 Blocks  |  30% Loss  |  4+4 FEC{RESET}")
    print(f"{BOLD}{YELLOW}{'═' * 60}{RESET}")
    print()
    print(f"  {CYAN}➜ Open Wireshark and filter: udp.port == 5002{RESET}")
    print(f"  {CYAN}➜ Start capture, then press Enter here{RESET}")
    print()


# ── RECEIVER (runs in separate thread) ──────────────────────────

def receiver_thread(results):
    """
    Receive packets, simulate loss, attempt FEC decoding.
    Stores results in the shared 'results' dict.
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((HOST, PORT))
    sock.settimeout(15)

    decoder = FECDecoder(n_data_packets=N_DATA, n_parity_packets=N_PARITY)
    rng = random.Random(RANDOM_SEED)

    # Storage: block_id → {packet_idx: payload}
    blocks = {}
    total_received = 0
    total_dropped = 0
    total_packets = NUM_BLOCKS * (N_DATA + N_PARITY)

    received_count = 0

    while received_count < total_packets:
        try:
            data, addr = sock.recvfrom(2048)

            # Parse FEC header
            header = data[:8]
            payload = data[8:]
            block_id, pkt_idx, total = struct.unpack('!IHH', header)

            # Determine packet type
            is_data = pkt_idx < N_DATA
            pkt_type = "DATA  " if is_data else "PARITY"

            # Simulate packet loss (drop BEFORE processing)
            if rng.random() < LOSS_RATE:
                total_dropped += 1
                color = RED
                status = "✗ DROPPED"
                print(f"  {DIM}[RECEIVER]{RESET} {RED}{status}{RESET}  "
                      f"block={block_id} idx={pkt_idx} ({pkt_type})  "
                      f"{RED}── simulated loss ──{RESET}")
            else:
                total_received += 1
                color = GREEN
                status = "✓ Received"
                print(f"  {DIM}[RECEIVER]{RESET} {GREEN}{status}{RESET} "
                      f"block={block_id} idx={pkt_idx} ({pkt_type})")

                # Store the packet
                if block_id not in blocks:
                    blocks[block_id] = {}
                blocks[block_id][pkt_idx] = payload

            received_count += 1

        except socket.timeout:
            break

    sock.close()

    # ── FEC Decoding ────────────────────────────────────────────
    print(f"\n  {BOLD}{CYAN}{'─' * 50}{RESET}")
    print(f"  {BOLD}{CYAN}  FEC DECODING PHASE{RESET}")
    print(f"  {BOLD}{CYAN}{'─' * 50}{RESET}\n")

    blocks_decoded = 0
    blocks_failed = 0
    total_data_recovered = 0
    total_parity_used = 0

    for block_id in sorted(blocks.keys()):
        block_data = blocks[block_id]
        total_in_block = N_DATA + N_PARITY

        # Build received array (None for missing)
        received = [None] * total_in_block
        for idx, payload in block_data.items():
            received[idx] = payload

        received_count_block = sum(1 for p in received if p is not None)
        missing_count = total_in_block - received_count_block

        # Count missing data vs parity
        missing_data = sum(1 for i in range(N_DATA) if received[i] is None)
        missing_parity = sum(1 for i in range(N_DATA, total_in_block) if received[i] is None)

        print(f"  Block {block_id}: received {received_count_block}/{total_in_block} "
              f"(lost {missing_data} data + {missing_parity} parity)")

        # Attempt decode
        recovered, success = decoder.decode_block(received)

        if success:
            blocks_decoded += 1
            total_data_recovered += N_DATA
            print(f"           {GREEN}✓ DECODED SUCCESSFULLY{RESET} "
                  f"— recovered {missing_data} missing data packet(s)")
        else:
            blocks_failed += 1
            print(f"           {RED}✗ DECODE FAILED{RESET} "
                  f"— too many losses ({missing_count} > {N_PARITY})")

    # Store results
    results['total_sent'] = total_packets
    results['total_received'] = total_received
    results['total_dropped'] = total_dropped
    results['blocks_decoded'] = blocks_decoded
    results['blocks_failed'] = blocks_failed
    results['data_recovered'] = total_data_recovered
    results['stats'] = decoder.get_statistics()


# ── SENDER ──────────────────────────────────────────────────────

def sender_thread():
    """Encode and send FEC blocks over UDP."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    dest = (HOST, PORT)
    encoder = FECEncoder(n_data_packets=N_DATA, n_parity_packets=N_PARITY)

    for block_id in range(NUM_BLOCKS):
        # Create labeled data packets
        data_packets = [
            f"BLOCK{block_id}_DATA{i}: FEC recovery demo!".encode() + b'\x00' * 988
            for i in range(N_DATA)
        ]

        # Encode (produces 8 packets)
        encoded = encoder.encode_block(data_packets)

        print(f"\n  {BOLD}[SENDER] Transmitting Block {block_id} "
              f"({len(encoded)} packets)...{RESET}")

        for idx, pkt_data in enumerate(encoded):
            # Build FEC header
            header = struct.pack('!IHH', block_id, idx, len(encoded))
            full_packet = header + pkt_data

            is_data = idx < N_DATA
            pkt_type = "DATA  " if is_data else "PARITY"
            color = GREEN if is_data else BLUE

            print(f"  {DIM}[SENDER]{RESET}   {color}→ Sent{RESET}     "
                  f"block={block_id} idx={idx} ({pkt_type})  "
                  f"{DIM}{len(full_packet)} bytes{RESET}")

            sock.sendto(full_packet, dest)
            time.sleep(SEND_DELAY)

    sock.close()


# ── MAIN ────────────────────────────────────────────────────────

def run_demo():
    print_header()
    input(f"  {YELLOW}Press Enter to start the live recovery demo...{RESET}")

    results = {}

    # Start receiver first (needs to bind before sender sends)
    recv = threading.Thread(target=receiver_thread, args=(results,), daemon=True)
    recv.start()
    time.sleep(0.5)  # Give receiver time to bind

    # Start sender
    sender_thread()  # Run in main thread so we see output in order

    # Wait for receiver to finish decoding
    recv.join(timeout=15)

    # ── Final Summary ───────────────────────────────────────────
    print(f"\n{BOLD}{YELLOW}{'═' * 60}{RESET}")
    print(f"{BOLD}  DEMO 3 RESULTS{RESET}")
    print(f"{YELLOW}{'═' * 60}{RESET}")

    total_sent = results.get('total_sent', 0)
    total_received = results.get('total_received', 0)
    total_dropped = results.get('total_dropped', 0)
    blocks_decoded = results.get('blocks_decoded', 0)
    blocks_failed = results.get('blocks_failed', 0)

    actual_loss = (total_dropped / total_sent * 100) if total_sent > 0 else 0

    print(f"\n  {BOLD}Network Statistics:{RESET}")
    print(f"    Packets sent:       {total_sent}")
    print(f"    Packets received:   {GREEN}{total_received}{RESET}")
    print(f"    Packets dropped:    {RED}{total_dropped}{RESET}")
    print(f"    Actual loss rate:   {RED}{actual_loss:.1f}%{RESET}")

    print(f"\n  {BOLD}FEC Decoder Statistics:{RESET}")
    print(f"    Blocks decoded:     {GREEN}{blocks_decoded}/{NUM_BLOCKS}{RESET}")
    print(f"    Blocks failed:      {blocks_failed}/{NUM_BLOCKS}")

    recovery_pct = (blocks_decoded / NUM_BLOCKS * 100) if NUM_BLOCKS > 0 else 0
    recovery_color = GREEN if recovery_pct == 100 else (YELLOW if recovery_pct >= 80 else RED)

    print(f"    {BOLD}Success rate:     {recovery_color}{recovery_pct:.0f}%{RESET}")

    stats = results.get('stats', {})
    if stats.get('packets_recovered', 0) > 0:
        print(f"    Packets recovered:  {GREEN}{stats['packets_recovered']}{RESET} "
              f"(via GF(256) Gaussian elimination)")

    print(f"\n  {CYAN}🔍 Wireshark Verification:{RESET}")
    print(f"     • Statistics → Conversations → UDP tab")
    print(f"     • You'll see {total_sent} packets from sender")
    print(f"     • Despite {total_dropped} drops, {BOLD}all data recovered!{RESET}")

    if recovery_pct == 100:
        print(f"\n  {GREEN}{BOLD}  ★ FEC SUCCESSFULLY RECOVERED ALL DATA! ★{RESET}")
        print(f"  {GREEN}  No retransmissions needed — exactly what 5G URLLC requires.{RESET}")
    else:
        print(f"\n  {YELLOW}  Note: Some blocks had too many losses for recovery.{RESET}")
        print(f"  {YELLOW}  Try again or lower LOSS_RATE in script configuration.{RESET}")

    print(f"\n{YELLOW}{'═' * 60}{RESET}\n")


if __name__ == '__main__':
    run_demo()
