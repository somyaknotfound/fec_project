#!/usr/bin/env python3
"""
Test FEC Encoder/Decoder — Multi-Packet Recovery
=================================================
Tests the GF(256) erasure coding with loss scenarios from 0 to 5 packets.
Up to n_parity (4) lost packets should be fully recoverable.
"""

from core.fec_encoder import FECEncoder
from core.fec_decoder import FECDecoder


def test_fec():
    print("=" * 60)
    print("FEC ENCODER/DECODER TEST — GF(256) Erasure Coding")
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
    print(f"\n2. Encoding with GF(256) Cauchy matrix...")
    encoded_packets = encoder.encode_block(data_packets)
    print(f"   Created {len(encoded_packets)} packets (4 data + 4 parity)")
    print(f"   Overhead: {encoder.get_overhead():.1f}%")
    print(f"   Max recoverable losses: 4 packets")

    # Verify parity packets are all DIFFERENT (unlike old XOR approach)
    parity_set = set(encoded_packets[4:])
    print(f"   Unique parity packets: {len(parity_set)}/4", end="")
    if len(parity_set) == 4:
        print("  ✓ (all different — GF(256) working correctly)")
    else:
        print("  ✗ WARNING: some parity packets are identical!")

    # Test scenarios
    print(f"\n3. Testing Packet Loss Scenarios:")
    print(f"   {'Scenario':<35} {'Result':<18} {'Data OK?'}")
    print("   " + "-" * 70)

    scenarios = [
        ([0, 1, 2, 3, 4, 5, 6, 7], "No loss (0/8 lost)"),
        ([0, 2, 3, 4, 5, 6, 7],    "1 loss (data pkt 1)"),
        ([0, 1, 3, 5, 6, 7],       "2 losses (data 2 + parity 4)"),
        ([2, 3, 5, 6, 7],          "3 losses (data 0,1 + parity 4)"),
        ([0, 4, 5, 6, 7],          "3 losses (data 1,2,3)"),
        ([4, 5, 6, 7],             "4 losses (ALL data lost!)"),
        ([0, 1, 6, 7],             "4 losses (data 2,3 + parity 4,5)"),
        ([0, 1, 2],                "5 losses — TOO MANY"),
    ]

    expected_results = [True, True, True, True, True, True, True, False]
    all_passed = True

    for (received_indices, description), expected in zip(scenarios, expected_results):
        # Create received list (None for missing)
        received = [None] * len(encoded_packets)
        for idx in received_indices:
            received[idx] = encoded_packets[idx]

        # Decode
        recovered, success = decoder.decode_block(received)

        # Verify data integrity if successful
        status = "✓ RECOVERED" if success else "✗ FAILED"
        data_ok = "—"

        if success:
            # Compare recovered data to original (trimmed to original length)
            match = all(
                data_packets[i] == recovered[i][:len(data_packets[i])]
                for i in range(len(data_packets))
            )
            data_ok = "✓ verified" if match else "✗ CORRUPT!"
            if not match:
                all_passed = False
        
        if success != expected:
            status += " (UNEXPECTED!)"
            all_passed = False

        print(f"   {description:<35} {status:<18} {data_ok}")

    # Statistics
    print(f"\n4. Decoder Statistics:")
    stats = decoder.get_statistics()
    for key, value in stats.items():
        print(f"   {key}: {value}")

    print(f"\n5. Overall Result: {'ALL TESTS PASSED ✓' if all_passed else 'SOME TESTS FAILED ✗'}")

    print("\n" + "=" * 60)
    print("TEST COMPLETE")
    print("=" * 60)

    return all_passed


if __name__ == "__main__":
    success = test_fec()
    exit(0 if success else 1)
