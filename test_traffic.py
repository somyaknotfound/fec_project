#!/usr/bin/env python3
"""
Test basic UDP traffic
"""

import threading
import time
from network.traffic_generator import TrafficGenerator
from network.traffic_receiver import TrafficReceiver

def receiver_thread():
    """Run receiver in separate thread"""
    receiver = TrafficReceiver(listen_ip="127.0.0.1", listen_port=5000)
    data = receiver.receive_packets(num_packets=10, timeout=15)
    receiver.close()
    print(f"\n✓ Receiver got {len(data)} packets")

def test_traffic():
    print("=" * 60)
    print("TRAFFIC GENERATOR/RECEIVER TEST")
    print("=" * 60)
    
    # Start receiver
    print("\n1. Starting receiver...")
    recv_thread = threading.Thread(target=receiver_thread, daemon=True)
    recv_thread.start()
    
    time.sleep(2)
    
    # Send traffic
    print("\n2. Starting sender...")
    sender = TrafficGenerator(dest_ip="127.0.0.1", dest_port=5000)
    sender.send_packets(num_packets=10, packet_size=512, delay=0.5)
    sender.close()
    
    recv_thread.join(timeout=20)
    
    print("\n" + "=" * 60)
    print("TEST COMPLETE")
    print("=" * 60)

if __name__ == "__main__":
    test_traffic()
