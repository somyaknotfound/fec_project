#!/usr/bin/env python3
"""
DEMO 1: Baseline Transmission WITHOUT FEC
==========================================
Sends 10 UDP packets with NO forward error correction.
Use this to show that packet loss is permanent without FEC.

Wireshark Setup:
  1. Open Wireshark → Select "Loopback" or "lo" interface
  2. Apply display filter:  udp.port == 5000
  3. Start capture
  4. Run this script
  5. Observe: packets appear in order, any loss = permanent loss

Port: 5000
Duration: ~10 seconds
"""

import socket
import time
import sys
import os

# Allow importing from parent directory
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# ── Terminal colors ──────────────────────────────────────────────
GREEN  = '\033[92m'
RED    = '\033[91m'
YELLOW = '\033[93m'
CYAN   = '\033[96m'
BOLD   = '\033[1m'
RESET  = '\033[0m'


def print_header():
    print(f"\n{BOLD}{YELLOW}{'═' * 60}{RESET}")
    print(f"{BOLD}{YELLOW}  DEMO 1: Baseline UDP Transmission (NO FEC){RESET}")
    print(f"{BOLD}{YELLOW}  Port: 5000   |   Packets: 10   |   Protection: NONE{RESET}")
    print(f"{BOLD}{YELLOW}{'═' * 60}{RESET}")
    print()
    print(f"  {CYAN}➜ Open Wireshark and filter: udp.port == 5000{RESET}")
    print(f"  {CYAN}➜ Start capture, then press Enter here{RESET}")
    print()


def run_demo():
    print_header()
    input(f"  {YELLOW}Press Enter to start sending packets...{RESET}")
    print()

    # Create UDP socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    dest = ("127.0.0.1", 5000)

    num_packets = 10
    packet_size = 1024
    delay = 0.5  # 500ms between packets — slow enough to watch in Wireshark

    print(f"  {BOLD}Sending {num_packets} unprotected packets...{RESET}\n")

    for i in range(num_packets):
        # Create a clearly-labeled payload
        # The label will be visible in Wireshark's hex dump
        label = f"PACKET_{i:02d}_NO_FEC".encode()
        padding = b'\x00' * (packet_size - len(label))
        payload = label + padding

        sock.sendto(payload, dest)

        # Progress bar
        bar_fill = '█' * (i + 1) + '░' * (num_packets - i - 1)
        print(f"  {GREEN}✓ Sent PACKET_{i:02d}{RESET}  "
              f"[{bar_fill}] {(i+1)*10}%  "
              f"({len(payload)} bytes)")

        time.sleep(delay)

    sock.close()

    # Summary
    print(f"\n{BOLD}{YELLOW}{'═' * 60}{RESET}")
    print(f"{BOLD}  DEMO 1 SUMMARY{RESET}")
    print(f"{YELLOW}{'═' * 60}{RESET}")
    print(f"  Packets sent:      {GREEN}{num_packets}{RESET}")
    print(f"  Packet size:       {packet_size} bytes")
    print(f"  Total data:        {num_packets * packet_size} bytes")
    print(f"  Port:              5000")
    print(f"  FEC protection:    {RED}NONE{RESET}")
    print()
    print(f"  {CYAN}🔍 Check Wireshark:{RESET}")
    print(f"     • You should see {num_packets} UDP packets")
    print(f"     • Click any packet → Data section shows \"PACKET_XX_NO_FEC\"")
    print(f"     • If any packet is lost in transit, that data is {RED}GONE FOREVER{RESET}")
    print(f"     • No recovery mechanism exists without FEC")
    print(f"{YELLOW}{'═' * 60}{RESET}\n")


if __name__ == '__main__':
    run_demo()
