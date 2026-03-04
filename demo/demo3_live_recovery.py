#!/usr/bin/env python3
"""
DEMO 3: Live Packet Loss with FEC Recovery (Kernel-Level Loss)
================================================================
The main demonstration! Uses Linux Traffic Control (tc netem) to drop
packets at the KERNEL level — so Wireshark genuinely shows missing packets.

How it works:
  1. Applies 'tc netem loss 30%' on loopback interface  (requires sudo)
  2. Sender transmits 2 FEC blocks (16 packets) over UDP
  3. Kernel randomly drops ~30% before they reach the receiver
  4. Wireshark only sees the SURVIVING packets (not all 16!)
  5. FEC decoder recovers all original data from the survivors
  6. Removes the netem rule when done

Wireshark Setup:
  1. Open Wireshark → Select "Loopback: lo" interface
  2. Apply display filter:  udp.port == 5002
  3. Start capture
  4. Run this script WITH SUDO:  sudo python3 demo3_live_recovery.py
  5. Watch: Wireshark shows FEWER than 16 packets (real kernel drops!)
  6. Terminal shows: 100% data recovery despite the losses

Fallback: If not running as root, falls back to application-level loss
          simulation (Wireshark will show all packets in fallback mode).

Port: 5002
Duration: ~20 seconds
"""

import socket
import struct
import time
import threading
import os
import sys
import subprocess
import platform

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
NUM_BLOCKS = 2          # 2 blocks = 8 data packets → 16 total transmitted
LOSS_RATE = 30          # 30% kernel-level packet loss
SEND_DELAY = 0.4        # seconds between packets (slow enough for Wireshark)


# ── NETEM (kernel-level loss) ───────────────────────────────────

def is_root():
    """Check if running as root/sudo."""
    if platform.system() != 'Linux':
        return False
    return os.geteuid() == 0


def setup_netem(loss_pct):
    """
    Apply packet loss on the loopback interface using tc netem.
    This causes the KERNEL to drop packets before they reach
    the application — so Wireshark sees the drops too.
    """
    try:
        # Remove any existing rules first
        subprocess.run(
            ['tc', 'qdisc', 'del', 'dev', 'lo', 'root'],
            capture_output=True, timeout=5
        )
        # Add packet loss rule
        result = subprocess.run(
            ['tc', 'qdisc', 'add', 'dev', 'lo', 'root', 'netem', 'loss', f'{loss_pct}%'],
            capture_output=True, timeout=5
        )
        if result.returncode == 0:
            return True
        else:
            print(f"  {RED}✗ tc netem failed: {result.stderr.decode().strip()}{RESET}")
            return False
    except Exception as e:
        print(f"  {RED}✗ tc netem error: {e}{RESET}")
        return False


def teardown_netem():
    """Remove the netem packet loss rule."""
    try:
        subprocess.run(
            ['tc', 'qdisc', 'del', 'dev', 'lo', 'root'],
            capture_output=True, timeout=5
        )
    except Exception:
        pass  # Best effort cleanup


def print_header(using_netem):
    mode = "KERNEL-LEVEL (tc netem)" if using_netem else "APPLICATION-LEVEL (fallback)"
    print(f"\n{BOLD}{YELLOW}{'═' * 60}{RESET}")
    print(f"{BOLD}{YELLOW}  DEMO 3: Live Packet Loss + FEC Recovery{RESET}")
    print(f"{BOLD}{YELLOW}  Port: 5002  |  2 Blocks  |  ~30% Loss{RESET}")
    print(f"{BOLD}{YELLOW}  Loss Mode: {mode}{RESET}")
    print(f"{BOLD}{YELLOW}{'═' * 60}{RESET}")

    if using_netem:
        print(f"\n  {GREEN}✓ Kernel-level loss active (tc netem){RESET}")
        print(f"    {DIM}Packets are dropped BEFORE reaching the receiver.{RESET}")
        print(f"    {DIM}Wireshark will show missing packets!{RESET}")
    else:
        print(f"\n  {YELLOW}⚠ Fallback: application-level loss simulation{RESET}")
        print(f"    {DIM}Run with sudo for kernel-level drops visible in Wireshark:{RESET}")
        print(f"    {CYAN}sudo python3 demo/demo3_live_recovery.py{RESET}")

    print(f"\n  {CYAN}➜ Open Wireshark and filter: udp.port == 5002{RESET}")
    print(f"  {CYAN}➜ Start capture, then press Enter here{RESET}")
    print()


# ── RECEIVER ────────────────────────────────────────────────────

def receiver_thread(results, using_netem):
    """
    Receive packets and attempt FEC decoding.
    In netem mode: just receives whatever the kernel delivers (loss is real).
    In fallback mode: simulates loss in application (for non-Linux/non-root).
    """
    import random

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind((HOST, PORT))
    sock.settimeout(15)

    decoder = FECDecoder(n_data_packets=N_DATA, n_parity_packets=N_PARITY)
    rng = random.Random(42)

    # Storage: block_id → {packet_idx: payload}
    blocks = {}
    total_expected = NUM_BLOCKS * (N_DATA + N_PARITY)
    total_received = 0
    total_dropped = 0  # Only tracked in fallback mode

    attempts = 0
    max_attempts = total_expected + 10  # safety limit

    while attempts < max_attempts:
        try:
            data, addr = sock.recvfrom(2048)
            attempts += 1

            # Parse FEC header
            header = data[:8]
            payload = data[8:]
            block_id, pkt_idx, total = struct.unpack('!IHH', header)

            is_data = pkt_idx < N_DATA
            pkt_type = "DATA  " if is_data else "PARITY"

            if not using_netem and rng.random() < (LOSS_RATE / 100.0):
                # FALLBACK: simulate loss in application
                total_dropped += 1
                print(f"  {DIM}[RECEIVER]{RESET} {RED}✗ DROPPED{RESET}  "
                      f"block={block_id} idx={pkt_idx} ({pkt_type})  "
                      f"{RED}── app-level loss ──{RESET}")
                continue

            # Packet survived (either netem didn't drop it, or fallback kept it)
            total_received += 1
            print(f"  {DIM}[RECEIVER]{RESET} {GREEN}✓ Received{RESET} "
                  f"block={block_id} idx={pkt_idx} ({pkt_type})")

            if block_id not in blocks:
                blocks[block_id] = {}
            blocks[block_id][pkt_idx] = payload

            # Check if we've likely received everything that will arrive
            if total_received + total_dropped >= total_expected:
                break

        except socket.timeout:
            break

    sock.close()

    # ── FEC Decoding ────────────────────────────────────────────
    print(f"\n  {BOLD}{CYAN}{'─' * 50}{RESET}")
    print(f"  {BOLD}{CYAN}  FEC DECODING PHASE{RESET}")
    print(f"  {BOLD}{CYAN}{'─' * 50}{RESET}\n")

    blocks_decoded = 0
    blocks_failed = 0

    for block_id in sorted(blocks.keys()):
        block_data = blocks[block_id]
        total_in_block = N_DATA + N_PARITY

        # Build received array (None for missing)
        received = [None] * total_in_block
        for idx, payload in block_data.items():
            received[idx] = payload

        received_count = sum(1 for p in received if p is not None)
        missing_data = sum(1 for i in range(N_DATA) if received[i] is None)
        missing_parity = sum(1 for i in range(N_DATA, total_in_block) if received[i] is None)
        missing_indices = [i for i in range(total_in_block) if received[i] is None]

        print(f"  Block {block_id}: received {received_count}/{total_in_block} "
              f"(lost {missing_data} data + {missing_parity} parity)")
        if missing_indices:
            print(f"           {DIM}Missing indices: {missing_indices}{RESET}")

        recovered, success = decoder.decode_block(received)

        if success:
            blocks_decoded += 1
            print(f"           {GREEN}✓ DECODED SUCCESSFULLY{RESET} "
                  f"— recovered {missing_data} missing data packet(s)")
        else:
            blocks_failed += 1
            print(f"           {RED}✗ DECODE FAILED{RESET} "
                  f"(need {N_DATA} packets, only got {received_count})")

    # Detect blocks we never saw at all
    for expected_block in range(NUM_BLOCKS):
        if expected_block not in blocks:
            blocks_failed += 1
            print(f"  Block {expected_block}: {RED}NEVER RECEIVED — all packets lost!{RESET}")

    # Results
    total_missing = total_expected - total_received - total_dropped
    results['total_sent'] = total_expected
    results['total_received'] = total_received
    results['total_kernel_dropped'] = total_missing if using_netem else 0
    results['total_app_dropped'] = total_dropped
    results['blocks_decoded'] = blocks_decoded
    results['blocks_failed'] = blocks_failed
    results['stats'] = decoder.get_statistics()
    results['using_netem'] = using_netem


# ── SENDER ──────────────────────────────────────────────────────

def sender_thread():
    """Encode and send FEC blocks over UDP. No loss here — all packets sent."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    dest = (HOST, PORT)
    encoder = FECEncoder(n_data_packets=N_DATA, n_parity_packets=N_PARITY)

    total_sent = 0

    for block_id in range(NUM_BLOCKS):
        data_packets = [
            f"BLOCK{block_id}_DATA{i}: Recovery demo!".encode() + b'\x00' * 988
            for i in range(N_DATA)
        ]

        encoded = encoder.encode_block(data_packets)

        print(f"\n  {BOLD}[SENDER] Transmitting Block {block_id} "
              f"({len(encoded)} packets)...{RESET}")

        for idx, pkt_data in enumerate(encoded):
            header = struct.pack('!IHH', block_id, idx, len(encoded))
            full_packet = header + pkt_data

            is_data = idx < N_DATA
            pkt_type = "DATA  " if is_data else "PARITY"
            color = GREEN if is_data else BLUE

            print(f"  {DIM}[SENDER]{RESET}   {color}→ Sent{RESET}     "
                  f"block={block_id} idx={idx} ({pkt_type})  "
                  f"{DIM}{len(full_packet)} bytes{RESET}")

            sock.sendto(full_packet, dest)
            total_sent += 1
            time.sleep(SEND_DELAY)

    sock.close()
    return total_sent


# ── MAIN ────────────────────────────────────────────────────────

def run_demo():
    # Determine if we can use kernel-level loss
    using_netem = False

    if is_root():
        print(f"\n  {CYAN}Setting up kernel-level packet loss (tc netem)...{RESET}")
        using_netem = setup_netem(LOSS_RATE)
    elif platform.system() == 'Linux':
        print(f"\n  {YELLOW}Not running as root. Use sudo for Wireshark-visible loss:{RESET}")
        print(f"  {CYAN}  sudo python3 demo/demo3_live_recovery.py{RESET}\n")

    print_header(using_netem)
    input(f"  {YELLOW}Press Enter to start the live recovery demo...{RESET}")

    results = {}

    try:
        # Start receiver first
        recv = threading.Thread(target=receiver_thread,
                                args=(results, using_netem), daemon=True)
        recv.start()
        time.sleep(0.5)

        # Run sender in main thread
        sender_thread()

        # Wait for receiver to finish
        time.sleep(2)  # Extra time for last packets to arrive
        recv.join(timeout=15)

    finally:
        # ALWAYS clean up netem, even on error
        if using_netem:
            print(f"\n  {DIM}Removing tc netem rule...{RESET}")
            teardown_netem()
            print(f"  {GREEN}✓ Network restored to normal{RESET}")

    # ── Final Summary ───────────────────────────────────────────
    print(f"\n{BOLD}{YELLOW}{'═' * 60}{RESET}")
    print(f"{BOLD}  DEMO 3 RESULTS{RESET}")
    print(f"{YELLOW}{'═' * 60}{RESET}")

    total_sent = results.get('total_sent', 0)
    total_received = results.get('total_received', 0)
    kernel_dropped = results.get('total_kernel_dropped', 0)
    app_dropped = results.get('total_app_dropped', 0)
    blocks_decoded = results.get('blocks_decoded', 0)
    blocks_failed = results.get('blocks_failed', 0)
    was_netem = results.get('using_netem', False)

    total_lost = total_sent - total_received
    actual_loss = (total_lost / total_sent * 100) if total_sent > 0 else 0

    print(f"\n  {BOLD}Network Statistics:{RESET}")
    print(f"    Packets sent:       {total_sent}")
    print(f"    Packets received:   {GREEN}{total_received}{RESET}")
    print(f"    Packets lost:       {RED}{total_lost}{RESET}")
    print(f"    Actual loss rate:   {RED}{actual_loss:.1f}%{RESET}")

    if was_netem:
        print(f"    Loss method:        {GREEN}Kernel-level (tc netem){RESET}")
        print(f"                        {DIM}↳ Wireshark shows only {total_received} packets!{RESET}")
    else:
        print(f"    Loss method:        {YELLOW}Application-level (fallback){RESET}")
        print(f"                        {DIM}↳ Wireshark shows all {total_sent} packets{RESET}")

    print(f"\n  {BOLD}FEC Decoder Statistics:{RESET}")
    print(f"    Blocks decoded:     {GREEN}{blocks_decoded}/{NUM_BLOCKS}{RESET}")
    print(f"    Blocks failed:      {blocks_failed}/{NUM_BLOCKS}")

    recovery_pct = (blocks_decoded / NUM_BLOCKS * 100) if NUM_BLOCKS > 0 else 0
    color = GREEN if recovery_pct == 100 else (YELLOW if recovery_pct >= 80 else RED)

    print(f"    {BOLD}Success rate:     {color}{recovery_pct:.0f}%{RESET}")

    stats = results.get('stats', {})
    if stats.get('packets_recovered', 0) > 0:
        print(f"    Packets recovered:  {GREEN}{stats['packets_recovered']}{RESET} "
              f"(via GF(256) Gaussian elimination)")

    print(f"\n  {CYAN}🔍 Wireshark Verification:{RESET}")
    if was_netem:
        print(f"     • Wireshark captured only ~{total_received} of {total_sent} packets")
        print(f"     • {RED}{total_lost} packets are MISSING from the capture{RESET}")
        print(f"     • This is REAL kernel-level loss, not simulated!")
        print(f"     • Statistics → Conversations → UDP confirms the count")
    else:
        print(f"     • Fallback mode: Wireshark shows all {total_sent} packets")
        print(f"     • For visible loss, re-run with: {CYAN}sudo python3 demo/demo3_live_recovery.py{RESET}")

    if recovery_pct == 100:
        print(f"\n  {GREEN}{BOLD}  ★ FEC RECOVERED ALL DATA DESPITE {total_lost} LOST PACKETS! ★{RESET}")
        print(f"  {GREEN}  No retransmissions needed — 5G URLLC ready.{RESET}")
    elif recovery_pct > 0:
        print(f"\n  {YELLOW}  Partial recovery: {blocks_decoded}/{NUM_BLOCKS} blocks.{RESET}")
        print(f"  {YELLOW}  Some blocks had too many losses (>{N_PARITY} per block).{RESET}")
    else:
        print(f"\n  {RED}  All blocks failed — loss rate too high for this FEC code.{RESET}")
        print(f"  {RED}  Try a lower loss rate or increase parity packets.{RESET}")

    print(f"\n{YELLOW}{'═' * 60}{RESET}\n")


if __name__ == '__main__':
    run_demo()
