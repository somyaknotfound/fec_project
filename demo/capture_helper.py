#!/usr/bin/env python3
"""
Wireshark Capture Helper
========================
Optional wrapper around tshark for automated packet capture.
Can be used standalone or imported by demo scripts.

Usage (standalone):
    sudo python3 capture_helper.py start --port 5000 --name demo1
    # Run your demo script...
    sudo python3 capture_helper.py stop

Usage (as module):
    from capture_helper import WiresharkCapture
    cap = WiresharkCapture()
    cap.start_capture(port=5000, name="demo1")
    # ... run demo ...
    pcap_file = cap.stop_capture()
"""

import subprocess
import os
import sys
import time
import signal
import platform
from datetime import datetime

# ── Terminal colors ──────────────────────────────────────────────
GREEN  = '\033[92m'
RED    = '\033[91m'
YELLOW = '\033[93m'
CYAN   = '\033[96m'
BOLD   = '\033[1m'
DIM    = '\033[2m'
RESET  = '\033[0m'


class WiresharkCapture:
    """
    Controls tshark (command-line Wireshark) for packet capture.
    Handles: start/stop, file naming, permissions, platform detection.
    """

    def __init__(self, output_dir='../data/captures'):
        """
        Parameters
        ----------
        output_dir : str
            Directory to save PCAP files (relative to demo/ or absolute).
        """
        # Resolve relative to script location
        script_dir = os.path.dirname(os.path.abspath(__file__))
        if not os.path.isabs(output_dir):
            output_dir = os.path.join(script_dir, output_dir)
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)

        self.process = None
        self.capture_file = None
        self.interface = self._detect_interface()
        self.tshark_path = self._find_tshark()

    def _detect_interface(self):
        """Detect the loopback interface name based on OS."""
        system = platform.system()
        if system == 'Linux':
            return 'lo'
        elif system == 'Darwin':  # macOS
            return 'lo0'
        elif system == 'Windows':
            # Windows loopback adapter name varies
            return r'\Device\NPF_Loopback'
        return 'lo'

    def _find_tshark(self):
        """Find tshark executable path."""
        # Common locations
        candidates = [
            'tshark',                                    # In PATH
            '/usr/bin/tshark',                           # Linux
            '/usr/local/bin/tshark',                     # macOS Homebrew
            r'C:\Program Files\Wireshark\tshark.exe',    # Windows
        ]
        for path in candidates:
            try:
                result = subprocess.run(
                    [path, '--version'],
                    capture_output=True, timeout=5
                )
                if result.returncode == 0:
                    return path
            except (FileNotFoundError, subprocess.TimeoutExpired):
                continue
        return None

    def is_available(self):
        """Check if tshark is installed and accessible."""
        return self.tshark_path is not None

    def start_capture(self, port=5000, name="capture"):
        """
        Start packet capture.

        Parameters
        ----------
        port : int
            UDP port to capture.
        name : str
            Descriptive name for the capture file.

        Returns
        -------
        str or None
            Path to the PCAP file, or None if capture couldn't start.
        """
        if not self.is_available():
            print(f"\n  {YELLOW}⚠ tshark not found. Capture disabled.{RESET}")
            print(f"  {DIM}  Install Wireshark or use manual capture instead.{RESET}")
            self._print_manual_instructions(port)
            return None

        # Generate filename with timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"capture_{name}_{timestamp}.pcap"
        self.capture_file = os.path.join(self.output_dir, filename)

        # Build tshark command
        cmd = [
            self.tshark_path,
            '-i', self.interface,
            '-f', f'udp port {port}',
            '-w', self.capture_file,
            '-q',  # Quiet mode
        ]

        try:
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
            )
            time.sleep(1)  # Give tshark time to initialize

            # Check if process started successfully
            if self.process.poll() is not None:
                stderr = self.process.stderr.read().decode()
                if 'permission' in stderr.lower() or 'privileges' in stderr.lower():
                    print(f"\n  {YELLOW}⚠ Permission denied. Run with sudo:{RESET}")
                    print(f"  {CYAN}  sudo python3 {' '.join(sys.argv)}{RESET}")
                else:
                    print(f"\n  {RED}✗ tshark failed: {stderr.strip()}{RESET}")
                self.process = None
                self._print_manual_instructions(port)
                return None

            print(f"\n  {GREEN}✓ Capture started: {filename}{RESET}")
            print(f"  {DIM}  Interface: {self.interface}  |  Filter: udp port {port}{RESET}")
            return self.capture_file

        except PermissionError:
            print(f"\n  {YELLOW}⚠ Permission denied. Run with sudo:{RESET}")
            print(f"  {CYAN}  sudo python3 {' '.join(sys.argv)}{RESET}")
            self._print_manual_instructions(port)
            return None
        except Exception as e:
            print(f"\n  {RED}✗ Capture error: {e}{RESET}")
            self._print_manual_instructions(port)
            return None

    def stop_capture(self):
        """
        Stop packet capture.

        Returns
        -------
        str or None
            Path to the saved PCAP file.
        """
        if self.process is None:
            return self.capture_file

        try:
            # Send SIGINT for graceful shutdown (tshark finishes writing)
            if platform.system() == 'Windows':
                self.process.terminate()
            else:
                self.process.send_signal(signal.SIGINT)

            self.process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            self.process.kill()

        self.process = None

        if self.capture_file and os.path.exists(self.capture_file):
            size = os.path.getsize(self.capture_file)
            print(f"\n  {GREEN}✓ Capture saved: {os.path.basename(self.capture_file)}{RESET}")
            print(f"  {DIM}  Size: {size:,} bytes  |  Path: {self.capture_file}{RESET}")
            return self.capture_file
        else:
            print(f"\n  {YELLOW}⚠ Capture file not found (no packets captured?){RESET}")
            return None

    def _print_manual_instructions(self, port):
        """Print manual Wireshark capture instructions."""
        print(f"\n  {CYAN}📋 Manual Wireshark Capture:{RESET}")
        print(f"     1. Open Wireshark (sudo wireshark)")
        print(f"     2. Select interface: {self.interface}")
        print(f"     3. Set capture filter: udp port {port}")
        print(f"     4. Click Start")
        print(f"     5. Run the demo script")
        print(f"     6. Click Stop")
        print(f"     7. Save: File → Save As → {self.output_dir}/")
        print()


# ── CLI usage ───────────────────────────────────────────────────

def main():
    import argparse
    parser = argparse.ArgumentParser(description='Wireshark Capture Helper')
    parser.add_argument('action', choices=['start', 'stop', 'check'],
                        help='start/stop capture or check availability')
    parser.add_argument('--port', type=int, default=5000,
                        help='UDP port to capture (default: 5000)')
    parser.add_argument('--name', default='manual',
                        help='Descriptive name for capture file')

    args = parser.parse_args()
    cap = WiresharkCapture()

    if args.action == 'check':
        if cap.is_available():
            print(f"  {GREEN}✓ tshark found: {cap.tshark_path}{RESET}")
            print(f"  {DIM}  Interface: {cap.interface}{RESET}")
        else:
            print(f"  {RED}✗ tshark not found{RESET}")
            print(f"  {DIM}  Install: sudo apt install wireshark-common{RESET}")
    elif args.action == 'start':
        cap.start_capture(port=args.port, name=args.name)
        print(f"  {DIM}  Process running. Run demo, then: python3 capture_helper.py stop{RESET}")
        # Keep running until Ctrl+C
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            cap.stop_capture()
    elif args.action == 'stop':
        print(f"  {YELLOW}Note: stop only works when used as a module.{RESET}")
        print(f"  {DIM}  For CLI, use Ctrl+C after 'start'.{RESET}")


if __name__ == '__main__':
    main()
