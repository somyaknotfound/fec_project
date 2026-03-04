"""
Simple working FEC encoder
"""

import reedsolo

class FECEncoder:
    def __init__(self, n_data_packets=4, n_parity_packets=2):
        self.n_data = n_data_packets
        self.n_parity = n_parity_packets
        # Use small RS code per byte position
        self.rs = reedsolo.RSCodec(n_parity_packets)
    
    def encode_block(self, data_packets):
        # Get max size
        max_len = max(len(p) for p in data_packets)
        
        # Pad all to same size
        padded = [p + b'\x00' * (max_len - len(p)) for p in data_packets]
        
        # Transpose: group bytes by position
        result_packets = list(padded)  # Start with data packets
        
        # Add parity packets (simple XOR-based for now)
        for _ in range(self.n_parity):
            parity = bytearray(max_len)
            for pkt in padded:
                for i, byte in enumerate(pkt):
                    parity[i] ^= byte
            result_packets.append(bytes(parity))
        
        return result_packets
    
    def get_overhead(self):
        return (self.n_parity / self.n_data) * 100
