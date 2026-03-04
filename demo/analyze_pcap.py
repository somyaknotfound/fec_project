#!/usr/bin/env python3
"""
PCAP Analyzer — Post-Demo Protocol Analysis
=============================================
Reads PCAP files captured during demos, parses FEC headers, and generates
a protocol analysis report for the academic project documentation.

Usage:
    python3 analyze_pcap.py <pcap_file>
    python3 analyze_pcap.py data/captures/capture_demo3_*.pcap

Requires: scapy (pip install scapy)
Fallback: Works without scapy using raw PCAP parsing (limited).

Output: Prints analysis to terminal + saves Markdown report.
"""

import struct
import os
import sys
import math
from datetime import datetime
from collections import defaultdict

# ── Terminal colors ──────────────────────────────────────────────
GREEN  = '\033[92m'
RED    = '\033[91m'
YELLOW = '\033[93m'
CYAN   = '\033[96m'
BOLD   = '\033[1m'
DIM    = '\033[2m'
RESET  = '\033[0m'


class FECPacketInfo:
    """Parsed FEC packet information."""
    def __init__(self, timestamp, block_id, packet_idx, total_packets,
                 payload_size, raw_size):
        self.timestamp = timestamp
        self.block_id = block_id
        self.packet_idx = packet_idx
        self.total_packets = total_packets
        self.payload_size = payload_size
        self.raw_size = raw_size
        self.is_data = packet_idx < (total_packets // 2)  # first half = data


class PCAPAnalyzer:
    """
    Analyzes PCAP files containing FEC-encoded UDP traffic.
    Parses custom FEC headers and generates protocol statistics.
    """

    def __init__(self, pcap_file, udp_port=None):
        """
        Parameters
        ----------
        pcap_file : str
            Path to the PCAP file.
        udp_port : int, optional
            Filter to specific UDP port. None = analyze all UDP.
        """
        self.pcap_file = pcap_file
        self.udp_port = udp_port
        self.packets = []
        self.blocks = defaultdict(dict)

    def parse(self):
        """Parse the PCAP file and extract FEC packet information."""
        try:
            self._parse_with_scapy()
        except ImportError:
            print(f"  {YELLOW}⚠ scapy not installed. Using raw PCAP parser.{RESET}")
            print(f"  {DIM}  Install: pip install scapy{RESET}")
            self._parse_raw_pcap()

        # Group by block
        for pkt in self.packets:
            self.blocks[pkt.block_id][pkt.packet_idx] = pkt

        return len(self.packets)

    def _parse_with_scapy(self):
        """Parse using scapy (preferred method)."""
        from scapy.all import rdpcap, UDP

        cap = rdpcap(self.pcap_file)
        base_time = None

        for pkt in cap:
            if not pkt.haslayer(UDP):
                continue

            udp = pkt[UDP]
            if self.udp_port and udp.dport != self.udp_port and udp.sport != self.udp_port:
                continue

            payload = bytes(udp.payload)
            if len(payload) < 8:
                continue  # Too small for FEC header

            # Parse FEC header
            try:
                block_id, pkt_idx, total = struct.unpack('!IHH', payload[:8])
            except struct.error:
                continue

            # Sanity check header values
            if total == 0 or total > 100 or pkt_idx >= total:
                continue

            timestamp = float(pkt.time)
            if base_time is None:
                base_time = timestamp

            info = FECPacketInfo(
                timestamp=timestamp - base_time,
                block_id=block_id,
                packet_idx=pkt_idx,
                total_packets=total,
                payload_size=len(payload) - 8,
                raw_size=len(payload),
            )
            self.packets.append(info)

    def _parse_raw_pcap(self):
        """Fallback: parse PCAP file format directly (no scapy needed)."""
        with open(self.pcap_file, 'rb') as f:
            # PCAP global header (24 bytes)
            magic = f.read(4)
            if magic not in (b'\xa1\xb2\xc3\xd4', b'\xd4\xc3\xb2\xa1'):
                raise ValueError("Not a valid PCAP file")

            big_endian = (magic == b'\xa1\xb2\xc3\xd4')
            endian = '>' if big_endian else '<'

            header = f.read(20)
            _, _, _, _, snaplen, network = struct.unpack(endian + 'HHIIII', header[:20])

            base_time = None
            pkt_num = 0

            while True:
                # Packet header (16 bytes)
                pkt_header = f.read(16)
                if len(pkt_header) < 16:
                    break

                ts_sec, ts_usec, incl_len, orig_len = struct.unpack(
                    endian + 'IIII', pkt_header
                )
                timestamp = ts_sec + ts_usec / 1e6
                if base_time is None:
                    base_time = timestamp

                # Read packet data
                pkt_data = f.read(incl_len)
                if len(pkt_data) < incl_len:
                    break

                # Parse Ethernet → IP → UDP → FEC
                # Skip to UDP payload (Eth=14, IP=20, UDP=8 = 42 bytes minimum)
                # For loopback (network=0): no Ethernet header, starts with IP
                if network == 0:  # Loopback (BSD)
                    offset = 4   # 4-byte loopback header
                elif network == 1:  # Ethernet
                    offset = 14  # Ethernet header
                elif network == 101:  # Raw IP
                    offset = 0
                else:
                    offset = 14  # Default to Ethernet

                if len(pkt_data) < offset + 28:  # IP(20) + UDP(8)
                    continue

                # Check IP protocol = UDP (17)
                ip_start = offset
                ip_protocol = pkt_data[ip_start + 9]
                if ip_protocol != 17:
                    continue

                # IP header length
                ip_hlen = (pkt_data[ip_start] & 0x0F) * 4

                # UDP header
                udp_start = ip_start + ip_hlen
                if len(pkt_data) < udp_start + 8:
                    continue

                src_port, dst_port = struct.unpack('!HH', pkt_data[udp_start:udp_start+4])

                if self.udp_port and dst_port != self.udp_port and src_port != self.udp_port:
                    continue

                # UDP payload
                udp_payload = pkt_data[udp_start + 8:]
                if len(udp_payload) < 8:
                    continue

                # Parse FEC header
                try:
                    block_id, pkt_idx, total = struct.unpack('!IHH', udp_payload[:8])
                except struct.error:
                    continue

                if total == 0 or total > 100 or pkt_idx >= total:
                    continue

                info = FECPacketInfo(
                    timestamp=timestamp - base_time,
                    block_id=block_id,
                    packet_idx=pkt_idx,
                    total_packets=total,
                    payload_size=len(udp_payload) - 8,
                    raw_size=len(udp_payload),
                )
                self.packets.append(info)
                pkt_num += 1

    # ── Analysis Methods ────────────────────────────────────────

    def get_block_analysis(self):
        """Analyze block completeness."""
        results = []
        for block_id in sorted(self.blocks.keys()):
            block = self.blocks[block_id]
            if not block:
                continue
            sample = next(iter(block.values()))
            total = sample.total_packets
            n_data = total // 2
            received = len(block)
            data_received = sum(1 for idx in block if idx < n_data)
            parity_received = sum(1 for idx in block if idx >= n_data)
            complete = received >= n_data  # Can decode if >= n_data received
            results.append({
                'block_id': block_id,
                'total': total,
                'received': received,
                'data_received': data_received,
                'parity_received': parity_received,
                'data_lost': n_data - data_received,
                'parity_lost': (total - n_data) - parity_received,
                'recoverable': complete,
                'missing_indices': [i for i in range(total) if i not in block],
            })
        return results

    def get_loss_statistics(self):
        """Calculate overall loss statistics."""
        if not self.blocks:
            return {}
        block_analysis = self.get_block_analysis()
        total_expected = sum(b['total'] for b in block_analysis)
        total_received = sum(b['received'] for b in block_analysis)
        total_lost = total_expected - total_received
        data_lost = sum(b['data_lost'] for b in block_analysis)
        parity_lost = sum(b['parity_lost'] for b in block_analysis)
        recoverable = sum(1 for b in block_analysis if b['recoverable'])

        return {
            'num_blocks': len(block_analysis),
            'total_expected': total_expected,
            'total_received': total_received,
            'total_lost': total_lost,
            'loss_rate': total_lost / total_expected if total_expected > 0 else 0,
            'data_lost': data_lost,
            'parity_lost': parity_lost,
            'recoverable_blocks': recoverable,
            'recovery_rate': recoverable / len(block_analysis) if block_analysis else 0,
        }

    def get_timing_statistics(self):
        """Calculate inter-packet timing statistics."""
        if len(self.packets) < 2:
            return {}
        delays = []
        for i in range(1, len(self.packets)):
            delay = (self.packets[i].timestamp - self.packets[i-1].timestamp) * 1000  # ms
            if delay > 0:
                delays.append(delay)

        if not delays:
            return {}

        delays.sort()
        n = len(delays)
        mean = sum(delays) / n
        var = sum((d - mean) ** 2 for d in delays) / n

        return {
            'count': n,
            'mean_ms': round(mean, 2),
            'std_ms': round(math.sqrt(var), 2),
            'min_ms': round(delays[0], 2),
            'max_ms': round(delays[-1], 2),
            'p50_ms': round(delays[int(n * 0.50)], 2),
            'p95_ms': round(delays[min(int(n * 0.95), n-1)], 2),
        }

    # ── Reporting ───────────────────────────────────────────────

    def print_report(self):
        """Print a formatted analysis report to terminal."""
        print(f"\n{BOLD}{YELLOW}{'═' * 60}{RESET}")
        print(f"{BOLD}  PCAP ANALYSIS REPORT{RESET}")
        print(f"{BOLD}  File: {os.path.basename(self.pcap_file)}{RESET}")
        print(f"{YELLOW}{'═' * 60}{RESET}")

        print(f"\n  {BOLD}Packets Parsed:{RESET} {len(self.packets)}")
        print(f"  {BOLD}Blocks Found:{RESET}   {len(self.blocks)}")

        # Block analysis
        block_analysis = self.get_block_analysis()
        if block_analysis:
            print(f"\n  {BOLD}{CYAN}Block Analysis:{RESET}")
            for b in block_analysis:
                status = f"{GREEN}✓ recoverable{RESET}" if b['recoverable'] else f"{RED}✗ unrecoverable{RESET}"
                print(f"    Block {b['block_id']}: "
                      f"{b['received']}/{b['total']} received  "
                      f"(lost: {b['data_lost']}D + {b['parity_lost']}P)  "
                      f"{status}")
                if b['missing_indices']:
                    print(f"      {DIM}Missing indices: {b['missing_indices']}{RESET}")

        # Loss stats
        loss = self.get_loss_statistics()
        if loss:
            print(f"\n  {BOLD}{CYAN}Loss Statistics:{RESET}")
            print(f"    Total expected:    {loss['total_expected']}")
            print(f"    Total received:    {GREEN}{loss['total_received']}{RESET}")
            print(f"    Total lost:        {RED}{loss['total_lost']}{RESET}")
            print(f"    Loss rate:         {RED}{loss['loss_rate']*100:.1f}%{RESET}")
            print(f"    Data packets lost: {loss['data_lost']}")
            print(f"    Parity lost:       {loss['parity_lost']}")
            print(f"    Recoverable:       {GREEN}{loss['recoverable_blocks']}/{loss['num_blocks']}{RESET} blocks")

        # Timing stats
        timing = self.get_timing_statistics()
        if timing:
            print(f"\n  {BOLD}{CYAN}Timing Statistics:{RESET}")
            print(f"    Mean delay:    {timing['mean_ms']} ms")
            print(f"    Std deviation: {timing['std_ms']} ms")
            print(f"    Min / Max:     {timing['min_ms']} / {timing['max_ms']} ms")
            print(f"    P50 / P95:     {timing['p50_ms']} / {timing['p95_ms']} ms")

        print(f"\n{YELLOW}{'═' * 60}{RESET}\n")

    def generate_markdown_report(self, output_path=None):
        """Generate a Markdown protocol analysis report."""
        if output_path is None:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            output_path = os.path.join(script_dir, '..', 'data', 'results',
                                        'protocol_analysis_report.md')

        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        loss = self.get_loss_statistics()
        timing = self.get_timing_statistics()
        block_analysis = self.get_block_analysis()

        lines = []
        lines.append("# Protocol Analysis Report")
        lines.append(f"\n**Source file:** `{os.path.basename(self.pcap_file)}`  ")
        lines.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  ")
        lines.append(f"**Total packets:** {len(self.packets)}  ")
        lines.append(f"**FEC blocks:** {len(self.blocks)}")

        lines.append("\n## Packet Structure")
        lines.append("\nEach FEC packet uses an 8-byte binary header followed by the payload:")
        lines.append("\n```")
        lines.append("┌──────────────┬──────────────┬────────────────┬─────────────┐")
        lines.append("│  Block ID    │ Packet Index │ Total Packets  │   Payload   │")
        lines.append("│  (4 bytes)   │   (2 bytes)  │   (2 bytes)    │  (variable) │")
        lines.append("└──────────────┴──────────────┴────────────────┴─────────────┘")
        lines.append("```")
        lines.append("\n- **Encoding:** Big-endian (network byte order)")
        lines.append("- **Struct format:** `!IHH` (Python struct module)")

        if loss:
            lines.append("\n## Capture Statistics")
            lines.append("\n| Metric | Value |")
            lines.append("|--------|-------|")
            lines.append(f"| Packets captured | {loss['total_received']} |")
            lines.append(f"| Packets expected | {loss['total_expected']} |")
            lines.append(f"| Packets lost | {loss['total_lost']} |")
            lines.append(f"| Loss rate | {loss['loss_rate']*100:.1f}% |")
            lines.append(f"| Data packets lost | {loss['data_lost']} |")
            lines.append(f"| Parity packets lost | {loss['parity_lost']} |")
            lines.append(f"| Recoverable blocks | {loss['recoverable_blocks']}/{loss['num_blocks']} |")
            lines.append(f"| Recovery rate | {loss['recovery_rate']*100:.1f}% |")

        if block_analysis:
            lines.append("\n## Block-by-Block Analysis")
            lines.append("\n| Block | Received | Lost (D+P) | Status |")
            lines.append("|:---:|:---:|:---:|:---:|")
            for b in block_analysis:
                status = "✓ Recoverable" if b['recoverable'] else "✗ Unrecoverable"
                lines.append(f"| {b['block_id']} | {b['received']}/{b['total']} "
                             f"| {b['data_lost']}D + {b['parity_lost']}P | {status} |")

        if timing:
            lines.append("\n## Timing Analysis")
            lines.append("\n| Metric | Value |")
            lines.append("|--------|-------|")
            lines.append(f"| Mean inter-packet delay | {timing['mean_ms']} ms |")
            lines.append(f"| Standard deviation | {timing['std_ms']} ms |")
            lines.append(f"| Minimum delay | {timing['min_ms']} ms |")
            lines.append(f"| Maximum delay | {timing['max_ms']} ms |")
            lines.append(f"| P50 (median) | {timing['p50_ms']} ms |")
            lines.append(f"| P95 | {timing['p95_ms']} ms |")

        lines.append("\n## Protocol Overhead")
        if self.packets:
            sample = self.packets[0]
            header_overhead = 8 / sample.raw_size * 100
            lines.append(f"\n- **FEC header size:** 8 bytes per packet")
            lines.append(f"- **Payload size:** {sample.payload_size} bytes")
            lines.append(f"- **Header overhead:** {header_overhead:.1f}%")
            lines.append(f"- **FEC redundancy:** 100% (4 parity per 4 data)")
            lines.append(f"- **Total overhead:** FEC header ({header_overhead:.1f}%) "
                         f"+ parity packets (100%)")

        report = '\n'.join(lines)

        with open(output_path, 'w') as f:
            f.write(report)

        print(f"  {GREEN}✓ Report saved: {output_path}{RESET}")
        return output_path


# ── CLI ─────────────────────────────────────────────────────────

def main():
    if len(sys.argv) < 2:
        print(f"Usage: python3 analyze_pcap.py <pcap_file> [--port PORT]")
        print(f"\nExample:")
        print(f"  python3 analyze_pcap.py ../data/captures/capture_demo3.pcap --port 5002")
        sys.exit(1)

    pcap_file = sys.argv[1]
    port = None

    if '--port' in sys.argv:
        port_idx = sys.argv.index('--port') + 1
        if port_idx < len(sys.argv):
            port = int(sys.argv[port_idx])

    if not os.path.exists(pcap_file):
        print(f"  {RED}✗ File not found: {pcap_file}{RESET}")
        sys.exit(1)

    analyzer = PCAPAnalyzer(pcap_file, udp_port=port)
    count = analyzer.parse()

    if count == 0:
        print(f"  {YELLOW}⚠ No FEC packets found in {pcap_file}{RESET}")
        print(f"  {DIM}  Make sure the file contains UDP traffic with FEC headers.{RESET}")
        sys.exit(1)

    analyzer.print_report()
    analyzer.generate_markdown_report()


if __name__ == '__main__':
    main()
