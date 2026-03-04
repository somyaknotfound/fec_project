#!/usr/bin/env python3
"""
Test FEC sender and receiver integration
"""

import threading
import time
from integration.fec_sender import FECSender
from integration.fec_receiver import FECReceiver

def receiver_thread():
    """Run FEC receiver"""
    receiver = FECReceiver(listen_ip="127.0.0.1", listen_port=5000,
                          n_data=4, n_parity=4)
    
    # Receive 3 blocks (12 data packets)
    data = receiver.receive_blocks(num_blocks=3, timeout=30)
    
    print(f"\n✓ Receiver decoded {len(data)} data packets")
    
    # Show statistics
    stats = receiver.get_statistics()
    print(f"\nDecoder Statistics:")
    for key, val in stats.items():
        print(f"  {key}: {val}")
    
    receiver.close()

def test_fec_integration():
    print("=" * 60)
    print("FEC INTEGRATION TEST (SENDER + RECEIVER)")
    print("=" * 60)
    
    # Start receiver
    print("\n1. Starting FEC receiver...")
    recv_thread = threading.Thread(target=receiver_thread, daemon=True)
    recv_thread.start()
    
    time.sleep(2)
    
    # Send data with FEC
    print("\n2. Starting FEC sender...")
    sender = FECSender(dest_ip="127.0.0.1", dest_port=5000,
                      n_data=4, n_parity=4)
    
    # Send 12 packets (will create 3 FEC blocks)
    print("\n3. Sending 12 data packets...")
    for i in range(12):
        payload = f"DATA_PACKET_{i:03d}".encode() + b'X' * 1000
        sender.send_data(payload)
        print(f"  Sent packet {i+1}/12")
        time.sleep(0.3)
    
    sender.close()
    print("\n✓ Sender complete")
    
    # Wait for receiver
    recv_thread.join(timeout=30)
    
    print("\n" + "=" * 60)
    print("TEST COMPLETE")
    print("=" * 60)

if __name__ == "__main__":
    test_fec_integration()
