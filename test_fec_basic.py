#!/usr/bin/env python3
"""
Test FEC encoder and decoder
"""

from core.fec_encoder import FECEncoder
from core.fec_decoder import FECDecoder

def test_fec():
    print("=" * 60)
    print("FEC ENCODER/DECODER TEST")
    print("=" * 60)
    
    # Use 4+4 code (can recover up to 4 lost packets)
    encoder = FECEncoder(n_data_packets=4, n_parity_packets=4)
    decoder = FECDecoder(n_data_packets=4, n_parity_packets=4)
    
    # Original data
    data_packets = [
        b"Packet 0: Hello World!",
        b"Packet 1: Testing FEC",
        b"Packet 2: This is data",
        b"Packet 3: Final packet"
    ]
    
    print(f"\n1. Original Data ({len(data_packets)} packets):")
    for i, pkt in enumerate(data_packets):
        print(f"   [{i}] {pkt}")
    
    # Encode
    print(f"\n2. Encoding...")
    encoded_packets = encoder.encode_block(data_packets)
    print(f"   ✓ Created {len(encoded_packets)} packets (4 data + 4 parity)")
    print(f"   Overhead: {encoder.get_overhead():.1f}%")
    print(f"   Can recover up to 4 lost packets")
    
    # Test scenarios
    print(f"\n3. Testing Packet Loss Scenarios:")
    
    scenarios = [
        ([0, 1, 2, 3, 4, 5, 6, 7], "No loss (0/8)"),
        ([0, 2, 3, 4, 5, 6, 7], "Lost 1 packet (1/8)"),
        ([0, 1, 3, 5, 6, 7], "Lost 2 packets (2/8)"),
        ([0, 3, 4, 5, 6], "Lost 3 packets (3/8)"),
        ([0, 1, 2, 3], "Lost 4 packets (4/8) - LIMIT"),
        ([0, 1, 2], "Lost 5 packets (5/8) - TOO MANY")
    ]
    
    for received_indices, description in scenarios:
        print(f"\n   {description}")
        print(f"   Received indices: {received_indices}")
        
        # Create received list
        received = [None] * len(encoded_packets)
        for idx in received_indices:
            received[idx] = encoded_packets[idx]
        
        # Decode
        recovered, success = decoder.decode_block(received)
        
        if success:
            print(f"   ✓ DECODING SUCCESS")
            # Verify
            match = all(data_packets[i] == recovered[i][:len(data_packets[i])] 
                       for i in range(len(data_packets)))
            if match:
                print(f"   ✓ Data integrity verified")
            else:
                print(f"   ✗ Data corrupted!")
        else:
            print(f"   ✗ DECODING FAILED")
    
    # Statistics
    print(f"\n4. Decoder Statistics:")
    stats = decoder.get_statistics()
    for key, value in stats.items():
        print(f"   {key}: {value}")
    
    print("\n" + "=" * 60)
    print("TEST COMPLETE")
    print("=" * 60)

if __name__ == "__main__":
    test_fec()
