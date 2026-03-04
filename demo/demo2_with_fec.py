#!/usr/bin/env python3
"""
DEMO 2: FEC Packet Structure
==============================
Sends exactly 1 FEC block (4 data → 8 total packets with parity).
Use this to show the FEC header structure in Wireshark.

Wireshark Setup:
  1. Open Wireshark → Select "Loopback" or "lo" interface
  2. Apply display filter:  udp.port == 5001
  3. Start capture
  4. Run this script
  5. Click any captured packet → expand UDP → Data
  6. First 8 bytes = FEC header:
       Bytes 0-3: Block ID   (uint32, big-endian)
       Bytes 4-5: Packet Idx (uint16, big-endian)
       Bytes 6-7: Total      (uint16, big-endian)

Port: 5001
Duration: ~8 seconds
"""

import socket
import struct
import time
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from core.fec_encoder import FECEncoder

# ── Terminal colors ──────────────────────────────────────────────
GREEN  = '\033[92m'
RED    = '\033[91m'
YELLOW = '\033[93m'
CYAN   = '\033[96m'
BLUE   = '\033[94m'
BOLD   = '\033[1m'
DIM    = '\033[2m'
RESET  = '\033[0m'


def print_header():
    print(f"\n{BOLD}{YELLOW}{'═' * 60}{RESET}")
    print(f"{BOLD}{YELLOW}  DEMO 2: FEC Packet Structure{RESET}")
    print(f"{BOLD}{YELLOW}  Port: 5001   |   1 Block   |   4 Data + 4 Parity{RESET}")
    print(f"{BOLD}{YELLOW}{'═' * 60}{RESET}")
    print()
    print(f"  {CYAN}➜ Open Wireshark and filter: udp.port == 5001{RESET}")
    print(f"  {CYAN}➜ Start capture, then press Enter here{RESET}")
    print()


def format_hex(data, max_bytes=8):
    """Format bytes as hex string for display."""
    return ' '.join(f'{b:02X}' for b in data[:max_bytes])


def run_demo():
    print_header()
    input(f"  {YELLOW}Press Enter to start sending FEC block...{RESET}")
    print()

    # Create FEC encoder (4 data + 4 parity)
    encoder = FECEncoder(n_data_packets=4, n_parity_packets=4)

    # Create clearly-labeled data packets
    data_packets = [
        b"DATA_PKT_0: Hello 5G World!   " + b'\xAA' * 994,
        b"DATA_PKT_1: FEC Protection!   " + b'\xBB' * 994,
        b"DATA_PKT_2: Erasure Coding!   " + b'\xCC' * 994,
        b"DATA_PKT_3: GF(256) Math!     " + b'\xDD' * 994,
    ]

    # Encode: 4 data → 8 packets (4 data + 4 parity)
    print(f"  {BOLD}Step 1: Encoding data with GF(256) Cauchy matrix...{RESET}")
    encoded_packets = encoder.encode_block(data_packets)
    print(f"  {GREEN}✓ Encoded: {len(data_packets)} data → {len(encoded_packets)} total packets{RESET}")
    print(f"  {DIM}  Code rate: 0.5  |  Overhead: 100%  |  Max recovery: 4 losses{RESET}")
    print()

    # Send each packet with FEC header
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    dest = ("127.0.0.1", 5001)
    block_id = 0
    total = len(encoded_packets)

    print(f"  {BOLD}Step 2: Sending {total} packets with FEC headers...{RESET}\n")

    # Print header format legend
    print(f"  {DIM}  FEC Header Format: [Block ID: 4B] [Pkt Idx: 2B] [Total: 2B]{RESET}")
    print(f"  {DIM}  ─────────────────────────────────────────────────────────────{RESET}")
    print()

    for idx, pkt_data in enumerate(encoded_packets):
        # Build FEC header: block_id(4B) | packet_idx(2B) | total(2B)
        header = struct.pack('!IHH', block_id, idx, total)
        full_packet = header + pkt_data

        sock.sendto(full_packet, dest)

        # Determine packet type
        if idx < 4:
            pkt_type = f"{GREEN}DATA  {RESET}"
            pkt_label = f"DATA_PKT_{idx}"
        else:
            pkt_type = f"{BLUE}PARITY{RESET}"
            pkt_label = f"PARITY_{idx - 4}"

        # Show header details
        header_hex = format_hex(header)
        print(f"  {pkt_type}  [{pkt_label}]  "
              f"block={block_id}  idx={idx}  total={total}  "
              f"{DIM}header: {header_hex}{RESET}")

        time.sleep(0.8)  # Slow enough to watch individual packets in Wireshark

    sock.close()

    # Summary with hex decoding example
    print(f"\n{BOLD}{YELLOW}{'═' * 60}{RESET}")
    print(f"{BOLD}  DEMO 2 SUMMARY{RESET}")
    print(f"{YELLOW}{'═' * 60}{RESET}")
    print(f"  Packets sent:      {GREEN}8{RESET} (4 data + 4 parity)")
    print(f"  Block ID:          0")
    print(f"  Port:              5001")
    print(f"  Header size:       8 bytes")
    print(f"  Payload size:      1024 bytes")
    print()
    print(f"  {CYAN}🔍 Wireshark Analysis:{RESET}")
    print(f"     1. Click any packet in the capture")
    print(f"     2. Expand: User Datagram Protocol → Data")
    print(f"     3. Look at the first 8 bytes (hex):")
    print()
    print(f"        {BOLD}Example: Packet index 3 (4th packet){RESET}")
    print(f"        ┌──────────────┬────────┬────────┐")
    print(f"        │  Block ID    │ Pkt ID │ Total  │")
    print(f"        │  00 00 00 00 │ 00 03  │ 00 08  │")
    print(f"        └──────────────┴────────┴────────┘")
    print(f"          block = 0      idx = 3  total = 8")
    print()
    print(f"     4. After byte 8: payload begins")
    print(f"        Data packets show: \"DATA_PKT_X: ...\"")
    print(f"        Parity packets show: computed GF(256) bytes")
    print(f"{YELLOW}{'═' * 60}{RESET}\n")


if __name__ == '__main__':
    run_demo()
